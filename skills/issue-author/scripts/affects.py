#!/usr/bin/env python3
"""Run one reproduction on several refs and report which ones show the bug.

Usage:
  affects.py --ref main --ref v1.9.4 --ref release/1.x \\
      [--copy test/repro.test.js] [--setup 'npm ci'] [--symptom '<regex>'] \\
      [--cwd <repo>] [--timeout 300] [--keep] [--json] -- <command>

Each ref gets a detached worktree in .git/issue-author/affects/, which git never
commits. --copy puts the current checkout's version of a file into each
worktree first, usually the reproduction test, since older refs do not have it.
--setup runs once per worktree before the command (a shell string, for example
an install). Worktrees are removed afterwards unless --keep is given.

Result per ref:
  affected        the command fails (and its output matches --symptom, if given)
  not-affected    the command passes
  other-failure   the command fails without the symptom, or setup failed
  error           the ref does not exist, or the command could not run
Exit code 0 when every ref ran, 1 otherwise.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd, cwd, timeout, shell=False):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, shell=shell)
        return r.returncode, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        return None, f"timeout after {timeout}s"
    except FileNotFoundError as e:
        return None, str(e)


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", action="append", required=True)
    ap.add_argument("--copy", action="append", default=[])
    ap.add_argument("--setup")
    ap.add_argument("--symptom")
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("command", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        sys.exit("give the command after --")

    repo = Path(git(args.cwd, "rev-parse", "--show-toplevel").stdout.strip() or args.cwd).resolve()
    common = Path(git(repo, "rev-parse", "--git-common-dir").stdout.strip())
    root = (common if common.is_absolute() else repo / common) / "issue-author" / "affects"
    root.mkdir(parents=True, exist_ok=True)
    symptom = re.compile(args.symptom) if args.symptom else None

    results = []
    for ref in args.ref:
        res = {"ref": ref}
        sha = git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").stdout.strip()
        if not sha:
            res.update(result="error", tail=[f"unknown ref: {ref}"])
            results.append(res)
            continue
        res["commit"] = sha[:12]
        wt = root / re.sub(r"[^A-Za-z0-9._-]", "-", ref)
        if wt.exists():
            git(repo, "worktree", "remove", "--force", str(wt))
            shutil.rmtree(wt, ignore_errors=True)
        made = git(repo, "worktree", "add", "--detach", str(wt), sha)
        if made.returncode != 0:
            res.update(result="error", tail=made.stderr.strip().splitlines()[-5:])
            results.append(res)
            continue
        try:
            for rel in args.copy:
                src = repo / rel
                dst = wt / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            if args.setup:
                code, out = run(args.setup, wt, args.timeout, shell=True)
                if code != 0:
                    res.update(result="other-failure", stage="setup", exit=code, tail=out.strip().splitlines()[-8:])
                    results.append(res)
                    continue
            code, out = run(command, wt, args.timeout)
            res["exit"] = code
            res["tail"] = out.strip().splitlines()[-8:]
            if code is None:
                res["result"] = "error"
            elif code == 0:
                res["result"] = "not-affected"
            elif symptom and not symptom.search(out):
                res["result"] = "other-failure"
            else:
                res["result"] = "affected"
            results.append(res)
        finally:
            if not args.keep:
                git(repo, "worktree", "remove", "--force", str(wt))
            else:
                res["worktree"] = str(wt)

    if args.json:
        print(json.dumps({"command": command, "results": results}, indent=2))
    else:
        for r in results:
            print(f"{r['ref']:<20} {r.get('commit', ''):<13} {r['result']}")
            if r["result"] in ("other-failure", "error"):
                for line in r.get("tail", [])[-3:]:
                    print(f"    {line}")
    sys.exit(0 if all(r["result"] != "error" for r in results) else 1)


if __name__ == "__main__":
    main()

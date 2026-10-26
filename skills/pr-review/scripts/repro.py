#!/usr/bin/env python3
"""Prove a fix: the reproduction must fail on the base and pass on the head.

Usage:
  repro.py <base-dir> <head-dir> --copy src/sum.test.js -- node --test src/sum.test.js
  repro.py <base-dir> <head-dir> -- ./repro.sh

--copy puts the head's version of a file on the base first, usually the test the
pull request adds or changes, since the base does not have it yet. The base's own
files are restored afterwards. The command runs in each directory.

Prints JSON with both results and a verdict:
  proven            fails on base, passes on head
  not-reproduced    passes on base too, so the problem is not shown
  not-fixed         fails on head too
  inconclusive      anything else (for example both error before running)
Exit code 0 only for "proven".
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd, cwd, timeout):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return {"exit": r.returncode, "tail": (r.stdout + r.stderr).strip().splitlines()[-12:]}
    except subprocess.TimeoutExpired:
        return {"exit": None, "tail": [f"timeout after {timeout}s"]}
    except FileNotFoundError as e:
        return {"exit": None, "tail": [str(e)]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base")
    ap.add_argument("head")
    ap.add_argument("--copy", action="append", default=[])
    ap.add_argument("--timeout", type=int, default=600)
    argv = sys.argv[1:]
    split = argv.index("--") if "--" in argv else len(argv)
    args = ap.parse_args(argv[:split])
    cmd = argv[split + 1:]
    if not cmd:
        ap.error("give the reproduction command after --")

    # Put the head's version of each file on the base, even when the base has its own
    # version (a PR often adds a test to an existing file). Restore the base afterwards.
    restore = []
    for rel in args.copy:
        src, dst = Path(args.head) / rel, Path(args.base) / rel
        backup = dst.read_bytes() if dst.exists() else None
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        restore.append((dst, backup))
    try:
        base, head = run(cmd, args.base, args.timeout), run(cmd, args.head, args.timeout)
    finally:
        for dst, backup in restore:
            if backup is None:
                dst.unlink()
            else:
                dst.write_bytes(backup)

    if base["exit"] not in (0, None) and head["exit"] == 0:
        verdict = "proven"
    elif base["exit"] == 0:
        verdict = "not-reproduced"
    elif head["exit"] not in (0, None):
        verdict = "not-fixed"
    else:
        verdict = "inconclusive"
    print(json.dumps({"command": " ".join(cmd), "copied": args.copy, "base": base, "head": head,
                      "verdict": verdict}, indent=2))
    raise SystemExit(0 if verdict == "proven" else 1)


if __name__ == "__main__":
    main()

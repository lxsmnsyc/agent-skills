#!/usr/bin/env python3
"""Check out the base and the head of a change side by side, so a problem can be
reproduced on the base and the fix checked on the head without touching the
user's own checkout.

Usage:
  worktrees.py prepare --pr 42                    # base and head of a GitHub pull request
  worktrees.py prepare --base main --head feat/x  # two local refs
  worktrees.py cleanup <name>                     # remove both worktrees
  worktrees.py cleanup --all                      # remove every review worktree of this repo

Worktrees go to .git/review-worktrees/<name>-base and <name>-head. Prints JSON with
both paths. The base worktree is at the merge base, which is what the pull
request was written against. Add --tip to use the current tip of the base branch.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def git(*args, cwd=None):
    r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        sys.exit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def review_dir():
    # Inside the git directory, so review checkouts never show up next to the user's
    # repos or in `git status`, even when a cleanup is missed.
    root = Path(git("rev-parse", "--show-toplevel"))
    common = Path(git("rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = (root / common).resolve()
    return root, common / "review-worktrees"


def add(path, ref):
    if path.exists():
        git("worktree", "remove", "--force", str(path))
    git("worktree", "add", "--detach", str(path), ref)


def prepare(args):
    root, base_dir = review_dir()
    base_dir.mkdir(exist_ok=True)
    if args.pr:
        info = json.loads(subprocess.run(
            ["gh", "pr", "view", str(args.pr), "--json", "baseRefName,headRefOid"],
            capture_output=True, text=True, check=True).stdout)
        git("fetch", "--quiet", "origin", info["baseRefName"], f"pull/{args.pr}/head")
        base_ref, head_ref, name = f"origin/{info['baseRefName']}", info["headRefOid"], f"pr-{args.pr}"
    else:
        base_ref, head_ref = args.base, args.head
        name = args.name or head_ref.replace("/", "-")
    base_at = git("rev-parse", base_ref) if args.tip else git("merge-base", base_ref, head_ref)
    paths = {"base": base_dir / f"{name}-base", "head": base_dir / f"{name}-head"}
    add(paths["base"], base_at)
    add(paths["head"], head_ref)
    print(json.dumps({"name": name, "base": str(paths["base"]), "head": str(paths["head"]),
                      "base_commit": base_at, "head_commit": git("rev-parse", head_ref),
                      "cleanup": f"python3 {Path(__file__).resolve()} cleanup {name}"}, indent=2))


def cleanup(args):
    _, base_dir = review_dir()
    if args.all:
        targets = [p for p in base_dir.glob("*") if p.is_dir()] if base_dir.exists() else []
    else:
        targets = [base_dir / f"{args.name}-{side}" for side in ("base", "head")]
    for p in targets:
        if p.exists():
            git("worktree", "remove", "--force", str(p))
    git("worktree", "prune")
    if base_dir.exists() and not any(base_dir.iterdir()):
        base_dir.rmdir()
    left = [l for l in git("worktree", "list").splitlines() if str(base_dir) in l]
    print("cleanup: no review worktrees left" if not left else
          "cleanup: still registered:\n" + "\n".join(left))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--pr")
    p.add_argument("--base")
    p.add_argument("--head")
    p.add_argument("--name")
    p.add_argument("--tip", action="store_true", help="base at the tip of the base branch")
    c = sub.add_parser("cleanup")
    c.add_argument("name", nargs="?")
    c.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.cmd == "prepare":
        if not args.pr and not (args.base and args.head):
            ap.error("prepare needs --pr, or --base and --head")
        prepare(args)
    else:
        if not args.name and not args.all:
            ap.error("cleanup needs a name or --all")
        cleanup(args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Manage one worktree per branch for authoring pull requests.

Usage:
  wt.py new <branch> [--base main] [--from <ref>]  # new branch in .worktrees/<branch>
  wt.py list                                       # worktrees with branch, base and state
  wt.py remove <branch> [--delete-branch]
  wt.py prune-merged [--base main]                 # remove worktrees whose branch is merged

Worktrees live in .worktrees/ at the repo root. The folder is added to
.git/info/exclude, so it never shows up in `git status` and is never committed,
while it stays easy to open in an editor. Each worktree gets an index that tools can use to pick free ports (for example
port = 3000 + 10 * index). `wt.py new` and `wt.py list` print it.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def git(*args, cwd=None, check=True):
    r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd)
    if check and r.returncode != 0:
        sys.exit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def root():
    # The main checkout, even when run from inside a worktree.
    common = Path(git("rev-parse", "--git-common-dir")).resolve()
    return common.parent


def exclude(repo):
    f = repo / ".git" / "info" / "exclude"
    f.parent.mkdir(parents=True, exist_ok=True)
    text = f.read_text() if f.exists() else ""
    if "/.worktrees/" not in text.splitlines():
        f.write_text(text + ("" if text.endswith("\n") or not text else "\n") + "/.worktrees/\n")


def worktrees():
    out, cur = [], {}
    for line in git("worktree", "list", "--porcelain").splitlines() + [""]:
        if not line:
            if cur:
                out.append(cur)
            cur = {}
            continue
        k, _, v = line.partition(" ")
        cur[k] = v or True
    return out


def meta(path):
    try:
        f = Path(git("rev-parse", "--absolute-git-dir", cwd=path, check=False)) / "pr-author.json"
        return json.loads(f.read_text())
    except (OSError, ValueError):
        return {}


def write_meta(path, data):
    f = Path(git("rev-parse", "--absolute-git-dir", cwd=path)) / "pr-author.json"
    f.write_text(json.dumps(data))


def slug(branch):
    return branch.replace("/", "-")


def new(args):
    repo = root()
    exclude(repo)
    path = repo / ".worktrees" / slug(args.branch)
    if path.exists():
        sys.exit(f"{path} already exists")
    start = args.from_ref or args.base
    exists = git("rev-parse", "--verify", "--quiet", f"refs/heads/{args.branch}", check=False)
    if exists:
        git("worktree", "add", str(path), args.branch)
    else:
        git("worktree", "add", "-b", args.branch, str(path), start)
    # Bookkeeping lives in git's private folder for this worktree, so the checkout stays clean.
    used = {meta(Path(w["worktree"])).get("index") for w in worktrees()}
    index = next(i for i in range(1, 1000) if i not in used)
    write_meta(path, {"index": index, "base": args.base, "created_at": git("rev-parse", "HEAD", cwd=path)})
    print(json.dumps({"branch": args.branch, "path": str(path), "base": args.base,
                      "started_from": start, "index": index}, indent=2))


def list_(args):
    repo = root()
    for w in worktrees():
        p = Path(w["worktree"])
        if p.parent != repo / ".worktrees":
            continue
        branch = w.get("branch", "").replace("refs/heads/", "") or "(detached)"
        dirty = bool(git("status", "--porcelain", cwd=p, check=False))
        ahead = git("rev-list", "--count", f"{args.base}..HEAD", cwd=p, check=False) or "?"
        print(f"{branch}  {p}  index {meta(p).get('index', '?')}  {ahead} commits ahead of "
              f"{args.base}{'  uncommitted changes' if dirty else ''}")


def remove(args):
    repo = root()
    path = repo / ".worktrees" / slug(args.branch)
    if path.exists():
        if git("status", "--porcelain", cwd=path, check=False) and not args.force:
            sys.exit(f"{path} has uncommitted changes; commit them or pass --force")
        git("worktree", "remove", "--force", str(path))
    git("worktree", "prune")
    if args.delete_branch:
        git("branch", "-D" if args.force else "-d", args.branch)
    print(f"removed {args.branch}")


def prune_merged(args):
    repo = root()
    for w in worktrees():
        p = Path(w["worktree"])
        branch = w.get("branch", "").replace("refs/heads/", "")
        if p.parent != repo / ".worktrees" or not branch or branch == args.base:
            continue
        tip, start = git("rev-parse", "HEAD", cwd=p), meta(p).get("created_at")
        # A branch with no commits of its own is new work, not merged work.
        if tip == start:
            continue
        merged = subprocess.run(["git", "merge-base", "--is-ancestor", tip, args.base],
                                cwd=p).returncode == 0
        if merged:
            if git("status", "--porcelain", cwd=p, check=False):
                print(f"kept {branch}: merged, but has uncommitted changes")
                continue
            git("worktree", "remove", str(p))
            print(f"removed {branch} (merged into {args.base})")
    git("worktree", "prune")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("branch")
    n.add_argument("--base", default="main")
    n.add_argument("--from", dest="from_ref")
    l = sub.add_parser("list")
    l.add_argument("--base", default="main")
    r = sub.add_parser("remove")
    r.add_argument("branch")
    r.add_argument("--delete-branch", action="store_true")
    r.add_argument("--force", action="store_true")
    p = sub.add_parser("prune-merged")
    p.add_argument("--base", default="main")
    args = ap.parse_args()
    {"new": new, "list": list_, "remove": remove, "prune-merged": prune_merged}[args.cmd](args)


if __name__ == "__main__":
    main()

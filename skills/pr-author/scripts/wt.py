#!/usr/bin/env python3
"""Manage one worktree per branch for authoring pull requests.

Usage:
  wt.py new <branch> [--base main] [--from <ref>]  # new branch in .worktrees/<branch>
  wt.py list                                       # worktrees with branch, base and state
  wt.py remove <branch> [--delete-branch]
  wt.py prune-merged [--base main --base dev] [--remote] [--all-branches] [--dry-run]
                                                   # remove merged branches: worktree, local, remote

Worktrees live in .worktrees/ at the repo root. The folder is added to
.git/info/exclude, so it never shows up in `git status` and is never committed,
while it stays easy to open in an editor.

prune-merged asks GitHub for the branch's merged pull request when `gh` works,
which finds squash and rebase merges, and falls back to commit ancestry. A
branch with commits newer than its merged PR is kept. Each worktree gets an index that tools can use to pick free ports (for example
port = 3000 + 10 * index). `wt.py new` and `wt.py list` print it.
"""
import argparse
import json
import os
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


def gh_merged_pr(branch):
    """The merged pull request for a branch, from GitHub. Finds squash and rebase merges,
    which plain git cannot see. Returns None when gh is missing or there is no merged PR."""
    fake = os.environ.get("PR_AUTHOR_FAKE_GH")  # tests: a JSON file mapping branch -> PR
    if fake:
        return json.loads(Path(fake).read_text()).get(branch)
    try:
        r = subprocess.run(["gh", "pr", "list", "--state", "merged", "--head", branch, "--json",
                            "number,baseRefName,headRefOid,mergedAt", "--limit", "1"],
                           capture_output=True, text=True, timeout=30)
        prs = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else []
        return prs[0] if prs else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def merged_into(branch, tip, bases, cwd):
    """Where a branch was merged, and how we know: (base, source) or (None, None)."""
    pr = gh_merged_pr(branch)
    if pr:
        # New commits after the merge are unmerged work.
        if pr.get("headRefOid") and pr["headRefOid"] != tip:
            return None, f"PR #{pr['number']} merged, but the branch has newer commits"
        return pr["baseRefName"], f"PR #{pr['number']}"
    for base in bases:
        if git("rev-parse", "--verify", "--quiet", base, cwd=cwd, check=False) and \
                subprocess.run(["git", "merge-base", "--is-ancestor", tip, base], cwd=cwd).returncode == 0:
            return base, "commits are in " + base
    return None, None


def remote_has(branch, cwd):
    out = git("ls-remote", "--heads", "origin", branch, cwd=cwd, check=False)
    return bool(out.strip())


def prune_merged(args):
    repo = root()
    bases = args.base or ["main"]
    candidates = []
    for w in worktrees():
        p = Path(w["worktree"])
        branch = w.get("branch", "").replace("refs/heads/", "")
        if p.parent == repo / ".worktrees" and branch and branch not in bases:
            candidates.append((branch, p))
    if args.all_branches:
        listed = {b for b, _ in candidates}
        for b in git("branch", "--format=%(refname:short)").splitlines():
            if b not in listed and b not in bases and b != git("branch", "--show-current"):
                candidates.append((b, None))

    for branch, p in candidates:
        tip = git("rev-parse", branch)
        start = meta(p).get("created_at") if p else None
        if tip == start:  # no commits of its own yet: new work, not merged work
            continue
        base, how = merged_into(branch, tip, bases, repo)
        if not base:
            if how:
                print(f"kept {branch}: {how}")
            continue
        if p and git("status", "--porcelain", cwd=p, check=False):
            print(f"kept {branch}: merged into {base} ({how}), but has uncommitted changes")
            continue
        actions = []
        if p:
            actions.append("worktree")
            if not args.dry_run:
                git("worktree", "remove", str(p))
        actions.append("local branch")
        if not args.dry_run:
            # -D is safe here: the merge is confirmed by GitHub or by ancestry.
            git("branch", "-D", branch)
        if args.remote and remote_has(branch, repo):
            actions.append("remote branch")
            if not args.dry_run:
                git("push", "--quiet", "origin", "--delete", branch)
        verb = "would remove" if args.dry_run else "removed"
        print(f"{verb} {branch} ({', '.join(actions)}): merged into {base} ({how})")
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
    p.add_argument("--base", action="append",
                   help="integration branch to check against; repeat for several (default main)")
    p.add_argument("--remote", action="store_true", help="also delete the branch on origin")
    p.add_argument("--all-branches", action="store_true",
                   help="also local branches without a worktree")
    p.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    {"new": new, "list": list_, "remove": remove, "prune-merged": prune_merged}[args.cmd](args)


if __name__ == "__main__":
    main()

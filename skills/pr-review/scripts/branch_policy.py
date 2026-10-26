#!/usr/bin/env python3
"""Work out which branch each kind of change should target.

Usage:
  branch_policy.py                          # the policy, as JSON
  branch_policy.py --type fix               # the branch a fix should target
  branch_policy.py --type feature --base main   # check a PR's base; exit 1 when it is wrong
  branch_policy.py --roadmap docs/roadmaps/x    # read the policy from that roadmap's GOAL.md

Kinds: feature, fix, hotfix, refactor, docs, chore, release.

Where the policy comes from, first match wins:
1. The `branches:` frontmatter of a roadmap's GOAL.md (with --roadmap).
2. A `.github/branches.yml` file with the same keys.
3. Detection from the branches that exist:
   - `dev` or `develop` exists: features and fixes go there, hotfixes go to the
     default branch, and releases promote dev -> next (if `next` exists) -> default.
   - otherwise trunk-based: everything targets the default branch.

Policy keys: default, feature, fix, hotfix, refactor, docs, chore, promote (a list
from the first integration branch to the release branch), back_merge (branches a
hotfix is merged back into).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

KINDS = ("feature", "fix", "hotfix", "refactor", "docs", "chore", "release")


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def branches():
    names = set()
    for line in git("branch", "-a", "--format=%(refname:short)").splitlines():
        names.add(re.sub(r"^origin/", "", line.strip()))
    names.discard("HEAD")
    names.discard("origin")
    return names


def default_branch(names):
    head = git("symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    if head:
        return head.split("/", 1)[1]
    for b in ("main", "master", "trunk"):
        if b in names:
            return b
    return git("branch", "--show-current") or "main"


def parse_simple_yaml(text):
    """key: value and key: [a, b] lines only. Enough for a branch policy."""
    out = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].rstrip()
        m = re.match(r"^\s*([\w-]+):\s*(.*)$", line)
        if not m or not m.group(2):
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith("["):
            out[key] = [v.strip() for v in val.strip("[]").split(",") if v.strip()]
        elif "->" in val:
            out[key] = [v.strip() for v in val.split("->")]
        else:
            out[key] = val
    return out


def from_roadmap(root):
    goal = Path(root) / "GOAL.md"
    if not goal.exists():
        return None
    text = goal.read_text()
    if not text.startswith("---"):
        return None
    fm = text[3:text.find("\n---", 3)]
    block = re.search(r"^branches:\s*\n((?:[ \t]+.*\n?)+)", fm, re.M)
    return parse_simple_yaml(block.group(1)) if block else None


def detect(names):
    default = default_branch(names)
    dev = next((b for b in ("dev", "develop", "development") if b in names), None)
    if not dev:
        return {"default": default, "feature": default, "fix": default, "hotfix": default,
                "promote": [default], "back_merge": [], "style": "trunk"}
    chain = [dev] + (["next"] if "next" in names else []) + [default]
    return {"default": default, "feature": dev, "fix": dev, "hotfix": default,
            "promote": chain, "back_merge": [b for b in chain[:-1]][::-1], "style": "gitflow"}


def policy(roadmap=None):
    names = branches()
    detected = detect(names)
    for source, found in (("roadmap GOAL.md", from_roadmap(roadmap) if roadmap else None),
                          (".github/branches.yml", parse_simple_yaml(Path(".github/branches.yml").read_text())
                           if Path(".github/branches.yml").exists() else None)):
        if found:
            merged = {**detected, **found}
            merged.setdefault("default", detected["default"])
            if "back_merge" not in found and merged.get("promote"):
                merged["back_merge"] = list(reversed(merged["promote"][:-1]))
            merged["source"] = source
            return merged
    detected["source"] = "detected from branches"
    return detected


def target(pol, kind):
    if kind == "release":
        return pol["promote"][-1]
    return pol.get(kind) or pol.get("feature") or pol["default"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--type", choices=KINDS)
    ap.add_argument("--base", help="the base a PR uses; checked against the policy")
    ap.add_argument("--roadmap")
    args = ap.parse_args()
    pol = policy(args.roadmap)
    if not args.type:
        print(json.dumps(pol, indent=2))
        return
    want = target(pol, args.type)
    out = {"type": args.type, "target": want, "source": pol["source"]}
    if args.type == "hotfix":
        out["back_merge"] = pol.get("back_merge", [])
    if args.base:
        out["base"] = args.base
        out["ok"] = args.base == want
        if not out["ok"]:
            out["advice"] = f"A {args.type} should target {want}, not {args.base}."
    print(json.dumps(out, indent=2))
    sys.exit(0 if out.get("ok", True) else 1)


if __name__ == "__main__":
    main()

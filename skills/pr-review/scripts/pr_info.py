#!/usr/bin/env python3
"""Collect what a review needs to know about a pull request, as JSON.

Usage:
  pr_info.py <number|url>                     # a GitHub pull request (needs gh)
  pr_info.py --local --base main --head feat  # two local refs, no GitHub needed

Output: title, body, author, base, head, changed files, a type hint (fix, feature,
other), linked issues, repo visibility, the maintainer and how it was found, the
session user, CI check results, roadmap nodes the change may belong to, and the
base the branch policy expects for this kind of change (see branch_policy.py).
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
import branch_policy  # noqa: E402


def base_check(kind, base):
    """Which branch this kind of change should target under the repo's branch policy."""
    pol = branch_policy.policy()
    want = branch_policy.target(pol, kind if kind in branch_policy.KINDS else "feature")
    return {"policy_style": pol.get("style", pol.get("source")), "expected_base": want,
            "base_ok": base == want, "policy_source": pol["source"]}


def run(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}: {r.stderr.strip()}")
    return r.stdout.strip()


def gh_json(args):
    return json.loads(run(["gh"] + args))


def type_hint(title, labels, branch):
    text = " ".join([title.lower(), branch.lower()] + [l.lower() for l in labels])
    if branch.lower().startswith(("hotfix/", "hotfix-")) or re.search(r"\bhotfix\b", text):
        return "hotfix"
    if branch.lower().startswith(("release/", "release-")) or "release" in [l.lower() for l in labels]:
        return "release"
    if re.search(r"^(fix|bugfix|hotfix)(\(.+?\))?!?:", title.lower()) or re.search(
            r"\b(fix|bug|hotfix|regression)\b", text):
        return "fix"
    if re.search(r"^feat(\(.+?\))?!?:", title.lower()) or re.search(
            r"\b(feat|feature|enhancement)\b", text):
        return "feature"
    return "other"


def linked_issues(body):
    return sorted(set(int(n) for n in re.findall(
        r"(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)", body or "")))


def codeowners(root, files):
    for p in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        f = Path(root) / p
        if f.exists():
            rules = []
            for line in f.read_text().splitlines():
                line = line.split("#", 1)[0].strip()
                if line:
                    parts = line.split()
                    rules.append((parts[0], parts[1:]))
            owners = set()
            for path in files:
                match = None
                for pat, who in rules:  # last match wins, as on GitHub
                    g = pat.lstrip("/")
                    if g.endswith("/"):
                        g += "**"
                    if fnmatch.fnmatch(path, g) or fnmatch.fnmatch(path, g + "/**") or (
                            "/" not in pat.strip("/") and fnmatch.fnmatch(Path(path).name, g)):
                        match = who
                if match:
                    owners.update(o.lstrip("@") for o in match)
            return sorted(owners)
    return []


def maintainer(owner, owner_type, root, files, me):
    if owner_type == "User":
        return [owner], "repo owner"
    owners = codeowners(root, files)
    if owners:
        return owners, "CODEOWNERS for the changed files"
    return ([me] if me else []), "no CODEOWNERS match in an organization repo; falls back to the session user"


def roadmap_nodes(root, files, body):
    """Nodes whose brief is linked in the body, or whose owned paths cover changed files."""
    root = Path(root)
    briefs = list(root.glob("docs/roadmaps/*/nodes/*/brief.md")) + list(
        root.glob("roadmaps/*/nodes/*/brief.md"))
    found = []
    for b in briefs:
        rel = str(b.relative_to(root))
        text = b.read_text()
        fm = text.split("---", 2)[1] if text.startswith("---") else ""
        nid = (re.search(r"^id:\s*(\S+)", fm, re.M) or [None, b.parent.name])[1]
        status = (re.search(r"^status:\s*(\S+)", fm, re.M) or [None, "todo"])[1]
        owns = re.findall(r"^\s*-\s+(\S+)", fm.split("owns:", 1)[1].split("\n\S", 1)[0], re.M) \
            if "owns:" in fm else []
        inline = re.search(r"^owns:\s*\[(.*)\]", fm, re.M)
        if inline:
            owns = [o.strip() for o in inline.group(1).split(",") if o.strip()]
        linked = rel in (body or "") or f"nodes/{nid}/" in (body or "")
        covered = [f for f in files for o in owns if fnmatch.fnmatch(f, o) or f.startswith(o.rstrip("*"))]
        if linked or covered:
            found.append({"id": nid, "brief": rel, "status": status, "linked": linked,
                          "covers": sorted(set(covered))[:10]})
    return found


def from_github(ref):
    fields = ("number,title,body,author,baseRefName,headRefName,headRefOid,baseRefOid,files,"
              "additions,deletions,labels,isDraft,mergeable,url,headRepositoryOwner,"
              "isCrossRepository")
    pr = gh_json(["pr", "view", str(ref), "--json", fields])
    repo = gh_json(["repo", "view", "--json", "nameWithOwner,visibility,owner"])
    owner_type = gh_json(["api", f"users/{repo['owner']['login']}", "--jq", "{type: .type}"])["type"]
    me = run(["gh", "api", "user", "--jq", ".login"], check=False) or None
    try:
        checks = json.loads(run(["gh", "pr", "checks", str(ref), "--json", "name,state,bucket"],
                                check=False) or "[]")
    except ValueError:
        checks = []
    files = [f["path"] for f in pr["files"]]
    root = run(["git", "rev-parse", "--show-toplevel"])
    who, how = maintainer(repo["owner"]["login"], owner_type, root, files, me)
    return {
        "mode": "github",
        "number": pr["number"], "url": pr["url"], "title": pr["title"], "body": pr["body"],
        "author": pr["author"]["login"], "base": pr["baseRefName"], "head": pr["headRefName"],
        "head_sha": pr["headRefOid"], "draft": pr["isDraft"], "mergeable": pr["mergeable"],
        "from_fork": pr["isCrossRepository"],
        "labels": [l["name"] for l in pr["labels"]],
        "files": [{"path": f["path"], "additions": f["additions"], "deletions": f["deletions"]}
                  for f in pr["files"]],
        "additions": pr["additions"], "deletions": pr["deletions"],
        "type_hint": type_hint(pr["title"], [l["name"] for l in pr["labels"]], pr["headRefName"]),
        "linked_issues": linked_issues(pr["body"]),
        "repo": repo["nameWithOwner"], "visibility": repo["visibility"],
        "maintainer": who, "maintainer_source": how, "session_user": me,
        "session_user_is_maintainer": bool(me and me in who),
        "checks": [{"name": c["name"], "state": c["state"], "bucket": c.get("bucket")} for c in checks],
        "roadmap_nodes": roadmap_nodes(root, files, pr["body"]),
        **base_check(type_hint(pr["title"], [l["name"] for l in pr["labels"]], pr["headRefName"]),
                     pr["baseRefName"]),
    }


def from_local(base, head):
    root = run(["git", "rev-parse", "--show-toplevel"])
    mb = run(["git", "merge-base", base, head])
    numstat = run(["git", "diff", "--numstat", f"{mb}..{head}"])
    files = []
    for line in numstat.splitlines():
        a, d, path = line.split("\t", 2)
        files.append({"path": path, "additions": int(a) if a.isdigit() else 0,
                      "deletions": int(d) if d.isdigit() else 0})
    log = run(["git", "log", "--format=%s%n%b%x1e", f"{mb}..{head}"])
    subjects = [c.strip().split("\n", 1)[0] for c in log.split("\x1e") if c.strip()]
    title = subjects[-1] if subjects else head
    body = log.replace("\x1e", "\n")
    me = run(["git", "config", "user.name"], check=False) or None
    return {
        "mode": "local", "title": title, "body": body, "commits": subjects[::-1],
        "author": run(["git", "log", "-1", "--format=%an", head]),
        "base": base, "head": head, "merge_base": mb, "head_sha": run(["git", "rev-parse", head]),
        "files": files,
        "additions": sum(f["additions"] for f in files),
        "deletions": sum(f["deletions"] for f in files),
        "type_hint": type_hint(title, [], head),
        "linked_issues": linked_issues(body),
        "repo": Path(root).name, "visibility": "local",
        "maintainer": [me] if me else [], "maintainer_source": "local review; the session user",
        "session_user": me, "session_user_is_maintainer": True,
        "checks": [],
        "roadmap_nodes": roadmap_nodes(root, [f["path"] for f in files], body),
        **base_check(type_hint(title, [], head), base),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pr", nargs="?")
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--base")
    ap.add_argument("--head")
    args = ap.parse_args()
    try:
        if args.local:
            if not (args.base and args.head):
                ap.error("--local needs --base and --head")
            info = from_local(args.base, args.head)
        else:
            if not args.pr:
                ap.error("give a pull request number or url, or --local")
            info = from_github(args.pr)
    except RuntimeError as e:
        sys.exit(str(e))
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()

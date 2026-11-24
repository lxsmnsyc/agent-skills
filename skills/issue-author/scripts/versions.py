#!/usr/bin/env python3
"""List a repo's release lines and say which ones are still maintained.

Usage:
  versions.py [--cwd <repo>] [--json] [--offline] [--package <npm name>] [--active-days 365]

A release line is one major version ("2.x"), or one minor for 0.x releases
("0.4.x"), because before 1.0 each minor can break. For each line the script
collects what the repo shows:

  policy     a row of the support table in SECURITY.md or SUPPORT.md
             (root, .github/ or docs/), marked supported or not
  branch     a maintenance branch such as release/1.x, v1, 1.x or 1.4.x
  tag        the newest semver tag of the line, and its date
  dist_tag   npm dist-tags pointing into the line (skipped with --offline)
  current    the line of the default branch's package.json, or of the newest tag

Verdict, first match wins:
  maintained    the policy says supported, or it is the current line
  unmaintained  the policy says not supported
  likely        a maintenance branch with a commit in the last --active-days,
                or an npm dist-tag other than latest points into it
  unmaintained  none of the above

The verdict is a reading of the repo, not the maintainers' word. When the repo
has no support policy, say so in the issue and name the evidence.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")
BRANCH = re.compile(r"^(?:release[/-]|releases/|maint(?:enance)?[/-]|lts[/-])?v?(\d+)(?:\.(\d+|x))?(?:\.x)?$")
POLICY_FILES = ("SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md", "SUPPORT.md", ".github/SUPPORT.md")
YES = re.compile(r"✅|:white_check_mark:|:heavy_check_mark:|✔|\byes\b|\bsupported\b|\bactive\b|\blts\b", re.I)
NO = re.compile(r"❌|:x:|✗|✖|\bno\b|\bunsupported\b|\bnot supported\b|\bend[- ]of[- ]life\b|\beol\b|\bdeprecated\b", re.I)


def git(cwd, *args):
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def line_of(major, minor):
    """The release line a version belongs to."""
    return f"0.{minor}.x" if major == 0 else f"{major}.x"


def read_policy(cwd):
    """Rows of the support table: (spec, supported or None, file)."""
    rows = []
    for name in POLICY_FILES:
        path = Path(cwd) / name
        if not path.is_file():
            continue
        for raw in path.read_text(errors="replace").splitlines():
            cells = [c.strip() for c in raw.strip().strip("|").split("|")]
            if len(cells) < 2 or not re.search(r"\d", cells[0]) or set(raw.strip()) <= set("|-: "):
                continue
            rest = " ".join(cells[1:])
            # Check "no" first: "not supported" contains "supported".
            state = False if NO.search(rest) else True if YES.search(rest) else None
            if state is not None:
                rows.append({"spec": cells[0], "supported": state, "file": name})
        if rows:
            break
    return rows


def spec_matches(spec, major, minor):
    """Does a support-table spec such as '5.x', '4.1.x', '>= 3.0' or '< 2' cover the line?"""
    m = re.search(r"(>=|<=|>|<)?\s*v?(\d+)(?:\.(\d+|x|\*))?", spec)
    if not m:
        return False
    op, smaj, smin = m.group(1), int(m.group(2)), m.group(3)
    smin = int(smin) if smin and smin.isdigit() else None
    key = (major, minor) if major == 0 else (major, 0)
    skey = (smaj, smin or 0) if smaj == 0 else (smaj, 0)
    if op == ">=":
        return key >= skey
    if op == ">":
        return key > skey
    if op == "<=":
        return key <= skey
    if op == "<":
        return key < skey
    if major == 0 and smaj == 0 and smin is not None:
        return smin == minor
    return smaj == major


def default_branch(cwd):
    head = git(cwd, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    if head:
        return head.split("/", 1)[1]
    names = git(cwd, "branch", "--format=%(refname:short)").splitlines()
    for b in ("main", "master", "trunk"):
        if b in names:
            return b
    return git(cwd, "branch", "--show-current") or "main"


def package_version(cwd, ref):
    text = git(cwd, "show", f"{ref}:package.json")
    try:
        data = json.loads(text) if text else {}
    except json.JSONDecodeError:
        return None, None, False
    m = SEMVER.match(str(data.get("version", "")))
    version = (int(m.group(1)), int(m.group(2))) if m else None
    return version, data.get("name"), bool(data.get("private"))


def npm_dist_tags(name):
    try:
        r = subprocess.run(["npm", "view", name, "dist-tags", "--json"], capture_output=True, text=True, timeout=20)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}
    if r.returncode != 0:
        return {}
    try:
        data = json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--offline", action="store_true", help="skip the npm registry")
    ap.add_argument("--package", help="npm package name (default: package.json name, unless private)")
    ap.add_argument("--active-days", type=int, default=365)
    args = ap.parse_args()
    cwd = Path(args.cwd)
    if not git(cwd, "rev-parse", "--git-dir"):
        sys.exit(f"not a git repo: {cwd}")

    lines = {}

    def entry(major, minor):
        key = line_of(major, minor)
        return lines.setdefault(key, {"line": key, "major": major, "minor": minor if major == 0 else None,
                                      "branch": None, "branch_date": None, "tag": None, "tag_date": None,
                                      "dist_tags": [], "policy": None, "current": False})

    # Tags: the newest of each line.
    for raw in git(cwd, "tag", "--list", "--format=%(refname:short) %(creatordate:iso-strict)").splitlines():
        name, _, date = raw.partition(" ")
        m = SEMVER.match(name)
        if not m:
            continue
        v = tuple(int(x) for x in m.groups())
        e = entry(v[0], v[1])
        if e["tag"] is None or v > e["_v"]:
            e["tag"], e["tag_date"], e["_v"] = name, date, v

    # Maintenance branches, local and remote.
    default = default_branch(cwd)
    seen = set()
    for raw in git(cwd, "branch", "-a", "--format=%(refname:short) %(committerdate:iso-strict)").splitlines():
        ref, _, date = raw.partition(" ")
        name = re.sub(r"^origin/", "", ref)
        m = BRANCH.match(name)
        if not m or name in seen:
            continue
        seen.add(name)
        major = int(m.group(1))
        minor = int(m.group(2)) if m.group(2) and m.group(2).isdigit() else 0
        if major == 0 and not (m.group(2) and m.group(2).isdigit()):
            continue
        e = entry(major, minor)
        if e["branch_date"] is None or date > e["branch_date"]:
            e["branch"], e["branch_date"] = name, date

    # The current line: the default branch's package.json, else the newest tag.
    current, pkg_name, private = package_version(cwd, default)
    if current is None and any(e.get("_v") for e in lines.values()):
        newest = max(e["_v"] for e in lines.values() if e.get("_v"))
        current = newest[:2]
    if current is not None:
        e = entry(*current)
        e["current"] = True
        e["current_ref"] = default

    # npm dist-tags.
    name = args.package or (None if private else pkg_name)
    registry = None
    if name and not args.offline:
        tags = npm_dist_tags(name)
        registry = name if tags else None
        for tag, version in sorted(tags.items()):
            m = SEMVER.match(str(version))
            if m:
                entry(int(m.group(1)), int(m.group(2)))["dist_tags"].append(f"{tag}={version}")

    # Support policy.
    policy = read_policy(cwd)
    for e in lines.values():
        for row in policy:
            if spec_matches(row["spec"], e["major"], e["minor"] or 0):
                e["policy"] = {"spec": row["spec"], "supported": row["supported"], "file": row["file"]}
                break

    # Verdicts.
    now = datetime.now(timezone.utc)
    for e in lines.values():
        e.pop("_v", None)
        active = False
        if e["branch_date"]:
            try:
                age = (now - datetime.fromisoformat(e["branch_date"])).days
                active = age <= args.active_days
            except ValueError:
                pass
        other_tag = any(not t.startswith("latest=") for t in e["dist_tags"])
        if e["policy"] and e["policy"]["supported"]:
            e["verdict"], e["why"] = "maintained", f"{e['policy']['file']} supports {e['policy']['spec']}"
        elif e["current"]:
            e["verdict"], e["why"] = "maintained", f"current line ({default})"
        elif e["policy"]:
            e["verdict"], e["why"] = "unmaintained", f"{e['policy']['file']} does not support {e['policy']['spec']}"
        elif active:
            e["verdict"], e["why"] = "likely", f"branch {e['branch']} has commits in the last {args.active_days} days"
        elif other_tag:
            e["verdict"], e["why"] = "likely", "npm dist-tag " + ", ".join(t for t in e["dist_tags"] if not t.startswith("latest="))
        else:
            e["verdict"], e["why"] = "unmaintained", "no support row, no active branch, no dist-tag"

    ordered = sorted(lines.values(), key=lambda e: (e["major"], e["minor"] or 0), reverse=True)
    out = {"default_branch": default, "policy_file": policy[0]["file"] if policy else None,
           "registry_package": registry, "lines": ordered}
    if args.json:
        print(json.dumps(out, indent=2))
        return
    print(f"default branch: {default}")
    print(f"support policy: {out['policy_file'] or 'none found'}")
    if name and not args.offline:
        print(f"npm: {registry or name + ' (no dist-tags found)'}")
    for e in ordered:
        where = [x for x in (e["branch"] and f"branch {e['branch']}", e["tag"] and f"tag {e['tag']}") if x]
        where += e["dist_tags"]
        print(f"{e['line']:<10} {e['verdict']:<13} {e['why']}" + (f"  [{', '.join(where)}]" if where else ""))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Say whether pushing a branch or opening a pull request will start CI runs.

Usage:
  ci_guard.py [--visibility private|public|internal]   # default: ask gh

Reads .github/workflows/*.yml for push and pull_request triggers, and the repo's
visibility. GitHub Actions minutes are billed on private repos, so the result for
a private repo with such triggers is "ask": do not push until the user says so.

Prints JSON: visibility, the workflows that would run, and a verdict:
  safe   no workflow would run, or the repo is public
  ask    private repo, and a push or pull request would start workflows
Exit code 0 for safe, 2 for ask.

Each pull_request workflow also says whether it skips draft pull requests
(skips_drafts). A draft only saves CI runs when its workflows skip drafts.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path


def visibility():
    try:
        r = subprocess.run(["gh", "repo", "view", "--json", "visibility", "--jq", ".visibility"],
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip().lower() or "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def triggered_workflows(root):
    found = []
    for f in sorted(Path(root, ".github", "workflows").glob("*.y*ml")):
        text = f.read_text()
        block = re.search(r"^(?:on|\"on\"|'on'|true):(.*?)(?=^\S)", text + "\nend:", re.M | re.S)
        on = block.group(1) if block else ""
        inline = re.search(r"^on:\s*(\[.*\]|\S+)\s*$", text, re.M)
        triggers = set(re.findall(r"\b(push|pull_request|pull_request_target)\b",
                                  (inline.group(1) if inline else "") + on))
        if triggers:
            entry = {"file": str(f.relative_to(root)), "triggers": sorted(triggers)}
            if triggers & {"pull_request", "pull_request_target"}:
                entry["skips_drafts"] = "pull_request.draft" in text
            found.append(entry)
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--visibility")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    vis = (args.visibility or visibility()).lower()
    workflows = triggered_workflows(args.root)
    ask = bool(workflows) and vis in ("private", "internal", "unknown")
    out = {"visibility": vis, "workflows": workflows, "verdict": "ask" if ask else "safe"}
    on_drafts = [w["file"] for w in workflows if w.get("skips_drafts") is False]
    if on_drafts:
        out["runs_on_drafts"] = on_drafts
    if ask:
        out["advice"] = ("Pushing would start billed CI runs. Ask the user before pushing. "
                         "Run the checks locally instead, and keep the branch local until they decide.")
    print(json.dumps(out, indent=2))
    raise SystemExit(2 if ask else 0)


if __name__ == "__main__":
    main()

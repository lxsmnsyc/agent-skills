#!/usr/bin/env python3
"""List what a repo has and lacks against the repo-setup layout.

Usage:
  audit.py [root] [--offline] [--json]

Checks the package manager, changesets, the bundler, the test runner, oxlint and
oxfmt, the license, the check and release workflows, the folders, and each
publishable package. Without --offline it asks npm whether each package exists,
which decides whether it needs the manual 0.0.0-stage publish.

Each finding has a status:
  ok        matches the setup
  missing   add it
  migrate   something else is there; replace it
  info      not a change, but the setup step needs to know it

Prints a table, or JSON with --json. Exit code 0 when every finding is ok or
info, 1 otherwise.
"""
import argparse
import glob
import json
import re
import subprocess
from pathlib import Path

OTHER_LINTERS = ["biome.json", "biome.jsonc", ".eslintrc", ".eslintrc.js", ".eslintrc.cjs",
                 ".eslintrc.json", "eslint.config.js", "eslint.config.mjs", "eslint.config.ts",
                 ".prettierrc", ".prettierrc.json", ".prettierrc.js", "prettier.config.js"]
OTHER_BUNDLERS = ["tsup", "rollup", "unbuild", "microbundle", "esbuild"]
OTHER_RUNNERS = ["jest", "mocha", "ava", "uvu"]


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def workspace_globs(root):
    ws = root / "pnpm-workspace.yaml"
    if ws.exists():
        globs, inside = [], False
        for line in ws.read_text().splitlines():
            if re.match(r"^packages:\s*$", line):
                inside = True
                continue
            if inside:
                m = re.match(r"^\s+-\s+['\"]?([^'\"#]+?)['\"]?\s*(#.*)?$", line)
                if m:
                    globs.append(m.group(1))
                elif line.strip() and not line.lstrip().startswith("#"):
                    inside = False
        return globs
    pkg = read_json(root / "package.json") or {}
    ws = pkg.get("workspaces", [])
    return ws.get("packages", []) if isinstance(ws, dict) else ws


def packages(root):
    found = []
    for pattern in workspace_globs(root):
        if pattern.startswith("!"):
            continue
        for d in sorted(glob.glob(str(root / pattern))):
            pj = read_json(Path(d) / "package.json")
            if pj is not None:
                found.append((Path(d), pj))
    if not found:
        pj = read_json(root / "package.json")
        if pj is not None:
            found.append((root, pj))
    return found


def deps(pj):
    out = {}
    for key in ("dependencies", "devDependencies"):
        out.update(pj.get(key) or {})
    return out


def on_npm(name):
    try:
        r = subprocess.run(["npm", "view", name, "version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode == 0 and r.stdout.strip():
        return True
    if "E404" in r.stderr or "404" in r.stderr:
        return False
    return None


def workflows(root):
    out = {}
    for f in sorted((root / ".github" / "workflows").glob("*.y*ml")):
        out[f.name] = f.read_text()
    return out


def audit(root, offline=False):
    findings = []

    def add(check, status, detail=""):
        findings.append({"check": check, "status": status, "detail": detail})

    pj = read_json(root / "package.json") or {}
    all_deps = dict(deps(pj))
    pkgs = packages(root)
    for _, p in pkgs:
        all_deps.update(deps(p))

    pm = pj.get("packageManager", "")
    if pm.startswith("pnpm@") and (root / "pnpm-lock.yaml").exists():
        add("pnpm", "ok", pm)
    elif (root / "package-lock.json").exists() or (root / "yarn.lock").exists() or (root / "bun.lock").exists():
        add("pnpm", "migrate", "another lockfile is present")
    else:
        add("pnpm", "missing", "set packageManager to pnpm@<latest> and install")
    if len(pkgs) > 1 or (root / "packages").is_dir():
        add("pnpm workspace", "ok" if (root / "pnpm-workspace.yaml").exists() else "missing")

    cs = read_json(root / ".changeset" / "config.json")
    add("changesets", "ok" if cs is not None else "missing")

    publishable = [(d, p) for d, p in pkgs if not p.get("private")]
    for d, p in publishable:
        rel = d.relative_to(root).as_posix() or "."
        name = p.get("name", rel)
        if glob.glob(str(d / "tsdown.config.*")):
            add(f"tsdown: {name}", "ok")
        else:
            other = [b for b in OTHER_BUNDLERS if b in deps(p) or glob.glob(str(d / f"{b}.config.*"))]
            if other:
                add(f"tsdown: {name}", "migrate", ", ".join(other))
            elif "build" not in (p.get("scripts") or {}):
                add(f"tsdown: {name}", "info", "no build step; the package ships its source")
            else:
                add(f"tsdown: {name}", "missing")
        if not offline and name:
            exists = on_npm(name)
            if exists is False:
                add(f"npm: {name}", "info", "not on npm: needs the manual 0.0.0-stage publish")
            elif exists is None:
                add(f"npm: {name}", "info", "could not ask npm")

    runners = [r for r in OTHER_RUNNERS if r in all_deps]
    if "vitest" in all_deps:
        add("vitest", "migrate" if runners else "ok", ", ".join(runners))
    else:
        add("vitest", "migrate" if runners else "missing", ", ".join(runners))

    ox = next((root / n for n in ("oxlint.config.ts", ".oxlintrc.json") if (root / n).exists()), None)
    if ox is None:
        add("oxlint", "missing")
    elif "@lxsmnsyc/oxlint-config" not in ox.read_text():
        add("oxlint", "migrate", f"{ox.name} does not extend @lxsmnsyc/oxlint-config")
    else:
        add("oxlint", "ok")
    has_oxfmt = any((root / n).exists() for n in ("oxfmt.config.ts", ".oxfmtrc.json"))
    add("oxfmt", "ok" if has_oxfmt else "missing")
    others = [n for n in OTHER_LINTERS if (root / n).exists()]
    if others:
        add("other linters", "migrate", ", ".join(others))

    lic = root / "LICENSE"
    if not lic.exists():
        add("license", "missing")
    else:
        mit = "MIT License" in lic.read_text()[:200]
        add("license", "ok" if mit else "migrate", "" if mit else "not MIT")

    wf = workflows(root)
    check = [n for n, t in wf.items() if "pull_request" in t and re.search(r"\b(test|vitest)\b", t)]
    if not check:
        add("check workflow", "missing", "lint, format, types and tests on pull requests")
    else:
        text = "".join(wf[n] for n in check)
        gaps = [w for w, pat in (("lint", r"oxlint|\blint\b"), ("format", r"oxfmt|format"),
                                 ("types", r"tsc|typecheck"), ("tests", r"\btest\b|vitest"))
                if not re.search(pat, text)]
        add("check workflow", "migrate" if gaps else "ok",
            ", ".join(check) + (f" lacks {', '.join(gaps)}" if gaps else ""))
    release = [n for n, t in wf.items() if "changeset" in t]
    if not release:
        add("release workflow", "missing")
    else:
        text = "".join(wf[n] for n in release)
        if "NPM_TOKEN" in text or "NODE_AUTH_TOKEN" in text:
            add("release workflow", "migrate", "uses an npm token; switch to trusted publishing")
        elif "id-token: write" not in text:
            add("release workflow", "migrate", "no id-token: write")
        else:
            add("release workflow", "ok", ", ".join(release))
        envs = sorted(set(re.findall(r"^\s+environment:\s*(\S+)", text, re.M)))
        if envs:
            add("environments", "info", ", ".join(envs))

    for folder in ("examples", "benchmarks", "docs"):
        if (root / folder).is_dir():
            add(f"{folder}/", "ok")
        elif folder == "benchmarks" and (root / "benchmark").is_dir():
            add("benchmarks/", "migrate", "rename benchmark/ to benchmarks/")
        else:
            add(f"{folder}/", "info", "absent")
    if (root / "website").is_dir():
        add("website vercel.json", "ok" if (root / "website" / "vercel.json").exists() else "missing")
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    findings = audit(Path(args.root).resolve(), args.offline)
    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        width = max(len(f["check"]) for f in findings)
        for f in findings:
            print(f"{f['status']:<8} {f['check']:<{width}}  {f['detail']}".rstrip())
    return 0 if all(f["status"] in ("ok", "info") for f in findings) else 1


if __name__ == "__main__":
    raise SystemExit(main())

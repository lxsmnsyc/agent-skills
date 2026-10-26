#!/usr/bin/env python3
"""Find and run the checks a project expects before merging: lint, typecheck,
build and tests. Runs locally, so it never starts CI.

Usage:
  checks.py <dir>                 # list the detected checks
  checks.py <dir> --run           # run them and report pass or fail
  checks.py <dir> --run --install # install dependencies first (new worktrees need this)
  checks.py <dir> --run --only lint,typecheck

Detects package.json scripts (npm, pnpm, yarn, bun by lockfile), Makefile
targets, Cargo, Go and Python (ruff, mypy, pytest) projects.
"""
import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path

KINDS = ("lint", "format", "typecheck", "build", "test")
SCRIPT_NAMES = {
    "lint": ["lint", "check:lint", "lint:check"],
    "format": ["format:check", "fmt:check", "check:format"],
    "typecheck": ["typecheck", "type-check", "check:types", "types", "tsc"],
    "build": ["build"],
    "test": ["test", "test:unit"],
}


def node_checks(d):
    pkg = json.loads((d / "package.json").read_text())
    scripts = pkg.get("scripts", {})
    pm = ("pnpm" if (d / "pnpm-lock.yaml").exists() else "yarn" if (d / "yarn.lock").exists()
          else "bun" if (d / "bun.lockb").exists() or (d / "bun.lock").exists() else "npm")
    install = {"pnpm": "pnpm install --frozen-lockfile", "yarn": "yarn install --frozen-lockfile",
               "bun": "bun install --frozen-lockfile", "npm": "npm ci"}[pm]
    found = {}
    for kind, names in SCRIPT_NAMES.items():
        for n in names:
            if n in scripts:
                found[kind] = f"{pm} run {n}"
                break
    if "typecheck" not in found and (d / "tsconfig.json").exists():
        found["typecheck"] = f"{pm} exec tsc --noEmit"
    return install, found


def make_checks(d):
    targets = set(re.findall(r"^([A-Za-z][\w-]*):", (d / "Makefile").read_text(), re.M))
    return None, {k: f"make {k}" for k in KINDS if k in targets}


def detect(d):
    d = Path(d)
    if (d / "package.json").exists():
        return node_checks(d)
    if (d / "Cargo.toml").exists():
        return "cargo fetch", {"lint": "cargo clippy -- -D warnings", "format": "cargo fmt --check",
                               "build": "cargo build", "test": "cargo test"}
    if (d / "go.mod").exists():
        return "go mod download", {"lint": "go vet ./...", "build": "go build ./...",
                                   "test": "go test ./..."}
    if (d / "pyproject.toml").exists():
        text = (d / "pyproject.toml").read_text()
        found = {}
        if "ruff" in text:
            found["lint"] = "ruff check ."
        if "mypy" in text:
            found["typecheck"] = "mypy ."
        if "pytest" in text or (d / "tests").exists():
            found["test"] = "pytest -q"
        return None, found
    if (d / "Makefile").exists():
        return make_checks(d)
    return None, {}


def run(cmd, cwd, timeout):
    start = time.time()
    try:
        # CI=1 makes test runners such as vitest and jest run once instead of watching.
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "CI": "1"})
        ok, tail = r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-15:]
    except subprocess.TimeoutExpired:
        ok, tail = False, [f"timeout after {timeout}s"]
    return {"command": cmd, "passed": ok, "seconds": round(time.time() - start, 1), "tail": tail}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    install, found = detect(args.dir)
    if args.only:
        keep = set(args.only.split(","))
        found = {k: v for k, v in found.items() if k in keep}
    if not args.run:
        out = {"install": install, "checks": found, "missing": [k for k in KINDS if k not in found]}
        print(json.dumps(out, indent=2) if args.json else
              "\n".join([f"install: {install}"] + [f"{k}: {v}" for k, v in found.items()]
                        + [f"missing: {', '.join(out['missing']) or 'none'}"]))
        return
    results = {}
    if args.install and install:
        results["install"] = run(install, args.dir, args.timeout)
        if not results["install"]["passed"]:
            found = {}
    for kind in KINDS:
        if kind in found:
            results[kind] = run(found[kind], args.dir, args.timeout)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for kind, r in results.items():
            print(f"{kind}: {'pass' if r['passed'] else 'FAIL'} ({r['seconds']}s) {r['command']}")
            if not r["passed"]:
                for line in r["tail"]:
                    print(f"    {line}")
    raise SystemExit(0 if all(r["passed"] for r in results.values()) else 1)


if __name__ == "__main__":
    main()

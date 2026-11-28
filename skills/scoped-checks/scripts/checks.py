#!/usr/bin/env python3
"""Find and run the checks a project expects before merging: lint, typecheck,
build and tests. Runs locally, so it never starts CI.

Usage:
  checks.py <dir>                    # list the detected checks
  checks.py <dir> --run              # run them and report pass or fail
  checks.py <dir> --run --install    # install dependencies first (new worktrees need this)
  checks.py <dir> --run --only lint,typecheck
  checks.py <dir> --run --changed    # only what the change touches, against the default branch
  checks.py <dir> --run --changed main

Detects package.json scripts (npm, pnpm, yarn, bun by lockfile), Makefile
targets, Cargo, Go and Python (ruff, mypy, pytest) projects.

--changed takes the files changed since the merge base with the base branch,
plus uncommitted and untracked files, and scopes each check to them:
  lint, format  the linter or formatter on the changed files only
  test          vitest related, jest --findRelatedTests, or the test files
                named after a changed file (pytest, node --test)
  typecheck, build
                the packages that hold a changed file, and in a pnpm
                workspace their dependents too
A change to a config file (package.json, lockfile, tsconfig, *.config.*,
pyproject.toml and the like) runs the full check for its package, or for the
whole project when the file is at the root. A check whose command cannot be
scoped runs in full. A check with no related files is skipped.
"""
import argparse
import json
import os
import re
import shlex
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


LINT_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts", ".vue", ".svelte", ".astro"}
FMT_EXTS = LINT_EXTS | {".json", ".jsonc", ".md", ".mdx", ".css", ".scss", ".less", ".html", ".yaml", ".yml",
                        ".graphql", ".toml"}
PY_EXTS = {".py", ".pyi"}
# Tools that take file arguments, with the extensions they read.
FILE_TOOLS = {"oxlint": LINT_EXTS, "eslint": LINT_EXTS, "oxfmt": FMT_EXTS, "prettier": FMT_EXTS,
              "biome": FMT_EXTS, "ruff": PY_EXTS, "mypy": PY_EXTS}
CONFIG_NAMES = {"package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml", "yarn.lock", "package-lock.json",
                "bun.lock", "bun.lockb", "pyproject.toml", "setup.cfg", "setup.py", "requirements.txt",
                "uv.lock", "poetry.lock", "Cargo.toml", "Cargo.lock", "go.mod", "go.sum", "Makefile",
                ".editorconfig", ".prettierignore", ".eslintignore"}
CONFIG_RE = re.compile(r"^(tsconfig.*\.json|.*\.config\.[cm]?[jt]s|.*\.config\.json|\.[\w-]+rc(\.\w+)?|"
                       r"vitest\.workspace\.\w+|conftest\.py)$")
MAX_FILES = 400


def git(d, *args):
    r = subprocess.run(["git", *args], cwd=d, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def find_base(d, base):
    """The merge base of HEAD with the base branch, or None when no base is found."""
    candidates = [base] if base != "auto" else []
    if base == "auto":
        head = git(d, "rev-parse", "--abbrev-ref", "origin/HEAD")
        candidates += [head] if head else []
        candidates += ["origin/main", "main", "origin/master", "master"]
    for ref in candidates:
        mb = git(d, "merge-base", "HEAD", ref)
        if mb:
            return mb
    return None


def changed_files(d, mb):
    """Files under d changed since mb, committed or not, plus untracked files. Deleted files are left out."""
    tracked = git(d, "diff", "--name-only", "--relative", "--diff-filter=d", mb) or ""
    untracked = git(d, "ls-files", "--others", "--exclude-standard") or ""
    return sorted({f for f in (tracked + "\n" + untracked).splitlines() if f})


def is_config(rel):
    name = Path(rel).name
    return name in CONFIG_NAMES or bool(CONFIG_RE.match(name))


def package_of(d, rel):
    """The nearest folder at or above rel, inside d, that holds a package.json. "" is d itself."""
    p = Path(rel).parent
    while str(p) not in ("", "."):
        if (d / p / "package.json").exists():
            return str(p)
        p = p.parent
    return ""


def script_for(pkg_json, kind):
    scripts = json.loads(pkg_json.read_text()).get("scripts", {}) if pkg_json.exists() else {}
    for n in SCRIPT_NAMES[kind]:
        if n in scripts:
            return n, scripts[n]
    return None, None


TEST_RE = re.compile(r"(\.(test|spec)\.[^.]+$|^test_.*\.py$|_test\.py$)")


def strip_test_affix(name):
    """sum.test.js -> sum, test_sum.py -> sum, sum_test.py -> sum."""
    stem = name.split(".")[0]
    return re.sub(r"^test_|_test$", "", stem)


def test_files_for(d, pkg, files):
    """Changed test files, plus the test files named after each changed source file."""
    tests, stems = set(), set()
    for f in files:
        if TEST_RE.search(Path(f).name):
            tests.add(f)
        else:
            stems.add(Path(f).name.split(".")[0])
    if stems:
        for t in (git(d / pkg if pkg else d, "ls-files") or "").splitlines():
            name = Path(t).name
            if TEST_RE.search(name) and strip_test_affix(name) in stems:
                tests.add(str(Path(pkg) / t) if pkg else t)
    return sorted(tests)


def scope_command(d, pkg, body, kind, files, pm):
    """A command that runs the script body on files only, or None when it cannot be scoped."""
    if re.search(r"&&|\|\||;|\|", body):
        return None
    tokens = shlex.split(body)
    if not tokens:
        return None
    tool = Path(tokens[0]).name
    base = d / pkg if pkg else d
    # Drop folder, glob and "." targets; keep flags and their file values such as a config path.
    kept = [t for t in tokens[1:] if t.startswith("-") or ("*" not in t and t != "." and not (base / t).is_dir())]
    rel = [os.path.relpath(f, pkg) if pkg else f for f in files]
    run = f"{pm} exec " if pm else ""
    if kind in ("lint", "format", "typecheck") and tool in FILE_TOOLS:
        if kind == "typecheck" and tool != "mypy":
            return None
        rel = [f for f in rel if Path(f).suffix in FILE_TOOLS[tool]]
        if not rel:
            return ""
        if tool == "prettier" and "--ignore-unknown" not in kept:
            kept.append("--ignore-unknown")
        return f"{run}{tool} {' '.join(kept)} {' '.join(shlex.quote(f) for f in rel)}".replace("  ", " ")
    if kind == "test" and tool == "vitest":
        kept = [t for t in kept if t not in ("run", "watch", "related")]
        src = [f for f in rel if Path(f).suffix in LINT_EXTS]
        if not src:
            return ""
        return (f"{run}vitest related --run --passWithNoTests {' '.join(kept)} "
                f"{' '.join(shlex.quote(f) for f in src)}").replace("  ", " ")
    if kind == "test" and tool == "jest":
        src = [f for f in rel if Path(f).suffix in LINT_EXTS]
        if not src:
            return ""
        return (f"{run}jest --findRelatedTests --passWithNoTests {' '.join(kept)} "
                f"{' '.join(shlex.quote(f) for f in src)}").replace("  ", " ")
    if kind == "test" and (tool == "pytest" or (tool == "node" and "--test" in tokens)):
        tests = [os.path.relpath(t, pkg) if pkg else t for t in test_files_for(d, pkg, files)]
        if not tests:
            return ""
        prefix = "pytest" if tool == "pytest" else "node"
        return f"{prefix} {' '.join(kept)} {' '.join(shlex.quote(t) for t in tests)}".replace("  ", " ")
    return None


def node_scoped(d, kind, full_cmd, files, pm):
    """Scoped commands for a node project as a list of (command, cwd, scope)."""
    groups = {}
    for f in files:
        groups.setdefault(package_of(d, f), []).append(f)
    workspace = pm == "pnpm" and (d / "pnpm-workspace.yaml").exists()
    if kind in ("typecheck", "build"):
        pkgs = [p for p in groups if p]
        named = {script_for(d / p / "package.json", kind)[0] for p in pkgs} - {None}
        if "" in groups or not named:
            # A changed file in the root package, or no package with its own script: run in full.
            return [(full_cmd, d, "full (root package changed or no package script)")]
        if workspace and len(named) == 1:
            mb = os.environ["CHECKS_MERGE_BASE"]
            name = named.pop()
            return [(f'pnpm --filter "...[{mb}]" --if-present run {name}', d,
                     "changed packages and their dependents")]
        out = []
        for p in sorted(pkgs):
            name, _ = script_for(d / p / "package.json", kind)
            out.append((f"{pm} run {name}", d / p, p) if name else (full_cmd, d, "full"))
        return list(dict.fromkeys(out))
    # Files in a package without its own script fall back to the root script, in one command.
    by_script = {}
    for pkg, pfiles in sorted(groups.items()):
        own = script_for(d / pkg / "package.json", kind) if pkg else (None, None)
        if own[1]:
            key = (pkg, *own)
        else:
            key = ("", *script_for(d / "package.json", kind))
        if key[2]:
            by_script.setdefault(key, []).extend(pfiles)
    out = []
    for (pkg, name, body), pfiles in by_script.items():
        cwd, label = (d / pkg if pkg else d), pkg or "root"
        if any(is_config(f) for f in pfiles):
            out.append((f"{pm} run {name}", cwd, f"{label} in full (config changed)"))
            continue
        cmd = scope_command(d, pkg, body, kind, pfiles, pm)
        if cmd is None:
            out.append((f"{pm} run {name}", cwd, f"{label} in full (script cannot be scoped)"))
        elif cmd:
            out.append((cmd, cwd, f"{len(pfiles)} changed file(s), {label} script"))
    return out


def python_scoped(d, kind, full_cmd, files):
    cmd = scope_command(d, "", full_cmd, kind, files, None)
    if cmd is None:
        return [(full_cmd, d, "full (command cannot be scoped)")]
    return [(cmd, d, f"{len(files)} changed file(s)")] if cmd else []


def go_scoped(d, kind, full_cmd, files):
    """go vet, build and test on the packages that hold a changed .go file. Callers are not included."""
    dirs = sorted({"./" + str(Path(f).parent) for f in files if f.endswith(".go")})
    if not dirs:
        return []
    if "./..." not in full_cmd:
        return [(full_cmd, d, "full (command cannot be scoped)")]
    return [(full_cmd.replace("./...", " ".join(dirs)), d, f"{len(dirs)} changed package(s)")]


def plan_changed(d, found, files, pm):
    """Map each check to a list of (command, cwd, scope) for the changed files."""
    plan = {}
    root_config = [f for f in files if is_config(f) and "/" not in f]
    for kind, full_cmd in found.items():
        if root_config or len(files) > MAX_FILES:
            why = f"config changed: {', '.join(root_config)}" if root_config else f"over {MAX_FILES} files"
            plan[kind] = [(full_cmd, d, f"full ({why})")]
        elif (d / "package.json").exists():
            plan[kind] = node_scoped(d, kind, full_cmd, files, pm)
        elif (d / "pyproject.toml").exists():
            plan[kind] = python_scoped(d, kind, full_cmd, files)
        elif (d / "go.mod").exists():
            plan[kind] = go_scoped(d, kind, full_cmd, files)
        else:
            plan[kind] = [(full_cmd, d, "full (no scoping for this project type)")]
    return plan


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
    ap.add_argument("--changed", nargs="?", const="auto", metavar="BASE",
                    help="scope checks to files changed since the merge base with BASE (default: the default branch)")
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    install, found = detect(args.dir)
    if args.only:
        keep = set(args.only.split(","))
        found = {k: v for k, v in found.items() if k in keep}
    d = Path(args.dir).resolve()
    plan = None
    if args.changed:
        mb = find_base(d, args.changed)
        if not mb:
            raise SystemExit(f"no merge base with {args.changed}; pass the base branch, as in --changed main")
        os.environ["CHECKS_MERGE_BASE"] = mb
        files = changed_files(d, mb)
        if not files:
            print("no changed files: nothing to check")
            return
        pm = found and next(iter(found.values())).split()[0]
        pm = pm if pm in ("pnpm", "yarn", "bun", "npm") else None
        plan = plan_changed(d, found, files, pm)
    if not args.run:
        if plan is not None:
            out = {k: [{"command": c, "cwd": str(w), "scope": sc} for c, w, sc in v] for k, v in plan.items()}
            if args.json:
                print(json.dumps({"install": install, "files": files, "checks": out}, indent=2))
            else:
                print(f"install: {install}\nchanged files: {len(files)}")
                for k, v in out.items():
                    for e in v or [{"command": "skipped", "scope": "no related files", "cwd": ""}]:
                        print(f"{k}: {e['command']}  [{e['scope']}]")
            return
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
        if kind not in found:
            continue
        if plan is None:
            results[kind] = run(found[kind], args.dir, args.timeout)
            continue
        steps = plan.get(kind, [])
        if not steps:
            results[kind] = {"command": "skipped: no related files", "passed": True, "seconds": 0, "tail": []}
        for i, (cmd, cwd, scope) in enumerate(steps):
            r = run(cmd, cwd, args.timeout)
            r["scope"] = scope
            results[kind if len(steps) == 1 else f"{kind} {i + 1}"] = r
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for kind, r in results.items():
            scope = f"  [{r['scope']}]" if r.get("scope") else ""
            print(f"{kind}: {'pass' if r['passed'] else 'FAIL'} ({r['seconds']}s) {r['command']}{scope}")
            if not r["passed"]:
                for line in r["tail"]:
                    print(f"    {line}")
    raise SystemExit(0 if all(r["passed"] for r in results.values()) else 1)


if __name__ == "__main__":
    main()

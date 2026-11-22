#!/usr/bin/env python3
"""Gather the facts for a change's risk rating: reach, public API, data, dependencies, tests.

Usage:
  risk.py --base main [--head HEAD] [--json]

Reads `git diff <base>...<head>` and the head tree. It does not run anything.

Facts:
  symbols        names declared or edited in the diff (functions, classes, consts, types),
                 with the non-test files outside the diff that use each one (its callers)
  callers        distinct non-test files outside the diff that use any changed symbol
  exports        exported names on changed lines, and whether they sit in an entry file
                 (index.*, mod.ts, __init__.py, or a source file named in package.json)
  data           changed migrations, schemas, SQL, protobuf or GraphQL files
  dependencies   changed package manifests or lockfiles
  untested       changed source files that no test file names
  lines          lines added and removed

The suggested rating is a floor, not a verdict. Raise it for what the facts cannot see, such
as a hot path, concurrency or security code. Lower it only with a reason in the PR.

  high    an entry-file export changed, data or format files changed, or 20+ callers
  medium  5+ callers, an export changed, dependencies changed, untested files, or 400+ lines
  low     none of the above
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

CODE = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".py", ".rs", ".go"}
TEST = re.compile(r"(^|/)(tests?|__tests__|e2e)/|[._-](test|spec)\.[^/]+$|(^|/)test_[^/]+\.py$")
DATA = re.compile(r"(^|/)migrations?/|\.(sql|prisma|proto|graphql|gql)$|(^|/)schema\.[^/]+$")
DEPS = re.compile(r"(^|/)(package\.json|pnpm-lock\.yaml|package-lock\.json|yarn\.lock|bun\.lockb?"
                  r"|Cargo\.(toml|lock)|go\.(mod|sum)|pyproject\.toml|requirements[^/]*\.txt|uv\.lock)$")
ENTRY = re.compile(r"(^|/)(index\.(m|c)?[jt]sx?|mod\.ts|__init__\.py|lib\.rs)$")
DECL = [
    re.compile(r"\bfunction\*?\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"\b(?:const|let|var|class|interface|type|enum)\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"\b(?:def|class)\s+([A-Za-z_]\w*)"),
    re.compile(r"\bfn\s+([A-Za-z_]\w*)"),
    re.compile(r"\bfunc\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)"),
]
EXPORT = re.compile(r"^\s*(?:export\s+(?:default\s+)?(?:async\s+)?(?:function\*?|const|let|var|class|"
                    r"interface|type|enum)\s+([A-Za-z_$][\w$]*)|export\s*\{([^}]*)\}|pub\s+(?:fn|struct|enum|"
                    r"trait|const)\s+([A-Za-z_]\w*))")
# Names too common to say anything about reach.
SKIP = {"default", "props", "state", "data", "value", "result", "index", "main", "init", "self", "this",
        "test", "it", "describe", "expect", "options", "config", "type"}


def git(repo, *argv):
    r = subprocess.run(["git", *argv], cwd=repo, capture_output=True, text=True)
    if r.returncode not in (0, 1):
        sys.exit(f"git {' '.join(argv)}: {r.stderr.strip()}")
    return r.stdout


def parse_diff(text):
    """Changed files with their added and removed lines and hunk headers."""
    files, cur = {}, None
    for line in text.splitlines():
        if line.startswith("diff --git"):
            cur = None
        elif line.startswith("+++ "):
            path = line[4:].strip()
            if path != "/dev/null":
                cur = files.setdefault(path[2:] if path.startswith("b/") else path, {"lines": [], "added": 0, "removed": 0})
        elif line.startswith("--- "):
            path = line[4:].strip()
            if path != "/dev/null":
                name = path[2:] if path.startswith("a/") else path
                cur = files.setdefault(name, {"lines": [], "added": 0, "removed": 0})
        elif cur is None:
            continue
        elif line.startswith("@@"):
            cur["lines"].append(line.split("@@", 2)[-1])
        elif line.startswith("+"):
            cur["lines"].append(line[1:])
            cur["added"] += 1
        elif line.startswith("-"):
            cur["lines"].append(line[1:])
            cur["removed"] += 1
    return files


def entry_files(repo, head):
    """Source files a package.json names as main, module, types, bin or exports."""
    names = set()
    for manifest in git(repo, "ls-tree", "-r", "--name-only", head).splitlines():
        if PurePosixPath(manifest).name != "package.json" or "node_modules/" in manifest:
            continue
        try:
            pkg = json.loads(git(repo, "show", f"{head}:{manifest}") or "{}")
        except json.JSONDecodeError:
            continue
        stack = [pkg.get(k) for k in ("main", "module", "types", "typings", "bin", "exports", "source")]
        base = PurePosixPath(manifest).parent
        while stack:
            v = stack.pop()
            if isinstance(v, str):
                names.add(str((base / v).as_posix()).lstrip("./"))
            elif isinstance(v, dict):
                stack.extend(v.values())
            elif isinstance(v, list):
                stack.extend(v)
    return names


def is_entry(path, entries):
    stem = str(PurePosixPath(path).with_suffix(""))
    return bool(ENTRY.search(path)) or any(stem == str(PurePosixPath(e).with_suffix("")) for e in entries)


def users(repo, head, name):
    """Files in the head tree that use `name` as a whole word."""
    return set(git(repo, "grep", "-l", "-w", "-F", name, head, "--").replace(f"{head}:", "").split())


def gather(repo, base, head):
    diff = parse_diff(git(repo, "diff", "--no-color", "--unified=0", f"{base}...{head}"))
    changed = set(diff)
    code = {p for p in changed if PurePosixPath(p).suffix in CODE and not TEST.search(p)}
    entries = entry_files(repo, head)

    # Names declared or edited in the changed code, with the files outside the diff that use them.
    symbols, exports = {}, []
    for path in sorted(code):
        for line in diff[path]["lines"]:
            for rx in DECL:
                for m in rx.finditer(line):
                    if len(m.group(1)) > 2 and m.group(1) not in SKIP:
                        symbols.setdefault(m.group(1), set()).add(path)
            m = EXPORT.match(line)
            if m:
                found = [m.group(1) or m.group(3)] if (m.group(1) or m.group(3)) else \
                    [s.split(" as ")[-1].strip() for s in m.group(2).split(",") if s.strip()]
                for name in found:
                    exports.append({"name": name, "file": path, "entry": is_entry(path, entries)})
    reach, all_callers, tested = {}, set(), set()
    for name in sorted(symbols):
        found = users(repo, head, name)
        if any(TEST.search(f) for f in found):
            tested |= symbols[name]
        callers = sorted(f for f in found if f not in changed and not TEST.search(f))
        reach[name] = callers
        all_callers.update(callers)

    # A changed source file counts as tested when a test file names its stem or one of its symbols.
    tests = [f for f in git(repo, "ls-tree", "-r", "--name-only", head).splitlines() if TEST.search(f)]
    untested = []
    for path in sorted(code):
        stem = PurePosixPath(path).stem
        if stem == "index":
            stem = PurePosixPath(path).parent.name
        hits = users(repo, head, stem) if len(stem) > 2 else set()
        if not any(TEST.search(f) for f in hits) and path not in tested:
            untested.append(path)

    data = sorted(p for p in changed if DATA.search(p))
    deps = sorted(p for p in changed if DEPS.search(p))
    added = sum(f["added"] for f in diff.values())
    removed = sum(f["removed"] for f in diff.values())

    reasons_high, reasons_medium = [], []
    entry_exports = [e for e in exports if e["entry"]]
    if entry_exports:
        reasons_high.append("public API: " + ", ".join(sorted({e["name"] for e in entry_exports})[:8]))
    if data:
        reasons_high.append("data or format files: " + ", ".join(data[:5]))
    if len(all_callers) >= 20:
        reasons_high.append(f"{len(all_callers)} caller files")
    if 5 <= len(all_callers) < 20:
        reasons_medium.append(f"{len(all_callers)} caller files")
    if exports and not entry_exports:
        reasons_medium.append("exports changed: " + ", ".join(sorted({e["name"] for e in exports})[:8]))
    if deps:
        reasons_medium.append("dependencies: " + ", ".join(deps))
    if untested:
        reasons_medium.append("untested: " + ", ".join(untested[:5]))
    if added + removed >= 400:
        reasons_medium.append(f"{added + removed} lines changed")
    rating = "high" if reasons_high else "medium" if reasons_medium else "low"
    return {
        "base": base, "head": head, "rating": rating, "reasons": reasons_high + reasons_medium,
        "callers": len(all_callers), "symbols": reach, "exports": exports, "data": data,
        "dependencies": deps, "untested": untested, "files": len(changed),
        "lines": {"added": added, "removed": removed},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    repo = Path(args.repo)
    head = git(repo, "rev-parse", args.head).strip()
    out = gather(repo, args.base, head)
    out["head"] = args.head
    if args.json:
        print(json.dumps(out, indent=2))
        return
    print(f"suggested rating: {out['rating']}")
    for r in out["reasons"]:
        print(f"  - {r}")
    print(f"files {out['files']}, +{out['lines']['added']} -{out['lines']['removed']}, "
          f"caller files {out['callers']}")
    for name, callers in out["symbols"].items():
        if callers:
            print(f"  {name}: {len(callers)} ({', '.join(callers[:4])}{', ...' if len(callers) > 4 else ''})")


if __name__ == "__main__":
    main()

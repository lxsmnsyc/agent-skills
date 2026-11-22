#!/usr/bin/env python3
"""List the places outside a change that still mention what the change removed or changed.

Usage:
  surface.py --base main [--head HEAD] [--repo .] [--json]

A diff shows what was edited, not what should have been. This script reads the
diff for terms that left or changed, then searches the head tree outside the
changed files for every mention of them. It does not judge the code.

Terms:
  names      identifiers declared on removed lines (functions, classes, consts, types,
             Python defs) and names in removed export lists
  flags      CLI flags (--some-flag) and environment variables (SOME_VAR)
  strings    quoted strings of 12 or more characters, such as error messages and keys

Findings:
  stale      a term that left the code (on removed lines, on no added line, and no longer
             declared in the head) but is still mentioned outside the diff
  changed    a name declared on both removed and added lines (its signature or body
             changed) that docs or examples outside the diff mention
  changeset  the repo has .changeset/, the change edits package source, and adds no
             changeset file

Each finding lists file:line and the line. A stale mention in a changelog or a
past changeset is history: changelogs, .changeset/ and archive files are skipped.
Exit 0 when nothing is found, 1 when there are findings.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

CODE = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".py", ".rs", ".go", ".vue", ".svelte"}
DOC = re.compile(r"\.(md|mdx|rst|txt|adoc)$|(^|/)(docs?|examples?|website|guides?)/|\.d\.ts$")
HISTORY = re.compile(r"(^|/)(CHANGELOG|HISTORY|RELEASES)[^/]*$|(^|/)\.changeset/|(^|/)archive\.md$")
TEST = re.compile(r"(^|/)(tests?|__tests__|e2e)/|[._-](test|spec)\.[^/]+$|(^|/)test_[^/]+\.py$")
DECL = [
    re.compile(r"\bfunction\*?\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"\b(?:const|let|var|class|interface|type|enum)\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)"),
    re.compile(r"^\s*class\s+([A-Za-z_]\w*)"),
    re.compile(r"\bfn\s+([A-Za-z_]\w*)"),
    re.compile(r"^\s*([A-Za-z_$][\w$]*)\s*[:=]\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>"),
]
EXPORT_LIST = re.compile(r"export\s*\{([^}]*)\}")
FLAG = re.compile(r"(?<![\w-])--[a-z][a-z0-9]*(?:-[a-z0-9]+)+\b|(?<![\w-])--[a-z]{4,}\b")
ENV = re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]{2,}\b")
STRING = re.compile(r"""(["'`])((?:(?!\1).){12,200}?)\1""")
# Words too common to say anything when they show up elsewhere.
SKIP = {"default", "props", "state", "data", "value", "result", "index", "main", "init", "self", "this",
        "test", "options", "config", "type", "error", "name", "args", "item", "items", "node", "path"}


def git(repo, *argv):
    r = subprocess.run(["git", *argv], cwd=repo, capture_output=True, text=True)
    if r.returncode not in (0, 1):
        sys.exit(f"git {' '.join(argv)}: {r.stderr.strip()}")
    return r.stdout


def parse_diff(text):
    """For each changed file: removed lines, added lines, and whether it was added or deleted."""
    files, cur = {}, None
    old_path = None
    for line in text.splitlines():
        if line.startswith("diff --git"):
            cur, old_path = None, None
        elif line.startswith("--- "):
            p = line[4:].strip()
            old_path = None if p == "/dev/null" else p[2:]
        elif line.startswith("+++ "):
            p = line[4:].strip()
            path = old_path if p == "/dev/null" else p[2:]
            cur = files.setdefault(path, {"removed": [], "added": [], "new": old_path is None,
                                          "deleted": p == "/dev/null"})
        elif cur is None or line.startswith("@@"):
            continue
        elif line.startswith("-"):
            cur["removed"].append(line[1:])
        elif line.startswith("+"):
            cur["added"].append(line[1:])
    return files


def names_in(lines):
    out = set()
    for line in lines:
        for rx in DECL:
            for m in rx.finditer(line):
                out.add(m.group(1))
        for m in EXPORT_LIST.finditer(line):
            for part in m.group(1).split(","):
                part = part.strip().split(" as ")[-1].strip()
                if part:
                    out.add(part)
    return {n for n in out if len(n) > 3 and n not in SKIP}


def flags_in(lines):
    out = set()
    for line in lines:
        out.update(FLAG.findall(line))
        out.update(ENV.findall(line))
    return out


def strings_in(lines):
    out = set()
    for line in lines:
        for m in STRING.finditer(line):
            s = m.group(2)
            # Skip paths, URLs, imports and template expressions: they change for other reasons.
            if " " in s and "${" not in s and "://" not in s and not s.startswith(("./", "../", "/")):
                out.add(s)
    return out


def code_shaped(name):
    """camelCase, PascalCase, snake_case or with digits: unlikely to be an ordinary word."""
    return bool(re.search(r"[a-z][A-Z]|_|\d", name) or (name[:1].isupper() and name[1:] != name[1:].upper()))


def as_code(name, text):
    """Whether a line uses a plain-word name as code: opening a code span, called, or accessed."""
    n = re.escape(name)
    return bool(re.search(rf"`{n}\b|\b{n}\(|\.{n}\b|\b{n}\.\w", text))


def name_mentions(repo, head, name, exclude):
    """Mentions of an identifier. A name that reads like a word counts only where used as code."""
    hits = mentions(repo, head, name, True, exclude)
    return hits if code_shaped(name) else [h for h in hits if as_code(name, h["text"])]


def mentions(repo, head, term, word, exclude):
    """file:line hits for `term` in the head tree, outside the changed files and history."""
    args = ["grep", "-n", "-I", "-F"] + (["-w"] if word else []) + ["-e", term, head, "--"]
    hits = []
    for line in git(repo, *args).splitlines():
        rest = line[len(head) + 1:] if line.startswith(head + ":") else line
        path, _, more = rest.partition(":")
        num, _, text = more.partition(":")
        if path in exclude or HISTORY.search(path):
            continue
        hits.append({"file": path, "line": int(num) if num.isdigit() else 0, "text": text.strip()[:160]})
    return hits


def declared_in_head(repo, head, name):
    """Whether any code file in the head still declares `name`."""
    pattern = (rf"(function\*?|const|let|var|class|interface|type|enum|def|fn)\s+{re.escape(name)}\b"
               rf"|\b{re.escape(name)}\s*[:=]\s*(async\s*)?\(")
    out = git(repo, "grep", "-l", "-E", "-e", pattern, head, "--")
    return any(PurePosixPath(l.split(":", 1)[-1]).suffix in CODE for l in out.splitlines())


def gather(repo, base, head):
    diff = parse_diff(git(repo, "diff", "--no-color", "--unified=0", "-M", f"{base}...{head}"))
    changed = set(diff)
    code = {p: f for p, f in diff.items() if PurePosixPath(p).suffix in CODE and not TEST.search(p)}
    removed = [l for f in code.values() for l in f["removed"]]
    added = [l for f in code.values() for l in f["added"]]
    added_text = "\n".join(l for f in diff.values() for l in f["added"])

    # Terms that left the code: removed, not added back anywhere, not declared elsewhere.
    stale, changed_names = [], []
    gone_names = names_in(removed) - names_in(added)
    for name in sorted(gone_names):
        if re.search(rf"\b{re.escape(name)}\b", added_text) or declared_in_head(repo, head, name):
            continue
        hits = name_mentions(repo, head, name, changed)
        if hits:
            stale.append({"term": name, "kind": "name", "mentions": hits[:20], "count": len(hits)})
    for term in sorted(flags_in(removed) - flags_in(added)):
        if term in added_text:
            continue
        hits = mentions(repo, head, term, not term.startswith("--"), changed)
        if hits:
            stale.append({"term": term, "kind": "flag" if term.startswith("--") else "env", "mentions": hits[:20],
                          "count": len(hits)})
    for term in sorted(strings_in(removed) - strings_in(added)):
        if term in added_text:
            continue
        hits = mentions(repo, head, term, False, changed)
        if hits:
            stale.append({"term": term, "kind": "string", "mentions": hits[:20], "count": len(hits)})

    # Names whose declaration changed: docs and examples outside the diff may describe the old form.
    for name in sorted(names_in(removed) & names_in(added)):
        hits = [h for h in name_mentions(repo, head, name, changed) if DOC.search(h["file"])]
        if hits:
            changed_names.append({"term": name, "kind": "name", "mentions": hits[:20], "count": len(hits)})

    # A package change with no changeset, in a repo that releases with changesets.
    has_changesets = bool(git(repo, "ls-tree", "-d", "--name-only", head, ".changeset").strip())
    new_changeset = any(p.startswith(".changeset/") and p.endswith(".md") and f["new"]
                        and not p.endswith("README.md") for p, f in diff.items())
    changeset = has_changesets and bool(code) and not new_changeset

    return {"base": base, "head": head, "stale": stale, "changed": changed_names,
            "changeset_missing": changeset, "files": len(changed)}


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
    found = bool(out["stale"] or out["changed"] or out["changeset_missing"])
    if args.json:
        print(json.dumps(out, indent=2))
        return 1 if found else 0
    if not found:
        print("surface: nothing outside the diff mentions what it removed or changed")
        return 0
    for title, items in (("stale (left the code, still mentioned)", out["stale"]),
                         ("changed (docs or examples mention it)", out["changed"])):
        if items:
            print(title + ":")
            for it in items:
                print(f"  {it['kind']} {it['term']!r}: {it['count']} mention(s)")
                for h in it["mentions"][:5]:
                    print(f"    {h['file']}:{h['line']}: {h['text']}")
    if out["changeset_missing"]:
        print("changeset: package source changed and no .changeset/*.md was added")
    return 1


if __name__ == "__main__":
    sys.exit(main())

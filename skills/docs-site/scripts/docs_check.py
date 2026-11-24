#!/usr/bin/env python3
"""Check the structure of a docs site's Markdown pages.

Reads every .md and .mdx file under a folder and reports:
  - missing or unknown `type:` in the frontmatter (error)
  - sections the page type requires, such as `Why` on a feature page (error)
  - guides without numbered steps (error)
  - relative links to files that do not exist (error)
  - with --repo, paths in a page's `covers:` list that do not exist (error)
  - `requires:` entries that do not exist, cycles in them, or a required page in the
    same folder whose `order:` or `sidebar_position:` is not lower (error)
  - a required page the page does not link (warning)
  - with --exports, exports declared with no doc comment above them (warning)
  - with --translation, source pages with no translation (warning), translated pages
    with no source (error), translations older than their source in git (warning)
    and heading ids the translation lacks (warning)
  - pages whose first content is a heading instead of a lead sentence (warning)
  - code blocks with no language (warning)
  - pages no other page links to (warning)
  - with --exports and --reference, exported names no reference page mentions (warning)

Usage:
  docs_check.py website/docs
  docs_check.py website/docs --entry getting-started.md
  docs_check.py website/docs --exports src/index.ts --reference website/docs/reference
  docs_check.py website/docs --repo .
  docs_check.py website/docs/en --translation website/docs/ja
  docs_check.py website/docs --json

Links starting with / are resolved against the folder given. Navigation in the
site generator's config (a sidebar file) is not read.
Exits 1 when there is an error.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TYPES = {
    "tutorial", "guide", "concept", "feature", "reference",
    "troubleshooting", "migration", "example", "glossary", "internals", "index",
}

# Each required section lists the headings that satisfy it. A heading matches
# when it equals an alias or starts with the alias followed by a space.
RELATED = ["related", "see also", "next steps", "further reading"]
BEFORE = ["before you start", "prerequisites", "requirements"]
REQUIRED = {
    "tutorial": {"Before you start": BEFORE, "Next steps": RELATED},
    "guide": {"Related": RELATED},
    "concept": {"Related": RELATED},
    "feature": {
        "Why": ["why", "when to use"],
        "How it works": ["how it works"],
        "Usage": ["usage", "use", "using", "examples"],
        "Related": RELATED,
    },
    "migration": {"Breaking changes": ["breaking changes"]},
    "internals": {"Overview": ["overview"]},
}

FENCE = re.compile(r"^\s*(```+|~~~+)\s*([^\s`]*)")
HEADING_ID = re.compile(r"\{#([\w-]+)\}")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
ORDERED = re.compile(r"^\s*\d+[.)]\s+\S")
LINK = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
LINK_DEF = re.compile(r"^\s*\[[^\]]+\]:\s*<?(\S+?)>?(?:\s+.*)?$")
INLINE_CODE = re.compile(r"`[^`]*`")
EXTERNAL = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:|^//")
MDX_LINE = re.compile(r"^\s*(import|export)\s")
EXPORT_DECL = re.compile(
    r"^\s*export\s+(?:declare\s+)?(?:default\s+)?(?:async\s+)?"
    r"(?:function\*?|const|let|var|class|interface|type|enum|abstract\s+class)\s+([A-Za-z_$][\w$]*)",
    re.M,
)
EXPORT_LIST = re.compile(r"^\s*export\s+(?:type\s+)?\{([^}]*)\}", re.M)


def read_frontmatter(lines):
    """Return (fields, index of the first line after the frontmatter)."""
    if not lines or lines[0].strip() != "---":
        return {}, 0
    fields = {}
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            return fields, index + 1
        match = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip("'\"")
    return {}, 0


def parse_list(value):
    """Read a frontmatter value written as `[a, b]` or `a`."""
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    items = []
    for part in value.split(","):
        part = part.strip().strip("'\"")
        if part:
            items.append(part)
    return items


def normalize_heading(text):
    text = text.replace("`", "")
    text = re.sub(r"\{#[^}]*\}", "", text)
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(text.split())


def matches_alias(heading, aliases):
    for alias in aliases:
        if heading == alias or heading.startswith(alias + " "):
            return True
    return False


def scan_page(path, text):
    """Split a page into the parts the checks need."""
    lines = text.splitlines()
    fields, start = read_frontmatter(lines)
    page = {
        "fields": fields,
        "headings": [],
        "ids": set(),
        "links": [],
        "bare_fences": [],
        "ordered": False,
        "lead_problem": None,
    }
    fence = None
    first_content = None
    for number in range(start, len(lines)):
        line = lines[number]
        line_number = number + 1
        match = FENCE.match(line)

        # Track fenced code blocks. Only an opening fence carries a language.
        if fence is None and match:
            fence = match.group(1)
            if not match.group(2):
                page["bare_fences"].append(line_number)
            if first_content is None:
                first_content = ("code", line_number)
            continue
        if fence is not None:
            if match and match.group(1).startswith(fence[0] * len(fence)) and not match.group(2):
                fence = None
            continue

        # Record the first content line, skipping MDX imports and the H1 title.
        stripped = line.strip()
        heading = HEADING.match(line)
        if first_content is None and stripped and not MDX_LINE.match(line):
            if heading and len(heading.group(1)) == 1:
                pass
            elif heading:
                first_content = ("heading", line_number)
            else:
                first_content = ("text", line_number)

        if heading:
            page["headings"].append((normalize_heading(heading.group(2)), line_number))
            explicit = HEADING_ID.search(heading.group(2))
            if explicit:
                page["ids"].add(explicit.group(1))
            if re.match(r"^(step\s+)?\d+\b", normalize_heading(heading.group(2))):
                page["ordered"] = True
        if ORDERED.match(line):
            page["ordered"] = True

        # Collect links outside inline code.
        plain = INLINE_CODE.sub("", line)
        for link in LINK.finditer(plain):
            page["links"].append((link.group(1), line_number))
        definition = LINK_DEF.match(plain)
        if definition:
            page["links"].append((definition.group(1), line_number))

    if first_content is None:
        page["lead_problem"] = (start + 1, "page has no content")
    elif first_content[0] == "heading":
        page["lead_problem"] = (first_content[1], "page starts with a heading; add a lead sentence above it")
    return page


def resolve_link(root, page_path, target):
    """Return the file a relative link points to, or None when it is missing."""
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return page_path
    base = root / target.lstrip("/") if target.startswith("/") else page_path.parent / target
    candidates = [base]
    if base.suffix == ".html":
        candidates.append(base.with_suffix(".md"))
        candidates.append(base.with_suffix(".mdx"))
    candidates += [
        base.with_name(base.name + ".md"),
        base.with_name(base.name + ".mdx"),
        base / "index.md",
        base / "index.mdx",
        base / "README.md",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def read_exports(entry):
    """Return (exported names, declared exports with no doc comment above them)."""
    text = entry.read_text(encoding="utf-8")
    names = set()
    undocumented = set()
    for match in EXPORT_DECL.finditer(text):
        names.add(match.group(1))
        if not text[:match.start()].rstrip().endswith("*/"):
            undocumented.add(match.group(1))
    for group in EXPORT_LIST.findall(text):
        for part in group.split(","):
            part = re.sub(r"^\s*type\s+", "", part).strip()
            if not part:
                continue
            name = part.split(" as ")[-1].strip()
            if name and name != "default":
                names.add(name)
    return names, undocumented


def last_commit(path):
    """Return (unix time, date) of the last commit that touched a file, or None."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct %cs", "--", path.name],
            cwd=path.parent, capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    parts = result.stdout.split()
    if result.returncode != 0 or len(parts) != 2:
        return None
    return int(parts[0]), parts[1]


def check_translation(root, pages, translation, findings):
    """Compare a translation folder with the source pages under root."""
    translation = translation.resolve()

    def report(path, level, message):
        findings.append({"file": str(path), "line": 1, "level": level, "message": message})

    translated = set()
    for path in sorted(translation.rglob("*")):
        if path.suffix in (".md", ".mdx") and path.is_file():
            translated.add(path.relative_to(translation))

    for source, page in pages.items():
        relative = source.relative_to(root)
        target = translation / relative
        if relative not in translated:
            report(target, "warning", f"no translation of `{relative}`")
            continue

        # Older than the source, by commit time.
        source_commit = last_commit(source)
        target_commit = last_commit(target)
        if source_commit and target_commit and source_commit[0] > target_commit[0]:
            report(target, "warning",
                   f"source changed on {source_commit[1]}, translation last changed on {target_commit[1]}")

        # Heading ids that links rely on.
        target_page = scan_page(target, target.read_text(encoding="utf-8"))
        for missing in sorted(page["ids"] - target_page["ids"]):
            report(target, "warning", f"heading id `{missing}` from the source is missing")

    for relative in sorted(translated):
        if (root / relative).resolve() not in pages:
            report(translation / relative, "error", f"translated page `{relative}` has no source page")


def read_order(fields):
    """Return the page's position from `order:` or `sidebar_position:`, or None."""
    for key in ("order", "sidebar_position"):
        try:
            return float(fields[key])
        except (KeyError, ValueError):
            continue
    return None


def check_requires(root, pages, links_from, report):
    """Check `requires:` entries exist, are linked, form no cycle and come first."""
    graph = {}
    for path, page in pages.items():
        graph[path] = []
        for target in parse_list(page["fields"].get("requires", "")):
            resolved = resolve_link(root, path, target)
            if resolved is None or resolved not in pages:
                report(path, 1, "error", f"broken link in requires: `{target}`")
                continue
            graph[path].append(resolved)
            if resolved not in links_from.get(path, set()):
                report(path, 1, "warning", f"required page `{target}` is not linked from the page")
            mine = read_order(page["fields"])
            theirs = read_order(pages[resolved]["fields"])
            if resolved.parent == path.parent and mine is not None and theirs is not None and theirs >= mine:
                report(path, 1, "error", f"required page `{target}` must come earlier in the order")

    # Find cycles with a depth-first walk. 0 = unvisited, 1 = on the stack, 2 = done.
    state = {}
    reported = set()

    def visit(node, stack):
        state[node] = 1
        stack.append(node)
        for nxt in graph[node]:
            if state.get(nxt) == 1:
                cycle = stack[stack.index(nxt):]
                key = frozenset(cycle)
                if key not in reported:
                    reported.add(key)
                    names = []
                    for item in cycle + [nxt]:
                        names.append(str(item.relative_to(root)))
                    report(nxt, 1, "error", "requires cycle: " + " -> ".join(names))
            elif state.get(nxt) is None:
                visit(nxt, stack)
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        if state.get(node) is None:
            visit(node, [])


def check(root, entries, exports_file=None, reference_dir=None, repo=None, translations=()):
    root = root.resolve()
    findings = []
    pages = {}
    for path in sorted(root.rglob("*")):
        if path.suffix in (".md", ".mdx") and path.is_file() and "node_modules" not in path.parts:
            pages[path.resolve()] = scan_page(path, path.read_text(encoding="utf-8"))

    def report(path, line, level, message):
        findings.append({
            "file": str(path.relative_to(root)),
            "line": line,
            "level": level,
            "message": message,
        })

    linked = set()
    links_from = {}
    for path, page in pages.items():
        kind = page["fields"].get("type")

        # Page type and the sections it requires.
        if not kind:
            report(path, 1, "error", "frontmatter has no `type:`")
        elif kind not in TYPES:
            report(path, 1, "error", f"unknown type `{kind}`; use one of {', '.join(sorted(TYPES))}")
        else:
            headings = [heading for heading, _ in page["headings"]]
            for section, aliases in REQUIRED.get(kind, {}).items():
                found = False
                for heading in headings:
                    if matches_alias(heading, aliases):
                        found = True
                        break
                if not found:
                    report(path, 1, "error", f"{kind} page has no `{section}` section")
            if kind == "guide" and not page["ordered"]:
                report(path, 1, "error", "guide has no numbered steps")

        # Source paths the page says it describes.
        if repo is not None:
            for covered in parse_list(page["fields"].get("covers", "")):
                if not (repo / covered).exists():
                    report(path, 1, "error", f"covered path `{covered}` does not exist")

        # Lead sentence and code fences.
        if page["lead_problem"] and kind != "index":
            report(path, page["lead_problem"][0], "warning", page["lead_problem"][1])
        for line in page["bare_fences"]:
            report(path, line, "warning", "code block has no language")

        # Relative links.
        for target, line in page["links"]:
            if EXTERNAL.match(target) or target.startswith("#"):
                continue
            resolved = resolve_link(root, path, target)
            if resolved is None:
                report(path, line, "error", f"broken link `{target}`")
            elif resolved != path:
                linked.add(resolved)
                links_from.setdefault(path, set()).add(resolved)

    check_requires(root, pages, links_from, report)

    # Pages nothing links to.
    entry_paths = set()
    for entry in entries:
        entry_paths.add((root / entry).resolve())
    for path, page in pages.items():
        is_index = page["fields"].get("type") == "index" or path.stem in ("index", "README")
        if path not in linked and not is_index and path not in entry_paths:
            report(path, 1, "warning", "no other page links here")

    # Exports with no reference entry.
    if exports_file and reference_dir:
        reference_text = []
        for path in sorted(Path(reference_dir).rglob("*")):
            if path.suffix in (".md", ".mdx") and path.is_file():
                reference_text.append(path.read_text(encoding="utf-8"))
        joined = "\n".join(reference_text)
        names, undocumented = read_exports(Path(exports_file))
        for name in sorted(undocumented):
            findings.append({
                "file": str(exports_file),
                "line": 1,
                "level": "warning",
                "message": f"export `{name}` has no doc comment",
            })
        for name in sorted(names):
            if not re.search(r"(?<![\w$])" + re.escape(name) + r"(?![\w$])", joined):
                findings.append({
                    "file": str(exports_file),
                    "line": 1,
                    "level": "warning",
                    "message": f"export `{name}` has no reference entry",
                })

    for translation in translations:
        check_translation(root, pages, Path(translation), findings)

    return findings, len(pages)


def main():
    parser = argparse.ArgumentParser(description="Check the structure of a docs site.")
    parser.add_argument("root", type=Path, help="folder that holds the docs pages")
    parser.add_argument("--entry", action="append", default=[],
                        help="page reached from the sidebar or home, skipped by the orphan check (repeatable)")
    parser.add_argument("--exports", help="entry file whose exports need reference entries")
    parser.add_argument("--reference", help="folder that holds the reference pages")
    parser.add_argument("--repo", type=Path, help="repo root for checking `covers:` paths")
    parser.add_argument("--translation", action="append", default=[],
                        help="translation folder with the same tree as the source (repeatable)")
    parser.add_argument("--json", action="store_true", help="print findings as JSON")
    args = parser.parse_args()

    if not args.root.is_dir():
        print(f"not a folder: {args.root}", file=sys.stderr)
        return 2
    if bool(args.exports) != bool(args.reference):
        print("--exports and --reference go together", file=sys.stderr)
        return 2

    findings, count = check(args.root, args.entry, args.exports, args.reference, args.repo, args.translation)
    errors = 0
    for finding in findings:
        if finding["level"] == "error":
            errors += 1

    if args.json:
        print(json.dumps({"pages": count, "findings": findings}, indent=2))
    else:
        for finding in findings:
            print(f"{finding['file']}:{finding['line']}: {finding['level']}: {finding['message']}")
        print(f"{count} pages, {errors} errors, {len(findings) - errors} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

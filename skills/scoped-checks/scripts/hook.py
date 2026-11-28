#!/usr/bin/env python3
"""Claude Code PreToolUse hook: stop full runs of tests, lint, format and typecheck.

Enable with the environment variable SCOPED_CHECKS_HOOK:
  block  stop the command (exit 2, the reason goes to Claude)
  warn   let the command run (the reason is only logged)
  unset  do nothing (default)

A run counts as full when it names no file. These are full runs:
  pnpm test, npm run lint, yarn format:check, pnpm -r test
  vitest, vitest run, jest, oxlint, eslint ., prettier --check ., oxfmt,
  biome check ., ruff check ., ruff format ., mypy ., pytest, pytest tests/,
  go test ./..., go vet ./..., checks.py without --changed
  typecheck scripts at the root of a workspace (pnpm-workspace.yaml or
  "workspaces" in package.json). A single package has one tsconfig, so its
  typecheck stays allowed.
These are allowed: a command with a file argument (vitest run src/a.test.ts),
a run in one package (pnpm --filter a test, pnpm -C packages/a test), and any
command prefixed with SCOPED_CHECKS=full.
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path

CHECKS = Path(__file__).resolve().parent / "checks.py"
SEPARATORS = {"&&", "||", ";", "|", "&", "\n"}
PMS = {"npm", "pnpm", "yarn", "bun"}
SCRIPT_KINDS = {
    "test": "test", "test:unit": "test",
    "lint": "lint", "lint:fix": "lint", "check:lint": "lint", "lint:check": "lint",
    "format": "format", "format:check": "format", "fmt": "format", "fmt:check": "format",
    "check:format": "format",
    "typecheck": "typecheck", "type-check": "typecheck", "check:types": "typecheck", "types": "typecheck",
}
# Tools that take paths, and the subcommands that come before the paths.
TOOLS = {"vitest": ("test", {"run", "watch"}), "jest": ("test", set()), "oxlint": ("lint", set()),
         "eslint": ("lint", set()), "prettier": ("format", set()), "oxfmt": ("format", set()),
         "biome": ("lint", {"check", "lint", "format", "ci"}), "ruff": ("lint", {"check", "format"}),
         "mypy": ("typecheck", set()), "pytest": ("test", set())}
# Options of these tools that take a value, so the value is not read as a path.
VALUE_OPTIONS = {"-c", "--config", "--project", "--root", "--dir", "-p", "--reporter", "-t", "--testNamePattern",
                 "-k", "-m", "--ignore-path", "--tsconfig", "--format", "-f", "--max-warnings", "--rootDir",
                 "--environment", "--pool", "--shard", "--workspace"}


def segments(command):
    lex = shlex.shlex(command, posix=True, punctuation_chars=";&|")
    lex.whitespace_split = True
    lex.commenters = ""
    cur = []
    try:
        for t in lex:
            if t in SEPARATORS:
                if cur:
                    yield cur
                cur = []
            else:
                cur.append(t)
    except ValueError:
        return
    if cur:
        yield cur


def is_workspace_root(d):
    if (d / "pnpm-workspace.yaml").exists():
        return True
    try:
        return "workspaces" in json.loads((d / "package.json").read_text())
    except (OSError, ValueError):
        return False


def positionals(args):
    """Arguments that are not options or option values."""
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif a == "--":
            continue
        elif a.startswith("-"):
            skip = a in VALUE_OPTIONS
        else:
            out.append(a)
    return out


def names_a_file(cwd, args):
    """True when an argument is a file path, not a folder, a glob or "."."""
    for a in positionals(args):
        if "*" in a or a.endswith("/") or a == ".":
            continue
        p = cwd / a
        if p.is_dir():
            continue
        if p.is_file() or re.search(r"\.\w+$", a):
            return True
    return False


def full_run(cwd, tokens):
    """The kind of check a full run does, or None when the command is scoped or not a check."""
    while tokens and re.match(r"^\w+=", tokens[0]):
        tokens = tokens[1:]
    if not tokens:
        return None
    if tokens[0] in ("npx", "bunx") or tokens[:2] in (["pnpm", "exec"], ["pnpm", "dlx"], ["yarn", "exec"],
                                                      ["npm", "exec"], ["bun", "x"]):
        tokens = tokens[2:] if tokens[0] in PMS else tokens[1:]
        tokens = [t for t in tokens if t != "--"]
    if not tokens:
        return None
    tool = Path(tokens[0]).name
    if tool.startswith("python"):
        rest = tokens[1:]
        if rest[:2] == ["-m", "pytest"] or rest[:2] == ["-m", "mypy"]:
            tool, tokens = rest[1], rest[1:]
        elif rest and Path(rest[0]).name == "checks.py":
            return None if "--changed" in rest or "--run" not in rest else "every"
        else:
            return None
    if tool == "checks.py":
        return None if "--changed" in tokens or "--run" not in tokens else "every"
    if tool in PMS:
        args = tokens[1:]
        if any(a in ("--filter", "-F", "-C", "--dir", "--cwd", "--prefix") or a.startswith("--filter=")
               for a in args):
            return None
        recursive = any(a in ("-r", "--recursive", "-ws", "--workspaces") for a in args)
        rest = [a for a in args if not a.startswith("-")]
        if rest and rest[0] == "run":
            rest = rest[1:]
        if not rest or rest[0] not in SCRIPT_KINDS:
            return None
        kind = SCRIPT_KINDS[rest[0]]
        script_args = args[args.index(rest[0]) + 1:]
        if names_a_file(cwd, script_args):
            return None
        if kind == "typecheck" and not recursive and not is_workspace_root(cwd):
            return None
        return kind
    if tool == "go" and len(tokens) > 1 and tokens[1] in ("test", "vet"):
        return "test" if tokens[1] == "test" else "lint"
    if tool == "go":
        return None
    if tool not in TOOLS:
        return None
    kind, subcommands = TOOLS[tool]
    args = tokens[1:]
    if args and args[0] in subcommands:
        args = args[1:]
    if tool == "vitest" and args and args[0] == "related":
        return None
    if tool == "jest" and "--findRelatedTests" in args:
        return None
    if tool in ("vitest", "jest") and positionals(args):
        return None  # a name filter or a path, both narrow the run
    if names_a_file(cwd, args):
        return None
    return kind


def full_runs(command, cwd):
    found = []
    for tokens in segments(command):
        if tokens[0] == "cd" and len(tokens) > 1:
            cwd = (cwd / tokens[1]).resolve()
            continue
        if any(t == "SCOPED_CHECKS=full" for t in tokens):
            return []
        kind = full_run(cwd, tokens)
        if kind:
            found.append((kind, " ".join(tokens)))
    return found


def main():
    mode = os.environ.get("SCOPED_CHECKS_HOOK", "").lower()
    if mode not in ("block", "warn"):
        return
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    if event.get("tool_name") != "Bash":
        return
    command = (event.get("tool_input") or {}).get("command", "")
    found = full_runs(command, Path(event.get("cwd") or os.getcwd()))
    if not found:
        return
    kinds = sorted({k for k, _ in found if k != "every"})
    only = f" --only {','.join(kinds)}" if kinds else ""
    report = (
        "This command runs a full check: " + "; ".join(f"`{c}`" for _, c in found) + ".\n"
        "Check only what the change touches. Either pass the changed file paths to the tool, "
        f"or run `python3 {CHECKS} . --run --changed{only}`.\n"
        "When a full run is needed (a config file changed, the final gate on a repo with no CI, "
        "or the user asked for it), prefix the command with SCOPED_CHECKS=full."
    )
    print(report, file=sys.stderr)
    sys.exit(2 if mode == "block" else 0)


if __name__ == "__main__":
    main()

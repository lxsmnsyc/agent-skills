#!/usr/bin/env python3
"""Claude Code PreToolUse hook: check commit messages and PR text before they are sent.

Enable with the environment variable PLAIN_WRITING_HOOK:
  block  stop the command when the text has errors (exit 2, findings go to Claude)
  warn   let the command run (findings are only logged)
  unset  do nothing (default)

Covers `git commit -m/-F`, and `--title/--body/--body-file` of
`gh pr create|edit|review|comment` and `gh issue create|comment`.
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_prose import check_text  # noqa: E402

SEPARATORS = {"&&", "||", ";", "|", "&"}
GH_COMMANDS = {("pr", "create"), ("pr", "edit"), ("pr", "review"), ("pr", "comment"),
               ("issue", "create"), ("issue", "comment")}


def unwrap(value):
    """Return the text of a `$(cat <<'EOF' ... EOF)` argument, or the value itself."""
    m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?\n(.*?)\n\s*\1\s*\n?\)?\s*$", value, re.S)
    return m.group(2) if m else value


def segments(tokens):
    cur = []
    for t in tokens:
        if t in SEPARATORS:
            if cur:
                yield cur
            cur = []
        else:
            cur.append(t)
    if cur:
        yield cur


def option_values(args, names, file_names=()):
    """Collect values of options like -m X, --body=X, --body-file F."""
    out = []
    i = 0
    while i < len(args):
        a = args[i]
        for n in names + file_names:
            val = None
            if a == n and i + 1 < len(args):
                val = args[i + 1]
                i += 1
            elif n.startswith("--") and a.startswith(n + "="):
                val = a[len(n) + 1:]
            elif not n.startswith("--") and a.startswith(n) and len(a) > len(n):
                val = a[len(n):]
            if val is not None:
                if n in file_names:
                    try:
                        val = Path(val).read_text(encoding="utf-8") if val != "-" else ""
                    except OSError:
                        val = ""
                out.append((n, unwrap(val)))
                break
        i += 1
    return out


WRAPPERS = {"rtk", "command", "env", "time", "nice"}


def strip_wrappers(seg):
    """Drop leading wrappers such as `rtk`, `rtk proxy`, `env`, and VAR=value assignments."""
    i = 0
    while i < len(seg):
        t = seg[i]
        if t in WRAPPERS or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t):
            i += 1
            if t == "rtk" and i < len(seg) and seg[i] == "proxy":
                i += 1
            continue
        break
    return seg[i:]


def git_subcommand(seg):
    """Index of the git subcommand in a segment that runs git, skipping global options."""
    if not seg or seg[0] != "git":
        return None
    i = 1
    while i < len(seg) and seg[i].startswith("-"):
        # Global options that take a separate value.
        i += 2 if seg[i] in ("-C", "-c", "--git-dir", "--work-tree", "--namespace") else 1
    return i if i < len(seg) else None


def texts_from_command(command):
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return []
    found = []
    for seg in segments(tokens):
        # Only the command a segment runs counts: words inside a heredoc or a
        # quoted script are arguments, not commands.
        seg = strip_wrappers(seg)
        words = [w for w in seg if not w.startswith("-")]
        sub = git_subcommand(seg)
        if sub is not None and seg[sub] == "commit":
            rest = seg[sub + 1:]
            msgs = option_values(rest, ["-m", "--message"], ["-F", "--file"])
            if msgs:
                found.append(("commit message", "\n\n".join(v for _, v in msgs), True))
        elif seg and seg[0] == "gh" and len(words) >= 3 and (words[1], words[2]) in GH_COMMANDS:
            rest = seg[3:]
            for n, v in option_values(rest, ["--title", "-t", "--body", "-b"], ["--body-file", "-F"]):
                found.append((f"gh {words[1]} {words[2]} {n}", v, False))
    return found


def strip_trailers(text):
    return "\n".join(l for l in text.split("\n")
                     if not re.match(r"\s*(Co-Authored-By|Signed-off-by):", l, re.I)
                     and "Generated with [Claude Code]" not in l)


def main():
    mode = os.environ.get("PLAIN_WRITING_HOOK", "").lower()
    if mode not in ("block", "warn"):
        return
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    if event.get("tool_name") != "Bash":
        return
    command = (event.get("tool_input") or {}).get("command", "")
    errors = []
    for name, text, is_commit in texts_from_command(command):
        for _, n, level, rule, msg, hit in check_text(strip_trailers(text), name, commit=is_commit):
            if level == "error":
                errors.append(f"{name} line {n}: {rule}: {msg} [{hit}]")
    if not errors:
        return
    report = "plain-writing found problems in the text of this command:\n" + "\n".join(
        f"- {e}" for e in errors) + "\nRewrite the text and run the command again."
    print(report, file=sys.stderr)
    sys.exit(2 if mode == "block" else 0)


if __name__ == "__main__":
    main()

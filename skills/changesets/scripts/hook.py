#!/usr/bin/env python3
"""Claude Code PreToolUse hook: check changeset files before they are written.

Enable with the environment variable CHANGESETS_HOOK:
  block  stop the write when it breaks a rule (exit 2, findings go to Claude)
  warn   let the write happen (findings are only logged)
  unset  do nothing (default)

Covers Write, Edit and MultiEdit of `.changeset/*.md` (not README.md). It checks:
- that the agent making the write loaded the changesets and plain-writing skills,
- the frontmatter: each package has patch, minor or major,
- the prose with the plain-writing checker, where long sentences and
  semicolons count as errors,
- that each entry (a list item or a paragraph) has at most two sentences.
A `major` bump asks the user to approve the write instead of blocking it.
"""
import json
import os
import re
import sys
from pathlib import Path

PLAIN_WRITING = Path(__file__).resolve().parents[2] / "plain-writing/scripts"
sys.path.insert(0, str(PLAIN_WRITING))
from check_prose import check_text, sentences  # noqa: E402

REQUIRED_SKILLS = ("changesets", "plain-writing")
STRICT_RULES = {"long-sentence", "semicolon"}
MAX_SENTENCES = 2
LEVELS = {"patch", "minor", "major"}


def is_changeset(path):
    p = Path(path)
    return p.parent.name == ".changeset" and p.suffix == ".md" and p.name.lower() != "readme.md"


def new_content(tool, inp, path):
    """The file's text after the tool call, or None when it cannot be known."""
    if tool == "Write":
        return inp.get("content", "")
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    edits = inp.get("edits") if tool == "MultiEdit" else [inp]
    for e in edits or []:
        old, new = e.get("old_string", ""), e.get("new_string", "")
        if old not in text:
            return None
        text = text.replace(old, new) if e.get("replace_all") else text.replace(old, new, 1)
    return text


def transcripts(event):
    """Transcripts that belong to the agent making this call."""
    main = event.get("transcript_path")
    agent_id = event.get("agent_id")
    out = []
    if event.get("agent_transcript_path"):
        out.append(Path(event["agent_transcript_path"]))
    if agent_id and main:
        out.append(Path(main).with_suffix("") / "subagents" / f"agent-{agent_id}.jsonl")
    if not out and main:
        out.append(Path(main))
    return out


def loaded_skills(paths):
    """Names of skills loaded with the Skill tool or a slash command."""
    found = set()
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            content = (entry.get("message") or {}).get("content")
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            for block in content or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use" and block.get("name") == "Skill":
                    found.add(str((block.get("input") or {}).get("skill", "")).split(":")[-1])
                elif block.get("type") == "text" and entry.get("type") == "user":
                    for m in re.finditer(r"<command-name>/?([^<]+)</command-name>", block["text"]):
                        found.add(m.group(1).split(":")[-1].strip())
    return found


def split_frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
    if not m:
        return None, text
    return m.group(1), m.group(2)


def entries(body):
    """List items and paragraphs, each joined into one string."""
    out, cur = [], []
    for line in body.split("\n"):
        if not line.strip() or re.match(r"\s*([-*+]|\d+\.)\s", line):
            if cur:
                out.append(" ".join(cur))
            cur = [line.strip()] if line.strip() else []
        else:
            cur.append(line.strip())
    if cur:
        out.append(" ".join(cur))
    return out


def check(text, name):
    errors, majors = [], []
    front, body = split_frontmatter(text)
    if front is None:
        errors.append("No frontmatter. Start the file with --- and one `'package': level` line per package.")
    else:
        for line in front.split("\n"):
            if not line.strip():
                continue
            m = re.match(r"""\s*['"]?([^'":]+)['"]?\s*:\s*(\w+)\s*$""", line)
            if not m or m.group(2) not in LEVELS:
                errors.append(f"Frontmatter line `{line.strip()}` is not `'package': patch|minor|major`.")
            elif m.group(2) == "major":
                majors.append(m.group(1))
    if not body.strip():
        errors.append("The changeset has no text.")
    for _, n, level, rule, msg, hit in check_text(body, name):
        if level == "error" or rule in STRICT_RULES:
            errors.append(f"line {n}: {rule}: {msg} [{hit}]")
    plain = "\n".join(re.sub(r"`[^`]*`", "x", l) for l in body.split("\n"))
    for entry in entries(plain):
        count = len(sentences(re.sub(r"^([-*+]|\d+\.)\s+", "", entry)))
        if count > MAX_SENTENCES:
            errors.append(f"An entry has {count} sentences, the limit is {MAX_SENTENCES}. "
                          f"Say what is true now and drop the reasoning [{entry[:60]}...]")
    return errors, majors


def main():
    mode = os.environ.get("CHANGESETS_HOOK", "").lower()
    if mode not in ("block", "warn"):
        return
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    tool = event.get("tool_name")
    if tool not in ("Write", "Edit", "MultiEdit"):
        return
    inp = event.get("tool_input") or {}
    path = inp.get("file_path", "")
    if not is_changeset(path):
        return

    problems = []
    missing = [s for s in REQUIRED_SKILLS if s not in loaded_skills(transcripts(event))]
    if missing:
        problems.append("Load these skills with the Skill tool before writing a changeset: "
                        + ", ".join(f"agent-skills:{s}" for s in missing)
                        + ". Then rewrite the changeset to follow them.")
    majors = []
    text = new_content(tool, inp, path)
    if text is not None:
        errors, majors = check(text, Path(path).name)
        problems += errors

    if problems:
        report = f"The changeset {Path(path).name} breaks these rules:\n" + "\n".join(
            f"- {p}" for p in problems)
        print(report, file=sys.stderr)
        sys.exit(2 if mode == "block" else 0)
    if majors:
        reason = (f"Major bump for {', '.join(majors)}. The changesets skill needs the "
                  "maintainer's approval for a major bump.")
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }}))


if __name__ == "__main__":
    main()

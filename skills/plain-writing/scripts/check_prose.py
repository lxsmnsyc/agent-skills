#!/usr/bin/env python3
"""Check prose against the plain-writing rules.

Usage:
  check_prose.py FILE...              # Markdown or text files
  check_prose.py --comments FILE...   # only the comments in source files
  check_prose.py --commit RANGE       # commit messages, e.g. origin/main..HEAD
  check_prose.py -                    # read stdin
  check_prose.py --list               # print every rule and phrase

Prints `file:line: level rule: message`. Exit 1 when there are errors.
Code blocks and `inline code` are skipped.
"""
import argparse
import re
import subprocess
import sys

MAX_WORDS = 25
MAX_SUBJECT = 72

# Each entry: phrase -> suggestion ("" means delete it).
WORDY = {
    "in order to": "to",
    "due to the fact that": "because",
    "owing to the fact that": "because",
    "at this point in time": "now",
    "at the present time": "now",
    "for the purpose of": "for",
    "in the event that": "if",
    "in terms of": "",
    "with regard to": "about",
    "with respect to": "about",
    "a number of": "some, or the number",
    "a majority of": "most",
    "whether or not": "whether",
    "make use of": "use",
    "is able to": "can",
    "are able to": "can",
    "has the ability to": "can",
    "have the ability to": "can",
    "prior to": "before",
    "subsequent to": "after",
    "in spite of the fact that": "although",
    "the fact that": "",
    "it is possible that": "may",
    "there is a need to": "must",
    "take into account": "consider",
    "utilize": "use",
    "utilise": "use",
    "facilitate": "help, or let",
    "commence": "start",
    "terminate": "end, or stop",
    "approximately": "about",
    "additional": "more",
    "sufficient": "enough",
    "numerous": "many",
    "demonstrate": "show",
    "in conjunction with": "with",
    "on a regular basis": "regularly",
}

FILLER = [
    "just", "simply", "basically", "actually", "really", "very", "quite",
    "rather", "essentially", "literally", "of course", "obviously", "clearly",
    "needless to say", "note that", "it should be noted", "it's worth noting",
    "it is worth noting", "it's important to note", "it is important to note",
    "as you can see", "as mentioned", "as discussed", "please note",
]

HEDGES = [
    "might possibly", "perhaps", "somewhat", "arguably", "seems to",
    "sort of", "kind of", "more or less", "to some extent", "i think",
    "i believe",
]

# Marketing words and phrases that read as filler or as generated text.
STOCK = [
    "delve", "leverage", "leverages", "leveraging", "robust", "seamless",
    "seamlessly", "streamline", "empower", "elevate", "harness the", "unleash",
    "game-changer", "game changer", "cutting-edge", "state-of-the-art",
    "holistic", "synergy", "paradigm", "pivotal", "foster", "tapestry",
    "testament", "myriad", "plethora", "embark", "boasts", "showcase",
    "showcases", "underscore", "underscores", "ever-evolving", "best-in-class",
    "world-class", "blazing fast", "blazingly fast", "lightning fast",
    "battle-tested", "supercharge", "revolutionize", "effortless",
    "effortlessly", "next-level", "in today's", "let's dive in", "dive into",
    "in conclusion", "in summary", "to sum up", "rest assured",
    "a wide range of", "a wide variety of", "the power of", "powerful",
    "comprehensive", "crucial", "vital",
]

# Figures of speech. A list cannot catch every metaphor; reread for the rest.
METAPHORS = [
    "under the hood", "under the covers", "heavy lifting", "gatekeeper",
    "the heart of", "at its heart", "the backbone of", "cornerstone",
    "north star", "low-hanging fruit", "moving parts", "bells and whistles",
    "silver bullet", "boils down to", "at the end of the day",
    "double-edged sword", "deep dive", "rabbit hole", "sweet spot",
    "first-class citizen", "baked in", "in the weeds", "move the needle",
    "on the radar", "landscape", "journey", "realm", "ecosystem",
    "unlock", "unlocks", "unlocking", "glue code", "plumbing", "magic",
    "magically", "breathe", "breathes", "drown", "drowns", "tip of the iceberg",
    "the elephant in the room", "a perfect storm", "the lion's share",
    "bridge the gap", "paves the way", "pave the way", "shines", "shine",
    "a love letter", "a symphony", "dance", "dances", "orchestrates",
    "under one roof", "hand-holding", "out of the box",
]

VAGUE = [
    "significantly", "dramatically", "drastically", "massively", "greatly",
    "vastly", "hugely", "substantially", "considerably", "much faster",
    "much slower", "much smaller", "much larger", "much better", "far faster",
    "a lot faster", "a lot smaller", "way faster", "huge", "tiny",
]

RULES = {
    "em-dash": ("error", "Use a period and start a new sentence instead of a dash."),
    "javascript": ("error", "Do not write 'JavaScript'. Name the file type (`.js`) or leave it out."),
    "stock": ("error", "Stock or marketing phrase. Say the specific thing instead."),
    "metaphor": ("error", "Figure of speech. Say what the thing does in plain terms."),
    "wordy": ("error", "Wordy phrase with a shorter form."),
    "subject-length": ("error", f"Commit subject over {MAX_SUBJECT} characters."),
    "semicolon": ("warning", "Semicolon joins two points. Split them into sentences or list items."),
    "long-sentence": ("warning", f"Sentence over {MAX_WORDS} words. Split it."),
    "filler": ("warning", "Filler word. Delete it unless it changes the meaning."),
    "hedge": ("warning", "Hedge. State it, or say what is uncertain and why."),
    "vague": ("warning", "Size claim without a number. Give the measurement."),
}


def _pattern(phrases):
    escaped = sorted((re.escape(p) for p in phrases), key=len, reverse=True)
    return re.compile(r"(?<![\w-])(" + "|".join(escaped) + r")(?![\w-])", re.IGNORECASE)


PATTERNS = {
    "stock": _pattern(STOCK),
    "metaphor": _pattern(METAPHORS),
    "wordy": _pattern(WORDY),
    "filler": _pattern(FILLER),
    "hedge": _pattern(HEDGES),
    "vague": _pattern(VAGUE),
}


def strip_code(text):
    """Blank out fenced code blocks and inline code, keeping line numbers."""
    out, fence = [], None
    for line in text.split("\n"):
        m = re.match(r"\s*(```+|~~~+)", line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
            out.append("")
            continue
        if m:
            fence = m.group(1)
            out.append("")
            continue
        if re.match(r"(    |\t)", line) and not re.match(r"\s*([-*+]|\d+\.)\s", line):
            out.append("")
            continue
        out.append(re.sub(r"`[^`]*`", "`x`", line))
    return out


def extract_comments(text):
    """Keep only comment text from source code, keeping line numbers."""
    out = []
    in_block = False
    for line in text.split("\n"):
        s = line.strip()
        if in_block:
            out.append(re.sub(r"^\*+\s?|\*/.*$", "", s))
            if "*/" in s:
                in_block = False
            continue
        m = re.search(r"(^|\s)(//+|#+|--)\s?(.*)$", line)
        if s.startswith("/*"):
            in_block = "*/" not in s
            out.append(re.sub(r"^/\*+\s?|\*/.*$", "", s))
        elif m and not s.startswith("#!"):
            out.append(m.group(3))
        else:
            out.append("")
    return out


def sentences(line):
    return [s for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]


def check_lines(lines, name, subject_line=None):
    findings = []

    def add(n, rule, text):
        level, msg = RULES[rule]
        findings.append((name, n, level, rule, msg, text))

    for n, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if re.match(r"\s*\|", line):
            body = line  # table rows: check phrases, not sentence length
        else:
            body = None
        if re.search(r"—|–|\s--\s", line):
            add(n, "em-dash", line.strip())
        if re.search(r"\bjavascript\b", line, re.IGNORECASE):
            add(n, "javascript", line.strip())
        for rule, pat in PATTERNS.items():
            for m in pat.finditer(line):
                hit = m.group(1)
                if rule == "vague" and re.search(r"\d", line):
                    continue
                note = hit
                if rule == "wordy":
                    sug = WORDY.get(hit.lower(), "")
                    note = f"{hit} -> {sug}" if sug else f"{hit} -> delete"
                add(n, rule, note)
        if body is None:
            if re.search(r"\w;\s+\w", line):
                add(n, "semicolon", line.strip())
            for s in sentences(line):
                words = len(re.findall(r"[\w'`-]+", s))
                if words > MAX_WORDS:
                    add(n, "long-sentence", f"{words} words: {s.strip()[:60]}...")
    if subject_line is not None and len(subject_line) > MAX_SUBJECT:
        add(1, "subject-length", f"{len(subject_line)} chars")
    return findings


def check_text(text, name, comments=False, commit=False):
    lines = extract_comments(text) if comments else strip_code(text)
    subject = text.split("\n", 1)[0] if commit else None
    return check_lines(lines, name, subject)


def commit_messages(rng):
    out = subprocess.run(["git", "log", "--format=%H%x00%B%x1e", rng],
                         capture_output=True, text=True, check=True).stdout
    for rec in out.split("\x1e"):
        rec = rec.strip("\n")
        if rec:
            sha, _, body = rec.partition("\x00")
            body = "\n".join(l for l in body.strip().split("\n")
                             if not re.match(r"(Co-Authored-By|Signed-off-by):", l, re.I))
            yield sha[:8], body


def print_list():
    for rule, (level, msg) in RULES.items():
        print(f"{level:7} {rule}: {msg}")
    for title, items in (("stock", STOCK), ("metaphor", METAPHORS), ("filler", FILLER),
                         ("hedge", HEDGES), ("vague", VAGUE)):
        print(f"\n{title}: " + ", ".join(items))
    print("\nwordy: " + ", ".join(f"{k} -> {v or 'delete'}" for k, v in WORDY.items()))


def report(findings, quiet_warnings=False):
    errors = 0
    for name, n, level, rule, msg, text in findings:
        if level == "error":
            errors += 1
        elif quiet_warnings:
            continue
        print(f"{name}:{n}: {level} {rule}: {msg} [{text}]")
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--comments", action="store_true", help="check only comments in source files")
    ap.add_argument("--commit", metavar="RANGE", help="check commit messages in a git range")
    ap.add_argument("--errors-only", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        print_list()
        return
    findings = []
    if args.commit:
        for sha, body in commit_messages(args.commit):
            findings += check_text(body, f"commit {sha}", commit=True)
    for f in args.files:
        text = sys.stdin.read() if f == "-" else open(f, encoding="utf-8").read()
        findings += check_text(text, "stdin" if f == "-" else f, comments=args.comments)
    if not args.files and not args.commit:
        ap.error("give files, '-', --commit RANGE or --list")
    errors = report(findings, args.errors_only)
    if not findings:
        print("prose: ok")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()

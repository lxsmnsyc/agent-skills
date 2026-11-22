#!/usr/bin/env python3
"""Count the words of a built landing page, per section and in total.

Counts text inside <main> (or <body> when there is no <main>). Code blocks,
scripts, styles, elements with the hidden attribute or aria-hidden="true", and
anything matching --exclude are left out.

Usage:
  word_count.py dist/index.html [--budget 600] [--exclude "#faq"] [--exclude ".static-steps"]

--exclude takes a tag name, .class, #id or [attribute], and can repeat.
Exits 1 when --budget is given and the total is over it.
"""

import argparse
import re
import sys
from html.parser import HTMLParser

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
}
SKIPPED_TAGS = {"pre", "code", "script", "style", "template", "noscript"}
WORD = re.compile(r"[\w'’.-]*\w[\w'’.-]*")


def parse_selector(text):
    if text.startswith("."):
        return ("class", text[1:])
    if text.startswith("#"):
        return ("id", text[1:])
    if text.startswith("[") and text.endswith("]"):
        return ("attr", text[1:-1])
    return ("tag", text.lower())


def matches_selector(selector, tag, attrs):
    kind, value = selector
    if kind == "tag":
        return tag == value
    if kind == "id":
        return attrs.get("id") == value
    if kind == "class":
        return value in (attrs.get("class") or "").split()
    return value in attrs


class WordCounter(HTMLParser):
    def __init__(self, excludes):
        super().__init__(convert_charrefs=True)
        self.excludes = excludes
        self.has_main = False
        # Each stack entry: (tag, skips text, section label)
        self.stack = []
        self.main_words = 0
        self.body_words = 0
        self.sections = []

    def is_skipped(self):
        return any(entry[1] for entry in self.stack)

    def in_tag(self, name):
        return any(entry[0] == name for entry in self.stack)

    def handle_starttag(self, tag, attr_list):
        attrs = {key: (value or "") for key, value in attr_list}
        skips = (
            tag in SKIPPED_TAGS
            or "hidden" in attrs
            or attrs.get("aria-hidden") == "true"
            or any(matches_selector(selector, tag, attrs) for selector in self.excludes)
        )
        if tag == "main":
            self.has_main = True
        # Label top-level sections inside main by id, aria-label or order
        label = None
        if tag == "section" and not self.in_tag("section"):
            label = attrs.get("id") or attrs.get("aria-label") or f"section {len(self.sections) + 1}"
            self.sections.append([label, 0])
        if tag in VOID:
            return
        self.stack.append((tag, skips, label))

    def handle_endtag(self, tag):
        # Pop to the matching tag, tolerating unclosed children
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        if self.is_skipped() or not (self.in_tag("body") or self.in_tag("main")):
            return
        count = len(WORD.findall(data))
        if count == 0:
            return
        self.body_words += count
        if self.in_tag("main"):
            self.main_words += count
        if self.in_tag("section") and self.sections:
            self.sections[-1][1] += count


def count_words(html, excludes):
    counter = WordCounter([parse_selector(text) for text in excludes])
    counter.feed(html)
    counter.close()
    total = counter.main_words if counter.has_main else counter.body_words
    return total, counter.sections


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file")
    parser.add_argument("--budget", type=int)
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()

    with open(args.file, encoding="utf-8") as handle:
        html = handle.read()
    total, sections = count_words(html, args.exclude)

    for label, words in sections:
        print(f"{words:6d}  {label}")
    print(f"{total:6d}  total")
    if args.budget is not None:
        if total > args.budget:
            print(f"over budget: {total} > {args.budget} words", file=sys.stderr)
            return 1
        print(f"within budget: {total} <= {args.budget} words")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Tests for skills/docs-site/scripts. Run: python3 -m unittest discover tests"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/docs-site/scripts/docs_check.py"
TEMPLATES = Path(__file__).resolve().parents[1] / "skills/docs-site/templates"

PAGES = {
    "index.md": """---
title: Docs
type: index
---

# Docs

- [Getting started](getting-started.md)
- [Signals](concepts/signals.md)
- [Deploy](/guides/deploy)
""",
    "getting-started.md": """---
title: Getting started
type: tutorial
---

Build a counter in five minutes.

## Before you start

- Node 20.

## Next steps

- [Signals](concepts/signals.md)
""",
    "concepts/signals.md": """---
title: Signals
type: feature
---

# Signals

A signal holds a value and tells readers when it changes.

```ts
const count = createSignal(0);
```

## Why

Fine-grained updates.

## How it works

Reads subscribe.

## Usage

```
count.set(1);
```

## Related

- [Deploy](../guides/deploy.md#vercel)
- [Missing](../guides/missing.md)
- [Inline code is skipped](`../nope.md`)
""",
    "guides/deploy.md": """---
title: Deploy
type: guide
---

## Steps

Deploy the app.
""",
    "reference/api.md": """---
title: API
type: reference
---

The public API.

## `createSignal`
""",
    "internals/compiler.md": """---
title: How the compiler works
type: internals
covers: [src/compiler, "src/gone.ts"]
---

How source becomes split chunks. For contributors.

## Stages

Parse, then split.

## Related

- [Signals](../concepts/signals.md)
""",
    "internals/index.md": """---
title: Internals
type: index
---

- [Compiler](compiler.md)
""",
    "concepts/a.md": """---
title: A
type: concept
order: 2
requires: [b.md, missing.md]
---

Needs [B](b.md).

## Related

- [B](b.md)
""",
    "concepts/b.md": """---
title: B
type: concept
order: 3
requires: [c.md]
---

Comes first.

## Related

- [A](a.md)
""",
    "concepts/c.md": """---
title: C
type: concept
requires: [b.md]
---

Part of a cycle.

## Related

- [A](a.md)
""",
    "orphan.md": """---
title: Orphan
type: wrongtype
---

Nobody links here.
""",
}

ENTRY = """/** Creates a signal. */
export function createSignal() {}
export const createEffect = () => {};
export { batch, untrack as peek, type Accessor } from "./core";
export default createSignal;
"""


class DocsCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "docs"
        for name, text in PAGES.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.entry = Path(self.tmp.name) / "index.ts"
        self.entry.write_text(ENTRY)

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *extra):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root), "--json", *extra],
            capture_output=True,
            text=True,
        )
        return result.returncode, json.loads(result.stdout)["findings"]

    def messages_for(self, findings, file):
        found = []
        for finding in findings:
            if finding["file"] == file:
                found.append((finding["level"], finding["message"]))
        return found

    def test_exit_code_follows_errors(self):
        code, _ = self.run_script()
        self.assertEqual(code, 1)

    def test_valid_pages_pass(self):
        _, findings = self.run_script()
        self.assertEqual(self.messages_for(findings, "getting-started.md"), [])
        self.assertEqual(self.messages_for(findings, "index.md"), [])

    def test_feature_page(self):
        _, findings = self.run_script()
        messages = self.messages_for(findings, "concepts/signals.md")
        self.assertIn(("error", "broken link `../guides/missing.md`"), messages)
        self.assertIn(("warning", "code block has no language"), messages)
        # H1 title is skipped when looking for the lead; anchors and inline code are fine
        self.assertEqual(len(messages), 2)

    def test_guide_without_steps_or_related_or_lead(self):
        _, findings = self.run_script()
        messages = self.messages_for(findings, "guides/deploy.md")
        self.assertIn(("error", "guide page has no `Related` section"), messages)
        self.assertIn(("error", "guide has no numbered steps"), messages)
        self.assertIn(
            ("warning", "page starts with a heading; add a lead sentence above it"), messages
        )

    def test_unknown_type_and_orphans(self):
        _, findings = self.run_script()
        messages = self.messages_for(findings, "orphan.md")
        self.assertEqual(messages[0][0], "error")
        self.assertIn("unknown type `wrongtype`", messages[0][1])
        self.assertIn(("warning", "no other page links here"), messages)
        self.assertIn(("warning", "no other page links here"), self.messages_for(findings, "reference/api.md"))

    def test_entry_skips_orphan_check(self):
        _, findings = self.run_script("--entry", "reference/api.md")
        self.assertEqual(self.messages_for(findings, "reference/api.md"), [])

    def test_exports_without_reference(self):
        _, findings = self.run_script(
            "--exports", str(self.entry), "--reference", str(self.root / "reference")
        )
        missing = set()
        for finding in findings:
            if "has no reference entry" in finding["message"]:
                missing.add(finding["message"].split("`")[1])
        self.assertEqual(missing, {"createEffect", "batch", "peek", "Accessor"})

    def test_internals_requires_overview(self):
        _, findings = self.run_script()
        messages = self.messages_for(findings, "internals/compiler.md")
        self.assertEqual(messages, [("error", "internals page has no `Overview` section")])

    def test_covers_paths_checked_with_repo(self):
        (Path(self.tmp.name) / "src/compiler").mkdir(parents=True)
        _, findings = self.run_script("--repo", self.tmp.name)
        messages = self.messages_for(findings, "internals/compiler.md")
        self.assertIn(("error", "covered path `src/gone.ts` does not exist"), messages)
        self.assertEqual(len(messages), 2)

    def test_requires(self):
        _, findings = self.run_script()
        a = self.messages_for(findings, "concepts/a.md")
        self.assertIn(("error", "broken link in requires: `missing.md`"), a)
        self.assertIn(("error", "required page `b.md` must come earlier in the order"), a)
        b = self.messages_for(findings, "concepts/b.md")
        self.assertIn(("warning", "required page `c.md` is not linked from the page"), b)
        cycles = []
        for finding in findings:
            if finding["message"].startswith("requires cycle"):
                cycles.append(finding["message"])
        self.assertEqual(len(cycles), 1)
        self.assertIn("concepts/b.md", cycles[0])
        self.assertIn("concepts/c.md", cycles[0])

    def test_exports_without_doc_comment(self):
        _, findings = self.run_script(
            "--exports", str(self.entry), "--reference", str(self.root / "reference")
        )
        undocumented = set()
        for finding in findings:
            if "has no doc comment" in finding["message"]:
                undocumented.add(finding["message"].split("`")[1])
        self.assertEqual(undocumented, {"createEffect"})

    def test_translation(self):
        base = Path(self.tmp.name)
        source = base / "site/en"
        target = base / "site/ja"
        for folder in (source, target):
            folder.mkdir(parents=True)
        (source / "index.md").write_text("---\ntype: index\n---\n\n## Why {#why}\n\n## Use {#use}\n")
        (source / "only-source.md").write_text("---\ntype: index\n---\n\nText.\n")
        (target / "index.md").write_text("---\ntype: index\n---\n\n## Naze {#why}\n")
        (target / "extra.md").write_text("---\ntype: index\n---\n\nText.\n")

        def git(*args, date):
            env = {"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date, "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
            subprocess.run(["git", *args], cwd=base, env=env, check=True, capture_output=True)

        git("init", "-q", date="2026-01-01T00:00:00")
        git("-c", "user.name=t", "-c", "user.email=t@t", "add", "-A", date="2026-01-01T00:00:00")
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "one", date="2026-01-01T00:00:00")
        (source / "index.md").write_text((source / "index.md").read_text() + "\nMore.\n")
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "two", date="2026-02-01T00:00:00")

        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(source), "--json", "--translation", str(target)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        messages = set()
        for finding in json.loads(result.stdout)["findings"]:
            messages.add((finding["level"], finding["message"]))
        self.assertIn(("warning", "no translation of `only-source.md`"), messages)
        self.assertIn(("error", "translated page `extra.md` has no source page"), messages)
        self.assertIn(("warning", "heading id `use` from the source is missing"), messages)
        self.assertIn(
            ("warning", "source changed on 2026-02-01, translation last changed on 2026-01-01"), messages
        )

    def test_templates_have_their_required_sections(self):
        # Templates hold placeholder links, so only structure errors count here
        with tempfile.TemporaryDirectory() as tmp:
            for template in TEMPLATES.glob("*.md"):
                (Path(tmp) / template.name).write_text(template.read_text())
            result = subprocess.run(
                [sys.executable, str(SCRIPT), tmp, "--json"], capture_output=True, text=True
            )
            for finding in json.loads(result.stdout)["findings"]:
                if finding["level"] == "error":
                    self.assertIn("broken link", finding["message"], finding)


if __name__ == "__main__":
    unittest.main()

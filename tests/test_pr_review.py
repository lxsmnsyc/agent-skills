"""Tests for skills/pr-review/scripts. Run: python3 -m unittest discover tests"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/pr-review/scripts"


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, shell=True, check=True, capture_output=True, text=True).stdout


def script(name, *args, cwd):
    return subprocess.run([sys.executable, str(SCRIPTS / name), *args], cwd=cwd,
                          capture_output=True, text=True)


class PrReviewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        r = self.repo
        sh("git init -q -b main && git config user.name T && git config user.email t@example.com", r)
        (r / "package.json").write_text(json.dumps(
            {"name": "x", "type": "module", "scripts": {"test": "node --test", "lint": "node -e 0"}}))
        (r / "sum.js").write_text("export const sum = (xs) => xs.slice(1).reduce((a, b) => a + b, 0);\n")
        (r / "sum.test.js").write_text(
            'import { test } from "node:test";\nimport assert from "node:assert";\n'
            'import { sum } from "./sum.js";\ntest("empty", () => assert.equal(sum([]), 0));\n')
        sh("git add -A && git commit -qm init && git checkout -qb fix/sum", r)
        (r / "sum.js").write_text("export const sum = (xs) => xs.reduce((a, b) => a + b, 0);\n")
        with open(r / "sum.test.js", "a") as f:  # the fix edits an existing test file
            f.write('test("all", () => assert.equal(sum([1, 2]), 3));\n')
        sh("git add -A && git commit -qm 'fix: sum skipped the first item' && git checkout -q main", r)

    def tearDown(self):
        script("worktrees.py", "cleanup", "--all", cwd=self.repo)
        self.tmp.cleanup()

    def prepare(self):
        out = script("worktrees.py", "prepare", "--base", "main", "--head", "fix/sum", cwd=self.repo)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_pr_info_local(self):
        out = script("pr_info.py", "--local", "--base", "main", "--head", "fix/sum", cwd=self.repo)
        info = json.loads(out.stdout)
        self.assertEqual(info["type_hint"], "fix")
        self.assertEqual(sorted(f["path"] for f in info["files"]), ["sum.js", "sum.test.js"])
        blind = json.loads(script("pr_info.py", "--local", "--base", "main", "--head", "fix/sum", "--blind",
                                  cwd=self.repo).stdout)
        self.assertNotIn("files", blind)
        self.assertEqual(blind["title"], info["title"])

    def test_notes_folder_outside_checkouts_is_cleaned(self):
        out = self.prepare()
        notes = Path(out["notes"])
        self.assertTrue(notes.is_dir())
        self.assertFalse(str(notes).startswith(out["head"]))
        (notes / "expectations.md").write_text("- docs/cli.md mentions the flag\n")
        script("worktrees.py", "cleanup", "--all", cwd=self.repo)
        self.assertFalse(notes.exists())

    def test_hotfix_branch_is_typed_hotfix(self):
        sys.path.insert(0, str(SCRIPTS))
        import pr_info
        self.assertEqual(pr_info.type_hint("fix: subtotal", [], "hotfix/subtotal"), "hotfix")
        self.assertEqual(pr_info.type_hint("fix: subtotal", [], "fix/subtotal"), "fix")

    def test_repro_proves_fix_with_edited_test_file(self):
        wt = self.prepare()
        before = (Path(wt["base"]) / "sum.test.js").read_text()
        out = script("repro.py", wt["base"], wt["head"], "--copy", "sum.test.js", "--",
                     "node", "--test", "sum.test.js", cwd=self.repo)
        self.assertEqual(json.loads(out.stdout)["verdict"], "proven")
        self.assertEqual((Path(wt["base"]) / "sum.test.js").read_text(), before)

    def test_repro_not_reproduced(self):
        wt = self.prepare()
        out = script("repro.py", wt["base"], wt["head"], "--", "node", "-e", "0", cwd=self.repo)
        self.assertEqual(json.loads(out.stdout)["verdict"], "not-reproduced")

    def test_cleanup_reports_leftovers_and_all_removes_them(self):
        self.prepare()
        out = script("worktrees.py", "cleanup", "wrong-name", cwd=self.repo)
        self.assertIn("still registered", out.stdout)
        out = script("worktrees.py", "cleanup", "--all", cwd=self.repo)
        self.assertIn("no review worktrees left", out.stdout)
        self.assertEqual(len(sh("git worktree list", self.repo).splitlines()), 1)

    def test_worktrees_live_inside_git_dir(self):
        wt = self.prepare()
        self.assertIn("/.git/review-worktrees/", wt["base"])
        self.assertEqual(sh("git status --porcelain", self.repo), "")

    def test_prepare_copies_worktreeinclude_files(self):
        (self.repo / ".gitignore").write_text(".env\n")
        (self.repo / ".worktreeinclude").write_text(".env\n")
        (self.repo / ".env").write_text("SECRET=1\n")
        wt = self.prepare()
        self.assertEqual(wt["copied"], [".env"])
        for side in ("base", "head"):
            self.assertEqual((Path(wt[side]) / ".env").read_text(), "SECRET=1\n")

    def test_checks_detects_scripts(self):
        out = script("checks.py", str(self.repo), "--json", cwd=self.repo)
        found = json.loads(out.stdout)
        self.assertEqual(found["checks"]["test"], "npm run test")
        self.assertIn("build", found["missing"])


class ChangedChecksTest(unittest.TestCase):
    """checks.py --changed: each check runs on the changed files only."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        r = self.repo
        sh("git init -q -b main && git config user.name T && git config user.email t@example.com", r)
        (r / ".gitignore").write_text("node_modules\n")
        (r / "package.json").write_text(json.dumps({"name": "x", "type": "module", "scripts": {
            "lint": "oxlint --type-aware src", "format:check": "prettier --check .",
            "typecheck": "tsc --noEmit", "test": "node --test"}}))
        (r / "src").mkdir()
        (r / "src/sum.js").write_text("export const sum = (a, b) => a + b;\n")
        (r / "src/other.js").write_text("export const other = 1;\n")
        (r / "src/sum.test.js").write_text(
            'import { test } from "node:test";\nimport assert from "node:assert";\n'
            'import { sum } from "./sum.js";\ntest("sum", () => assert.equal(sum(1, 2), 3));\n')
        (r / "src/other.test.js").write_text('import { test } from "node:test";\n'
                                             'test("other", () => { throw new Error("must not run"); });\n')
        sh("git add -A && git commit -qm init && git checkout -qb feat/x", r)

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self):
        out = script("checks.py", str(self.repo), "--changed", "main", "--json", cwd=self.repo)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)["checks"]

    def test_lint_format_and_tests_take_changed_files(self):
        (self.repo / "src/sum.js").write_text("export const sum = (a, b) => b + a;\n")
        plan = self.plan()
        self.assertEqual(plan["lint"][0]["command"], "npm exec oxlint --type-aware src/sum.js")
        self.assertEqual(plan["format"][0]["command"], "npm exec prettier --check --ignore-unknown src/sum.js")
        self.assertEqual(plan["test"][0]["command"], "node --test src/sum.test.js")
        self.assertEqual(plan["typecheck"][0]["command"], "npm run typecheck")

    def test_run_skips_unrelated_tests(self):
        (self.repo / "src/sum.js").write_text("export const sum = (a, b) => b + a;\n")
        out = script("checks.py", str(self.repo), "--changed", "main", "--run", "--only", "test", cwd=self.repo)
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertIn("src/sum.test.js", out.stdout)

    def test_root_config_change_runs_everything(self):
        (self.repo / "tsconfig.json").write_text("{}\n")
        plan = self.plan()
        self.assertEqual(plan["lint"][0]["command"], "npm run lint")
        self.assertIn("tsconfig.json", plan["test"][0]["scope"])

    def test_no_changes_runs_nothing(self):
        out = script("checks.py", str(self.repo), "--changed", "main", "--run", cwd=self.repo)
        self.assertEqual(out.returncode, 0)
        self.assertIn("no changed files", out.stdout)

    def test_pnpm_workspace_typecheck_covers_dependents(self):
        r = self.repo
        (r / "pnpm-lock.yaml").write_text("")
        (r / "pnpm-workspace.yaml").write_text("packages:\n  - packages/*\n")
        (r / "packages/a/src").mkdir(parents=True)
        (r / "packages/a/package.json").write_text(json.dumps({"name": "a", "scripts": {"typecheck": "tsc"}}))
        (r / "packages/a/src/i.ts").write_text("export const i = 1;\n")
        sh("git add -A && git commit -qm workspace", r)
        sh("git checkout -q main && git merge -q feat/x && git checkout -q feat/x", r)
        (r / "packages/a/src/i.ts").write_text("export const i = 2;\n")
        plan = self.plan()
        self.assertRegex(plan["typecheck"][0]["command"], r'^pnpm --filter "\.\.\.\[[0-9a-f]+\]" --if-present run typecheck$')


class SurfaceTest(unittest.TestCase):
    """surface.py: mentions outside the diff of what the diff removed or changed."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        sh("git init -q -b main && git config user.name T && git config user.email t@example.com", self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def surface(self):
        r = script("surface.py", "--base", "main", "--head", "HEAD", "--json", cwd=self.repo)
        return r.returncode, json.loads(r.stdout)

    def base(self):
        self.write("src/date.ts", "export function parseDate(s: string) { return new Date(s) }\n"
                                  "export function formatDate(d: Date) { return d.toISOString() }\n")
        self.write("src/cli.ts", "if (args.includes('--dry-run')) dry = true\n"
                                 "throw new Error('missing input file name')\n")
        self.write("README.md", "Call `parseDate(s)` to read a date.\nPass `--dry-run` to preview.\n"
                                "See formatDate for output.\n")
        self.write("CHANGELOG.md", "- added parseDate\n")
        sh("git add -A && git commit -qm base && git switch -qc feat/x", self.repo)

    def test_rename_and_removed_flag_leave_stale_docs(self):
        self.base()
        self.write("src/date.ts", "export function parseDay(s: string) { return new Date(s) }\n"
                                  "export function formatDate(d: Date, utc = true) { return d.toISOString() }\n")
        self.write("src/cli.ts", "throw new Error('no input file given')\n")
        sh("git commit -qam rename", self.repo)
        code, out = self.surface()
        self.assertEqual(code, 1)
        stale = {s["term"]: s for s in out["stale"]}
        self.assertIn("parseDate", stale)
        self.assertEqual([m["file"] for m in stale["parseDate"]["mentions"]], ["README.md"])  # changelog skipped
        self.assertIn("--dry-run", stale)
        self.assertEqual([c["term"] for c in out["changed"]], ["formatDate"])

    def test_updated_docs_leave_nothing(self):
        self.base()
        self.write("src/date.ts", "export function parseDay(s: string) { return new Date(s) }\n"
                                  "export function formatDate(d: Date) { return d.toISOString() }\n")
        self.write("README.md", "Call `parseDay(s)` to read a date.\nPass `--dry-run` to preview.\n"
                                "See formatDate for output.\n")
        sh("git commit -qam rename", self.repo)
        code, out = self.surface()
        self.assertEqual(out["stale"], [], out)
        self.assertEqual(code, 0)

    def test_missing_changeset(self):
        self.write(".changeset/config.json", "{}\n")
        self.write("src/a.ts", "export const alpha = 1\n")
        sh("git add -A && git commit -qm base && git switch -qc feat/y", self.repo)
        self.write("src/a.ts", "export const alpha = 2\n")
        sh("git commit -qam change", self.repo)
        _, out = self.surface()
        self.assertTrue(out["changeset_missing"])
        self.write(".changeset/brave-cats.md", "---\n'x': patch\n---\n\nChange alpha.\n")
        sh("git add -A && git commit -qm changeset", self.repo)
        _, out = self.surface()
        self.assertFalse(out["changeset_missing"])


if __name__ == "__main__":
    unittest.main()

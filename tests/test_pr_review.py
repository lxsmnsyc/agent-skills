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

    def test_checks_detects_scripts(self):
        out = script("checks.py", str(self.repo), "--json", cwd=self.repo)
        found = json.loads(out.stdout)
        self.assertEqual(found["checks"]["test"], "npm run test")
        self.assertIn("build", found["missing"])


if __name__ == "__main__":
    unittest.main()

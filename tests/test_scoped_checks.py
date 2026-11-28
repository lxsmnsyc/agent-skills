"""Tests for skills/scoped-checks/scripts. Run: python3 -m unittest discover tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/scoped-checks/scripts"


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, shell=True, check=True, capture_output=True, text=True).stdout


def script(name, *args, cwd):
    return subprocess.run([sys.executable, str(SCRIPTS / name), *args], cwd=cwd,
                          capture_output=True, text=True)


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

    def test_detects_scripts(self):
        found = json.loads(script("checks.py", str(self.repo), "--json", cwd=self.repo).stdout)
        self.assertEqual(found["checks"]["test"], "npm run test")
        self.assertIn("build", found["missing"])

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


class HookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "package.json").write_text("{}")
        (self.dir / "src").mkdir()
        (self.dir / "src/a.ts").write_text("")

    def tearDown(self):
        self.tmp.cleanup()

    def hook(self, command, mode="block"):
        event = {"tool_name": "Bash", "cwd": str(self.dir), "tool_input": {"command": command}}
        return subprocess.run([sys.executable, str(SCRIPTS / "hook.py")], input=json.dumps(event),
                              capture_output=True, text=True, env={**os.environ, "SCOPED_CHECKS_HOOK": mode})

    def test_blocks_full_runs(self):
        for cmd in ("pnpm test", "npm run lint", "pnpm -r test", "pnpm exec vitest run", "npx eslint .",
                    "prettier --check .", "oxfmt", "ruff check .", "pytest tests/", "python3 -m pytest",
                    "go test ./...", "cd src && pnpm lint", "pnpm build && pnpm test",
                    "python3 /x/checks.py . --run"):
            r = self.hook(cmd)
            self.assertEqual(r.returncode, 2, cmd)
            self.assertIn("SCOPED_CHECKS=full", r.stderr)

    def test_allows_scoped_runs(self):
        for cmd in ("pnpm exec vitest run src/a.test.ts", "vitest related --run src/a.ts",
                    "jest --findRelatedTests src/a.ts", "pnpm exec oxlint --type-aware src/a.ts",
                    "pnpm --filter a test", "pnpm -C packages/a test", "pnpm test -- src/a.test.ts",
                    "pytest tests/test_a.py", "python3 /x/checks.py . --run --changed main",
                    "SCOPED_CHECKS=full pnpm test", "pnpm build", "git status", "pnpm typecheck",
                    "vitest run -c vitest.config.ts src/a.test.ts"):
            self.assertEqual(self.hook(cmd).returncode, 0, cmd)

    def test_workspace_typecheck_is_full(self):
        (self.dir / "pnpm-workspace.yaml").write_text("packages:\n  - packages/*\n")
        self.assertEqual(self.hook("pnpm typecheck").returncode, 2)

    def test_warn_and_off_let_it_run(self):
        self.assertEqual(self.hook("pnpm test", mode="warn").returncode, 0)
        self.assertEqual(self.hook("pnpm test", mode="").returncode, 0)


if __name__ == "__main__":
    unittest.main()

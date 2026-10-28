"""Tests for skills/repo-setup/scripts. Run: python3 -m unittest discover tests"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills/repo-setup"


def audit(root):
    r = subprocess.run([sys.executable, str(SKILL / "scripts/audit.py"), str(root), "--offline", "--json"],
                       capture_output=True, text=True)
    return r.returncode, {f["check"]: f for f in json.loads(r.stdout)}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class AuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def setup_from_templates(self):
        t = SKILL / "templates"
        root = self.root
        pkg = json.loads((t / "package.json").read_text())
        pkg["packageManager"] = "pnpm@12.0.0"
        pkg["devDependencies"] = {"@changesets/cli": "^3.0.0"}
        write(root / "package.json", json.dumps(pkg))
        write(root / "pnpm-lock.yaml", "")
        shutil.copy(t / "pnpm-workspace.yaml", root)
        write(root / ".changeset/config.json", (t / "changeset-config.json").read_text())
        for name in ("oxlint.config.ts", "oxfmt.config.ts", "LICENSE"):
            shutil.copy(t / name, root)
        for name in ("check.yml", "release.yml"):
            write(root / ".github/workflows" / name, (t / "workflows" / name).read_text())
        lib = root / "packages/lib"
        write(lib / "package.json", json.dumps({"name": "lib", "scripts": {"build": "tsdown"},
                                                "devDependencies": {"vitest": "^5.0.0"}}))
        shutil.copy(t / "tsdown.config.ts", lib)
        for folder in ("examples", "benchmarks", "docs"):
            (root / folder).mkdir()

    def test_templates_pass_the_audit(self):
        self.setup_from_templates()
        code, found = audit(self.root)
        self.assertEqual(code, 0, {k: v for k, v in found.items() if v["status"] not in ("ok", "info")})
        self.assertEqual(found["tsdown: lib"]["status"], "ok")
        self.assertEqual(found["release workflow"]["status"], "ok")
        self.assertNotIn("environments", found)

    def test_old_tools_need_migration(self):
        write(self.root / "package.json", json.dumps({"name": "old", "scripts": {"build": "tsup"},
                                                      "devDependencies": {"tsup": "1", "jest": "1"}}))
        write(self.root / "package-lock.json", "{}")
        write(self.root / "biome.json", "{}")
        write(self.root / "LICENSE", "ISC License")
        write(self.root / ".github/workflows/release.yml",
              "on: push\njobs:\n  r:\n    steps:\n      - uses: changesets/action@v1\n"
              "        env:\n          NPM_TOKEN: x\n")
        (self.root / "benchmark").mkdir()
        code, found = audit(self.root)
        self.assertEqual(code, 1)
        for check in ("pnpm", "tsdown: old", "vitest", "other linters", "license", "release workflow",
                      "benchmarks/"):
            self.assertEqual(found[check]["status"], "migrate", check)
        self.assertIn("trusted publishing", found["release workflow"]["detail"])
        self.assertEqual(found["changesets"]["status"], "missing")
        self.assertEqual(found["check workflow"]["status"], "missing")

    def test_check_workflow_gaps_and_environments(self):
        self.setup_from_templates()
        write(self.root / ".github/workflows/check.yml",
              "on:\n  pull_request:\njobs:\n  c:\n    steps:\n      - run: pnpm test\n")
        release = self.root / ".github/workflows/release.yml"
        release.write_text(release.read_text().replace(
            "    runs-on: ubuntu-latest\n    permissions:\n      contents: write\n",
            "    runs-on: ubuntu-latest\n    environment: npm\n    permissions:\n      contents: write\n", 1))
        code, found = audit(self.root)
        self.assertEqual(code, 1)
        self.assertEqual(found["check workflow"]["status"], "migrate")
        self.assertIn("lint, format, types", found["check workflow"]["detail"])
        self.assertEqual(found["environments"]["detail"], "npm")

    def test_package_without_build_ships_source(self):
        self.setup_from_templates()
        write(self.root / "packages/ui/package.json", json.dumps({"name": "ui"}))
        _, found = audit(self.root)
        self.assertEqual(found["tsdown: ui"]["status"], "info")

    def test_private_packages_are_skipped(self):
        self.setup_from_templates()
        write(self.root / "packages/site/package.json", json.dumps({"name": "site", "private": True}))
        _, found = audit(self.root)
        self.assertNotIn("tsdown: site", found)


if __name__ == "__main__":
    unittest.main()

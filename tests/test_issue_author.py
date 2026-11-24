"""Tests for skills/issue-author/scripts. Run: python3 -m unittest discover tests"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/issue-author/scripts"
VERSIONS = SCRIPTS / "versions.py"
AFFECTS = SCRIPTS / "affects.py"


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)


class RepoCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.name", "T")
        git(self.repo, "config", "user.email", "t@example.com")

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, files, message, tag=None):
        for name, text in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", message)
        if tag:
            git(self.repo, "tag", tag)

    def package(self, version):
        return json.dumps({"name": "cart", "version": version})

    def versions(self, *extra):
        r = subprocess.run([sys.executable, str(VERSIONS), "--cwd", str(self.repo), "--json", "--offline", *extra],
                           capture_output=True, text=True, check=True)
        return {e["line"]: e for e in json.loads(r.stdout)["lines"]}


class VersionsTest(RepoCase):
    def test_current_line_is_maintained_and_old_line_is_not(self):
        self.commit({"package.json": self.package("1.0.0")}, "1.0.0", tag="v1.0.0")
        self.commit({"package.json": self.package("2.0.0")}, "2.0.0", tag="v2.0.0")
        lines = self.versions()
        self.assertEqual(lines["2.x"]["verdict"], "maintained")
        self.assertTrue(lines["2.x"]["current"])
        self.assertEqual(lines["1.x"]["verdict"], "unmaintained")
        self.assertEqual(lines["1.x"]["tag"], "v1.0.0")

    def test_recent_maintenance_branch_is_likely(self):
        self.commit({"package.json": self.package("1.0.0")}, "1.0.0", tag="v1.0.0")
        git(self.repo, "branch", "release/1.x")
        self.commit({"package.json": self.package("2.0.0")}, "2.0.0", tag="v2.0.0")
        lines = self.versions()
        self.assertEqual(lines["1.x"]["verdict"], "likely")
        self.assertEqual(lines["1.x"]["branch"], "release/1.x")

    def test_support_table_wins_over_activity(self):
        # 1.x has a fresh maintenance branch, but the support table drops it.
        self.commit({"package.json": self.package("1.0.0")}, "1.0.0", tag="v1.0.0")
        git(self.repo, "branch", "1.x")
        self.commit({"package.json": self.package("2.4.0")}, "2.4.0", tag="v2.4.0")
        self.commit({"package.json": self.package("3.0.0")}, "3.0.0", tag="v3.0.0")
        self.commit({"SECURITY.md": "| Version | Supported |\n| --- | --- |\n| 3.x | :white_check_mark: |\n"
                                    "| 2.x | :white_check_mark: |\n| < 2.0 | :x: not supported |\n"}, "policy")
        lines = self.versions()
        self.assertEqual(lines["1.x"]["verdict"], "unmaintained")
        self.assertIn("SECURITY.md", lines["1.x"]["why"])
        self.assertEqual(lines["2.x"]["verdict"], "maintained")

    def test_zero_major_lines_split_by_minor(self):
        self.commit({"package.json": self.package("0.3.1")}, "0.3.1", tag="v0.3.1")
        self.commit({"package.json": self.package("0.4.0")}, "0.4.0", tag="v0.4.0")
        lines = self.versions()
        self.assertEqual(lines["0.4.x"]["verdict"], "maintained")
        self.assertEqual(lines["0.3.x"]["verdict"], "unmaintained")


class AffectsTest(RepoCase):
    def affects(self, *refs, extra=()):
        args = [sys.executable, str(AFFECTS), "--cwd", str(self.repo), "--json", *extra]
        for ref in refs:
            args += ["--ref", ref]
        args += ["--", sys.executable, "repro.py"]
        r = subprocess.run(args, capture_output=True, text=True)
        return r.returncode, {x["ref"]: x for x in json.loads(r.stdout)["results"]}

    def test_reports_each_ref_and_copies_the_reproduction(self):
        self.commit({"lib.py": "def add(a, b):\n    return a - b\n"}, "buggy", tag="v1.0.0")
        self.commit({"lib.py": "def add(a, b):\n    return a + b\n"}, "fixed", tag="v2.0.0")
        # The reproduction exists only in the working tree, not in any ref.
        (self.repo / "repro.py").write_text(
            "import sys\nfrom lib import add\nif add(2, 2) != 4:\n    print('expected 4, got', add(2, 2))\n    sys.exit(1)\n")
        code, res = self.affects("v1.0.0", "v2.0.0", "nope", extra=["--copy", "repro.py", "--symptom", "expected 4"])
        self.assertEqual(res["v1.0.0"]["result"], "affected")
        self.assertEqual(res["v2.0.0"]["result"], "not-affected")
        self.assertEqual(res["nope"]["result"], "error")
        self.assertEqual(code, 1)
        # Worktrees are cleaned up.
        listed = subprocess.run(["git", "-C", str(self.repo), "worktree", "list"], capture_output=True, text=True).stdout
        self.assertEqual(len(listed.strip().splitlines()), 1)

    def test_failure_without_symptom_is_other_failure(self):
        self.commit({"repro.py": "raise KeyError('x')\n"}, "broken")
        code, res = self.affects("main", extra=["--symptom", "expected 4"])
        self.assertEqual(res["main"]["result"], "other-failure")
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()

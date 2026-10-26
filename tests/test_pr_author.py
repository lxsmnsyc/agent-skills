"""Tests for skills/pr-author/scripts. Run: python3 -m unittest discover tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/pr-author/scripts"


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, shell=True, check=True, capture_output=True, text=True).stdout


def script(name, *args, cwd):
    return subprocess.run([sys.executable, str(SCRIPTS / name), *args], cwd=cwd,
                          capture_output=True, text=True)


class PrAuthorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        sh("git init -q -b main && git config user.name T && git config user.email t@example.com"
           " && git commit -q --allow-empty -m init", self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def test_worktree_is_hidden_and_clean(self):
        out = json.loads(script("wt.py", "new", "feat/a", cwd=self.repo).stdout)
        self.assertTrue(out["path"].endswith(".worktrees/feat-a"))
        self.assertEqual(out["index"], 1)
        self.assertEqual(sh("git status --porcelain", self.repo), "")
        self.assertEqual(sh("git status --porcelain", out["path"]), "")
        second = json.loads(script("wt.py", "new", "fix/b", cwd=self.repo).stdout)
        self.assertEqual(second["index"], 2)

    def test_prune_merged_keeps_new_branches(self):
        a = json.loads(script("wt.py", "new", "feat/a", cwd=self.repo).stdout)["path"]
        script("wt.py", "new", "fix/b", cwd=self.repo)
        sh("echo x > f && git add f && git commit -qm f", a)
        sh("git merge -q feat/a", self.repo)
        out = script("wt.py", "prune-merged", cwd=self.repo).stdout
        self.assertIn("removed feat/a", out)
        self.assertNotIn("fix/b", out)
        self.assertIn("fix-b", sh("git worktree list", self.repo))

    def test_squash_merge_found_through_github_and_remote_deleted(self):
        origin = self.repo.parent / (self.repo.name + "-origin.git")
        sh(f"git init -q --bare {origin} && git remote add origin {origin} && git push -q origin main",
           self.repo)
        path = json.loads(script("wt.py", "new", "feat/s", cwd=self.repo).stdout)["path"]
        sh("echo x > s && git add s && git commit -qm s && git push -q origin feat/s", path)
        tip = sh("git rev-parse HEAD", path).strip()
        # A squash merge: main gets a new commit, the branch is not an ancestor of main.
        sh("git merge -q --squash feat/s && git commit -qm 'feat: s (#7)'", self.repo)
        fake = self.repo.parent / (self.repo.name + "-gh.json")
        fake.write_text(json.dumps({"feat/s": {"number": 7, "baseRefName": "main", "headRefOid": tip}}))
        env = {**os.environ, "PR_AUTHOR_FAKE_GH": str(fake)}
        out = subprocess.run([sys.executable, str(SCRIPTS / "wt.py"), "prune-merged", "--remote"],
                             cwd=self.repo, capture_output=True, text=True, env=env).stdout
        self.assertIn("removed feat/s (worktree, local branch, remote branch)", out)
        self.assertNotIn("feat/s", sh("git branch", self.repo))
        self.assertEqual(sh(f"git --git-dir {origin} branch --format='%(refname:short)'", self.repo).split(), ["main"])
        sh(f"rm -rf {origin} {fake}", self.repo)

    def test_branch_with_commits_after_merge_is_kept(self):
        path = json.loads(script("wt.py", "new", "feat/k", cwd=self.repo).stdout)["path"]
        sh("echo 1 > k && git add k && git commit -qm k1", path)
        merged_tip = sh("git rev-parse HEAD", path).strip()
        sh("echo 2 > k && git commit -qam k2", path)
        fake = self.repo.parent / (self.repo.name + "-gh2.json")
        fake.write_text(json.dumps({"feat/k": {"number": 8, "baseRefName": "main", "headRefOid": merged_tip}}))
        env = {**os.environ, "PR_AUTHOR_FAKE_GH": str(fake)}
        out = subprocess.run([sys.executable, str(SCRIPTS / "wt.py"), "prune-merged"],
                             cwd=self.repo, capture_output=True, text=True, env=env).stdout
        self.assertIn("kept feat/k", out)
        self.assertIn("feat/k", sh("git branch", self.repo))
        fake.unlink()

    def test_merge_into_dev_counts_with_several_bases(self):
        sh("git branch dev", self.repo)
        path = json.loads(script("wt.py", "new", "feat/d", "--base", "dev", cwd=self.repo).stdout)["path"]
        sh("echo d > d && git add d && git commit -qm d", path)
        sh("git checkout -q dev && git merge -q feat/d && git checkout -q main", self.repo)
        out = script("wt.py", "prune-merged", "--base", "main", "--base", "dev", cwd=self.repo).stdout
        self.assertIn("merged into dev", out)

    def test_ci_guard(self):
        wf = self.repo / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text("name: ci\non:\n  pull_request:\njobs: {}\n")
        private = script("ci_guard.py", "--visibility", "private", cwd=self.repo)
        self.assertEqual(private.returncode, 2)
        self.assertEqual(json.loads(private.stdout)["verdict"], "ask")
        public = script("ci_guard.py", "--visibility", "public", cwd=self.repo)
        self.assertEqual(json.loads(public.stdout)["verdict"], "safe")

    def test_ci_guard_without_workflows_is_safe(self):
        out = script("ci_guard.py", "--visibility", "private", cwd=self.repo)
        self.assertEqual(json.loads(out.stdout)["verdict"], "safe")

    def test_capacity_reports_a_number(self):
        out = json.loads(script("capacity.py", "--json", cwd=self.repo).stdout)
        self.assertGreaterEqual(out["recommended_parallel"], 1)


if __name__ == "__main__":
    unittest.main()

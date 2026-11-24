"""Tests for skills/changesets/scripts/hook.py. Run: python3 -m unittest discover tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "skills/changesets/scripts/hook.py"
GOOD = "---\n'pkg': minor\n---\n\nAdds `scope()` for scoped styles.\n"


def skill_line(name):
    block = {"type": "tool_use", "name": "Skill", "input": {"skill": f"agent-skills:{name}"}}
    return json.dumps({"type": "assistant", "message": {"content": [block]}})


class HookTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / ".changeset").mkdir()
        self.main = self.dir / "session.jsonl"
        self.main.write_text(skill_line("changesets") + "\n" + skill_line("plain-writing") + "\n")
        self.path = self.dir / ".changeset/add-scope.md"

    def run_hook(self, tool_input, tool="Write", mode="block", **extra):
        event = {"tool_name": tool, "transcript_path": str(self.main),
                 "tool_input": {"file_path": str(self.path), **tool_input}, **extra}
        env = {**os.environ, "CHANGESETS_HOOK": mode}
        return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event),
                              capture_output=True, text=True, env=env)

    def test_allows_short_changeset(self):
        self.assertEqual(self.run_hook({"content": GOOD}).returncode, 0)

    def test_blocks_without_skills(self):
        self.main.write_text(skill_line("changesets") + "\n")
        r = self.run_hook({"content": GOOD})
        self.assertEqual(r.returncode, 2)
        self.assertIn("agent-skills:plain-writing", r.stderr)

    def test_subagent_needs_its_own_skills(self):
        sub = self.main.with_suffix("") / "subagents"
        sub.mkdir(parents=True)
        (sub / "agent-abc.jsonl").write_text("")
        self.assertEqual(self.run_hook({"content": GOOD}, agent_id="abc").returncode, 2)
        (sub / "agent-abc.jsonl").write_text(skill_line("changesets") + "\n"
                                             + skill_line("plain-writing") + "\n")
        self.assertEqual(self.run_hook({"content": GOOD}, agent_id="abc").returncode, 0)

    def test_blocks_long_entry(self):
        body = "One. Two. Three."
        r = self.run_hook({"content": GOOD.replace("Adds `scope()` for scoped styles.", body)})
        self.assertEqual(r.returncode, 2)
        self.assertIn("3 sentences", r.stderr)

    def test_blocks_semicolon_and_bad_level(self):
        text = "---\n'pkg': feature\n---\n\nAdds a thing; it works.\n"
        r = self.run_hook({"content": text})
        self.assertEqual(r.returncode, 2)
        self.assertIn("semicolon", r.stderr)
        self.assertIn("patch|minor|major", r.stderr)

    def test_list_items_count_on_their_own(self):
        text = "---\n'pkg': patch\n---\n\n- Fixes a. Fixes b.\n- Fixes c\n  on two lines.\n"
        self.assertEqual(self.run_hook({"content": text}).returncode, 0)

    def test_checks_edit_result(self):
        self.path.write_text(GOOD)
        r = self.run_hook({"old_string": "Adds", "new_string": "Adds; and"}, tool="Edit")
        self.assertEqual(r.returncode, 2)

    def test_major_asks(self):
        r = self.run_hook({"content": GOOD.replace("minor", "major")})
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "ask")

    def test_ignores_other_files(self):
        self.path = self.dir / ".changeset/README.md"
        self.assertEqual(self.run_hook({"content": "x; y"}).returncode, 0)
        self.path = self.dir / "notes.md"
        self.assertEqual(self.run_hook({"content": "x; y"}).returncode, 0)

    def test_off_without_env(self):
        self.main.write_text("")
        self.assertEqual(self.run_hook({"content": GOOD}, mode="").returncode, 0)

    def test_warn_mode_never_blocks(self):
        self.main.write_text("")
        self.assertEqual(self.run_hook({"content": GOOD}, mode="warn").returncode, 0)


if __name__ == "__main__":
    unittest.main()

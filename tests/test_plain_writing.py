"""Tests for skills/plain-writing/scripts. Run: python3 -m unittest discover tests"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "skills/plain-writing/scripts/hook.py"
DASH = "—"


def run_hook(command, mode="block"):
    event = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    env = {**os.environ, "PLAIN_WRITING_HOOK": mode}
    return subprocess.run([sys.executable, str(HOOK)], input=event, capture_output=True,
                          text=True, env=env).returncode


class HookTest(unittest.TestCase):
    def test_blocks_dash_in_commit(self):
        self.assertEqual(run_hook(f'git commit -m "fix: a {DASH} b"'), 2)

    def test_allows_clean_commit(self):
        self.assertEqual(run_hook('git commit -m "fix: count the first item"'), 0)

    def test_sees_through_wrappers(self):
        self.assertEqual(run_hook(f'rtk gh pr create --title x --body "a {DASH} b"'), 2)
        self.assertEqual(run_hook('rtk proxy git commit -m "uses leverage"'), 2)
        self.assertEqual(run_hook('GIT_EDITOR=true git -C repo commit -m "in order to fix"'), 2)

    def test_ignores_git_words_inside_other_commands(self):
        script = "python3 - <<'EOF'\nprint('git commit -m \"uses leverage\"')\nEOF"
        self.assertEqual(run_hook(script), 0)
        self.assertEqual(run_hook('echo git commit -m "uses leverage"'), 0)

    def test_off_without_env(self):
        self.assertEqual(run_hook(f'git commit -m "a {DASH} b"', mode=""), 0)

    def test_warn_mode_never_blocks(self):
        self.assertEqual(run_hook(f'git commit -m "a {DASH} b"', mode="warn"), 0)


if __name__ == "__main__":
    unittest.main()

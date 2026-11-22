"""Tests for skills/root-cause/scripts. Run: python3 -m unittest discover tests"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LOOP = Path(__file__).resolve().parents[1] / "skills/root-cause/scripts/loop.py"


class LoopTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def script(self, body):
        (self.dir / "repro.py").write_text(body)

    def run_loop(self, *extra, runs=4):
        args = [sys.executable, str(LOOP), "--runs", str(runs), "--cwd", str(self.dir), "--json", *extra,
                "--", sys.executable, "repro.py"]
        r = subprocess.run(args, capture_output=True, text=True)
        return r.returncode, json.loads(r.stdout)

    def test_always_failing_with_symptom_is_tight(self):
        self.script("import sys\nprint('expected 1999, got 1998')\nsys.exit(1)\n")
        code, out = self.run_loop("--symptom", r"got 1998")
        self.assertEqual(out["verdict"], "tight")
        self.assertEqual(out["red"], 4)
        self.assertEqual(code, 0)

    def test_failure_without_symptom_is_wrong_failure(self):
        self.script("raise KeyError('total')\n")
        code, out = self.run_loop("--symptom", r"got 1998")
        self.assertEqual(out["verdict"], "wrong-failure")
        self.assertEqual(out["other_failures"], 4)
        self.assertEqual(code, 1)

    def test_passing_command_is_green(self):
        self.script("print('ok')\n")
        _, out = self.run_loop()
        self.assertEqual(out["verdict"], "green")

    def test_alternating_failure_is_flaky_with_rate(self):
        # A counter file makes every second run fail.
        self.script(
            "import pathlib, sys\n"
            "p = pathlib.Path('n')\n"
            "n = int(p.read_text()) if p.exists() else 0\n"
            "p.write_text(str(n + 1))\n"
            "sys.exit(1 if n % 2 else 0)\n"
        )
        _, out = self.run_loop()
        self.assertEqual(out["verdict"], "flaky")
        self.assertEqual(out["rate"], 0.5)

    def test_slow_loop(self):
        self.script("import sys, time\ntime.sleep(0.3)\nsys.exit(1)\n")
        _, out = self.run_loop("--fast", "0.1", runs=2)
        self.assertEqual(out["verdict"], "slow")

    def test_stop_after_red(self):
        self.script("import sys\nsys.exit(1)\n")
        _, out = self.run_loop("--stop-after-red", runs=10)
        self.assertEqual(out["runs"], 1)


if __name__ == "__main__":
    unittest.main()

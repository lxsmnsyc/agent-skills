"""Tests for skills/perf-pass/scripts. Run: python3 -m unittest discover tests"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1] / "skills/perf-pass/scripts/bench.py"


class BenchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.slow, self.fast = root / "slow", root / "fast"
        for d, value in ((self.slow, 100), (self.fast, 900)):
            d.mkdir()
            (d / "x.py").write_text(f"print('ops/sec: {value}')\n")

    def tearDown(self):
        self.tmp.cleanup()

    def run_bench(self, *dirs, extra=()):
        args = [sys.executable, str(BENCH)]
        for name, path in dirs:
            args += ["--dir", f"{name}={path}"]
        args += ["--runs", "3", "--warmup", "0", "--json", *extra, "--", sys.executable, "x.py"]
        return json.loads(subprocess.run(args, capture_output=True, text=True, check=True).stdout)

    def test_metric_higher_is_better(self):
        out = self.run_bench(("base", self.slow), ("fast", self.fast),
                             extra=("--metric", r"ops/sec: (\d+)", "--higher-is-better"))
        fast = out["rows"][1]
        self.assertEqual(fast["median"], 900)
        self.assertEqual(fast["verdict"], "better")

    def test_same_code_is_not_a_real_change(self):
        out = self.run_bench(("base", self.slow), ("again", self.slow),
                             extra=("--metric", r"ops/sec: (\d+)"))
        self.assertEqual(out["rows"][1]["verdict"], "within noise")


if __name__ == "__main__":
    unittest.main()

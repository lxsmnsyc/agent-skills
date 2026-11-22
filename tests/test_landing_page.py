"""Tests for skills/landing-page/scripts. Run: python3 -m unittest discover tests"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/landing-page/scripts/word_count.py"

PAGE = """<!DOCTYPE html>
<html><head><title>Not counted here</title><style>.a { color: red }</style></head>
<body>
<nav>Docs Blog</nav>
<main>
  <section id="hero"><h1>Only the code you click loads.</h1><img src="x.png" alt="demo"><br>
    <p>A UI framework for server-rendered apps.</p>
    <pre><code>pnpm add idlip and many more words here</code></pre>
  </section>
  <section><h2>Four words go here</h2><p hidden>Hidden text is skipped</p>
    <div aria-hidden="true">Decorative words skipped</div>
    <div class="static-steps">Step one says a lot of words</div>
  </section>
  <section id="faq"><h2>Is it free?</h2><p>Yes, MIT.</p></section>
  <script>const words = "not counted";</script>
</main>
</body></html>
"""


class WordCountTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.page = Path(self.tmp.name) / "index.html"
        self.page.write_text(PAGE)

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.page), *extra],
            capture_output=True,
            text=True,
        )

    def total_of(self, result):
        for line in result.stdout.splitlines():
            if line.endswith("total"):
                return int(line.split()[0])
        self.fail(f"no total in {result.stdout}")

    def test_counts_main_only_and_skips_code_hidden_and_scripts(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0)
        # hero 6 + 6, second section 4 + 7 static steps, faq 3 + 2
        self.assertEqual(self.total_of(result), 28)
        self.assertIn("hero", result.stdout)
        self.assertIn("section 2", result.stdout)

    def test_exclude_selectors(self):
        result = self.run_script("--exclude", "#faq", "--exclude", ".static-steps")
        self.assertEqual(self.total_of(result), 16)

    def test_budget_fails_when_over(self):
        self.assertEqual(self.run_script("--budget", "10").returncode, 1)
        self.assertEqual(self.run_script("--budget", "28").returncode, 0)


if __name__ == "__main__":
    unittest.main()

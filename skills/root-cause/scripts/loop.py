#!/usr/bin/env python3
"""Run a reproduction command many times and judge it as a feedback loop.

Usage:
  loop.py --runs 20 -- npm test -- src/cart.test.ts
  loop.py --runs 50 --symptom 'expected 1999, got 1998' -- node repro.js
  loop.py --runs 100 --cwd .git/root-cause/subtotal/base --json -- ./repro.sh

A run is red when the command exits non-zero. With --symptom, a red run also
needs the regex to match its output, so a different failure nearby does not
count as this bug. Red runs that fail without the symptom are counted apart as
"other failures".

Verdicts:
  tight          every run red with the symptom, median time under --fast seconds
  slow           every run red, but the median time is over --fast seconds
  flaky          some runs red: report the rate and raise it before debugging
  wrong-failure  runs fail, but none show the symptom
  green          no run fails: the loop does not reproduce the bug

Exits 0 when every run is red (tight or slow), 1 otherwise. After the fix the
same loop should report green.
"""
import argparse
import json
import re
import statistics
import subprocess
import sys
import time


def one_run(cmd, cwd, timeout):
    start = time.perf_counter()
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        out, code = r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        out, code = out + f"\n[loop.py] timed out after {timeout}s", 124
    return code, out, time.perf_counter() - start


def judge(results, symptom, fast):
    red = [r for r in results if r["code"] != 0 and r["symptom"]]
    other = [r for r in results if r["code"] != 0 and not r["symptom"]]
    times = [r["seconds"] for r in results]
    median = statistics.median(times) if times else 0.0
    n = len(results)
    if not red and other:
        verdict = "wrong-failure" if symptom else "flaky"
    elif not red:
        verdict = "green"
    elif len(red) < n:
        verdict = "flaky"
    elif median > fast:
        verdict = "slow"
    else:
        verdict = "tight"
    return {
        "runs": n,
        "red": len(red),
        "other_failures": len(other),
        "green": n - len(red) - len(other),
        "rate": round(len(red) / n, 3) if n else 0.0,
        "median_seconds": round(median, 3),
        "max_seconds": round(max(times), 3) if times else 0.0,
        "verdict": verdict,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--symptom", help="regex the output of a red run must match")
    ap.add_argument("--cwd", default=None, help="directory to run in (default: current)")
    ap.add_argument("--timeout", type=int, default=120, help="seconds per run; a timeout counts as a failure")
    ap.add_argument("--fast", type=float, default=10.0, help="median seconds a tight loop stays under")
    ap.add_argument("--stop-after-red", action="store_true",
                    help="stop at the first red run, to measure time to reproduce a rare bug")
    ap.add_argument("--json", action="store_true")
    argv = sys.argv[1:]
    split = argv.index("--") if "--" in argv else len(argv)
    args = ap.parse_args(argv[:split])
    cmd = argv[split + 1:]
    if not cmd:
        ap.error("give the reproduction command after --")
    if args.runs < 1:
        ap.error("--runs must be at least 1")
    pattern = re.compile(args.symptom) if args.symptom else None

    # Run the command and keep one sample output of each kind for the report.
    results, samples = [], {}
    for _ in range(args.runs):
        code, out, seconds = one_run(cmd, args.cwd, args.timeout)
        hit = bool(pattern.search(out)) if pattern else True
        results.append({"code": code, "symptom": hit, "seconds": seconds})
        kind = "red" if code != 0 and hit else ("other" if code != 0 else "green")
        samples.setdefault(kind, out.strip()[-600:])
        if args.stop_after_red and kind == "red":
            break

    summary = judge(results, args.symptom, args.fast)
    summary["command"] = cmd
    summary["samples"] = samples
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"verdict: {summary['verdict']}")
        print(f"runs {summary['runs']}: red {summary['red']}, other failures {summary['other_failures']}, "
              f"green {summary['green']} (rate {summary['rate']:.0%})")
        print(f"time: median {summary['median_seconds']}s, max {summary['max_seconds']}s")
        for kind, text in samples.items():
            print(f"--- sample {kind} output (last 600 chars) ---\n{text}")
    return 0 if summary["verdict"] in ("tight", "slow") else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Run the same benchmark in several checkouts and compare them fairly.

Usage:
  bench.py --dir base=../repo.base --dir a=.worktrees/perf-a --dir b=.worktrees/perf-b \\
           --runs 10 --warmup 2 -- node bench/render.js
  bench.py ... --metric 'ops/sec: ([\\d.]+)' --higher-is-better -- npm run bench

Runs are interleaved (base, a, b, base, a, b, ...) so drift in machine load
hits every side equally. Without --metric the wall time of each run is
measured; with --metric the first capture group of the regex is read from the
command's output.

Prints median, mean, spread and the change against the first --dir, and marks
a change as real only when it is larger than the noise (the larger of the two
sides' median absolute deviations, times 3).
"""
import argparse
import json
import re
import statistics
import subprocess
import sys
import time


def one_run(cmd, cwd, metric, timeout):
    start = time.perf_counter()
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    elapsed = time.perf_counter() - start
    if r.returncode != 0:
        raise RuntimeError(f"{cwd}: exit {r.returncode}: {(r.stdout + r.stderr).strip()[-400:]}")
    if not metric:
        return elapsed
    m = re.search(metric, r.stdout + r.stderr)
    if not m:
        raise RuntimeError(f"{cwd}: metric {metric!r} not found in output")
    return float(m.group(1).replace(",", ""))


def mad(xs):
    med = statistics.median(xs)
    return statistics.median([abs(x - med) for x in xs])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", action="append", required=True, help="name=path; the first is the baseline")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--metric", help="regex with one group, read from the output instead of wall time")
    ap.add_argument("--higher-is-better", action="store_true")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--json", action="store_true")
    argv = sys.argv[1:]
    split = argv.index("--") if "--" in argv else len(argv)
    args = ap.parse_args(argv[:split])
    cmd = argv[split + 1:]
    if not cmd:
        ap.error("give the benchmark command after --")
    sides = [d.split("=", 1) if "=" in d else (d, d) for d in args.dir]

    samples = {name: [] for name, _ in sides}
    try:
        for i in range(args.warmup + args.runs):
            for name, path in sides:
                value = one_run(cmd, path, args.metric, args.timeout)
                if i >= args.warmup:
                    samples[name].append(value)
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        sys.exit(str(e))

    unit = "value" if args.metric else "seconds"
    base_name = sides[0][0]
    base = samples[base_name]
    rows = []
    for name, _ in sides:
        xs = samples[name]
        row = {"name": name, "median": statistics.median(xs), "mean": statistics.mean(xs),
               "min": min(xs), "max": max(xs), "mad": mad(xs), "runs": len(xs)}
        if name != base_name:
            delta = row["median"] - statistics.median(base)
            noise = 3 * max(mad(xs), mad(base))
            better = delta > 0 if args.higher_is_better else delta < 0
            row["change_pct"] = 100 * delta / statistics.median(base)
            row["real"] = abs(delta) > noise
            row["verdict"] = ("better" if better else "worse") if row["real"] else "within noise"
        rows.append(row)

    if args.json:
        print(json.dumps({"unit": unit, "command": " ".join(cmd), "rows": rows}, indent=2))
        return
    print(f"{' '.join(cmd)}  ({args.runs} runs each, {args.warmup} warmup, unit: {unit})")
    for r in rows:
        line = f"  {r['name']:<12} median {r['median']:.4g}  min {r['min']:.4g}  max {r['max']:.4g}  mad {r['mad']:.3g}"
        if "change_pct" in r:
            line += f"  {r['change_pct']:+.1f}% vs {base_name}: {r['verdict']}"
        print(line)


if __name__ == "__main__":
    main()

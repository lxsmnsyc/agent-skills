#!/usr/bin/env python3
"""Compare the size of build output between base and head.

Usage:
  size_diff.py <base-dir> <head-dir> [--glob 'dist/**/*.js']

Prints raw and gzip sizes for each file that changed, and the totals, so the
review can state the cost in bytes instead of "a bit bigger".
"""
import argparse
import gzip
from pathlib import Path


def sizes(root, pattern):
    out = {}
    for p in Path(root).glob(pattern):
        if p.is_file():
            data = p.read_bytes()
            out[str(p.relative_to(root))] = (len(data), len(gzip.compress(data, 9)))
    return out


def fmt(n):
    return f"{n / 1024:.1f}kB" if abs(n) >= 1024 else f"{n}B"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base")
    ap.add_argument("head")
    ap.add_argument("--glob", default="dist/**/*.*")
    args = ap.parse_args()
    a, b = sizes(args.base, args.glob), sizes(args.head, args.glob)
    if not a and not b:
        raise SystemExit(f"no files match {args.glob}; build both sides first")
    total = [0, 0, 0, 0]
    for f in sorted(set(a) | set(b)):
        ra, ga = a.get(f, (0, 0))
        rb, gb = b.get(f, (0, 0))
        total = [total[0] + ra, total[1] + ga, total[2] + rb, total[3] + gb]
        if (ra, ga) != (rb, gb):
            print(f"{f}: {fmt(ra)} -> {fmt(rb)} ({fmt(rb - ra):>8}), gzip {fmt(ga)} -> {fmt(gb)} ({fmt(gb - ga)})")
    print(f"total: {fmt(total[0])} -> {fmt(total[2])} ({fmt(total[2] - total[0])}), "
          f"gzip {fmt(total[1])} -> {fmt(total[3])} ({fmt(total[3] - total[1])})")


if __name__ == "__main__":
    main()

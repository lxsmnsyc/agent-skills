#!/usr/bin/env python3
"""Estimate how many worktrees (and agents working in them) this machine can take now.

Usage:
  capacity.py [--per-worktree-mb 1500] [--json]

Looks at free memory, CPU load, free disk and the worktrees that already exist,
and recommends a number of parallel worktrees with the reason for the limit.
A result of 1 means: work in one checkout, one task at a time.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys


def free_memory_mb():
    if sys.platform == "darwin":
        try:
            out = subprocess.run(["memory_pressure", "-Q"], capture_output=True, text=True,
                                 timeout=10).stdout
            pct = int(re.search(r"free percentage:\s*(\d+)%", out).group(1))
            total = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True,
                                       text=True).stdout) // (1024 * 1024)
            return total * pct // 100, total
        except (OSError, AttributeError, ValueError, subprocess.TimeoutExpired):
            return None, None
    try:
        info = dict(re.findall(r"(\w+):\s+(\d+) kB", open("/proc/meminfo").read()))
        return int(info["MemAvailable"]) // 1024, int(info["MemTotal"]) // 1024
    except (OSError, KeyError):
        return None, None


def worktree_count():
    try:
        out = subprocess.run(["git", "worktree", "list"], capture_output=True, text=True).stdout
        return max(0, len(out.splitlines()) - 1)
    except OSError:
        return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-worktree-mb", type=int, default=1500,
                    help="memory one agent plus its tests and dev server need (default 1500)")
    ap.add_argument("--per-worktree-disk-mb", type=int, default=1000)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cores = os.cpu_count() or 1
    load1 = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0
    free_mb, total_mb = free_memory_mb()
    disk_free_mb = shutil.disk_usage(".").free // (1024 * 1024)
    existing = worktree_count()

    limits = {
        # Leave half the cores for the user and the agents' own processes.
        "cpu": max(1, int((cores - load1) // 2)),
        "disk": max(1, disk_free_mb // args.per_worktree_disk_mb - 2),
    }
    if free_mb is not None:
        # Keep 2 GB free for the system and the user.
        limits["memory"] = max(1, (free_mb - 2048) // args.per_worktree_mb)
    limit_by = min(limits, key=limits.get)
    recommended = max(1, min(limits.values()) - existing)

    out = {
        "recommended_parallel": recommended,
        "limited_by": limit_by,
        "limits": limits,
        "cores": cores, "load_1m": round(load1, 2),
        "free_memory_mb": free_mb, "total_memory_mb": total_mb,
        "free_disk_mb": disk_free_mb,
        "existing_worktrees": existing,
        "use_worktrees": recommended > 1 or existing == 0,
    }
    if args.json:
        print(json.dumps(out, indent=2))
        return
    print(f"recommended parallel worktrees: {recommended} (limited by {limit_by})")
    print(f"cpu: {cores} cores, load {load1:.1f} -> {limits['cpu']}")
    if free_mb is not None:
        print(f"memory: {free_mb} MB free of {total_mb} MB -> {limits['memory']}")
    print(f"disk: {disk_free_mb} MB free -> {limits['disk']}")
    print(f"existing worktrees: {existing}")


if __name__ == "__main__":
    main()

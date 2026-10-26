---
name: perf-pass
description: Profile the finished version of a feature and make it faster or smaller with measured evidence. Measures a baseline, finds where the time or the bytes go, proposes several candidate optimizations, tries the promising ones side by side, and picks the one with the best gain for its cost. Runtime speed and memory for libraries, engines, servers and tools; bundle size and load cost for web apps. Use this skill when a feature is functionally done and before its PR is opened, when the user asks to profile, optimize, speed up, shrink or benchmark something, or when a change touches a hot path or the shipped bundle, even if they do not say "performance".
---

# Perf pass

A feature that works is the right moment to make it fast or small: the behavior is pinned down by tests, and the code is still fresh. This skill turns "make it faster" into a short, measured search. Every claim gets a number, every option gets tried against the same harness, and the result is the option with the best gain for its cost, not the first idea that helped.

## When to run it

- A feature is done and its tests pass, and it touches code that runs often (render loops, request handlers, parsers, compilers, game ticks, startup) or adds to what a browser downloads.
- The user asks to profile, optimize, speed up, shrink or benchmark.
- The pr-author skill reaches its checks for such a feature. Do the pass before the PR is opened, so the PR ships the tuned version and the numbers go in its Cost section.

Skip it for changes with no measurable cost (docs, config, one-off scripts), and say so.

## Scripts

```bash
python3 <skill>/scripts/bench.py --dir base=<path> --dir a=<path> [--dir b=<path>] \
    --runs 10 --warmup 2 [--metric '<regex>' --higher-is-better] -- <command>
python3 <skills>/pr-review/scripts/size_diff.py <base> <candidate> --glob 'dist/**/*.js'
```

`bench.py` interleaves runs across checkouts so machine load hits every side equally, and marks a change as real only when it is larger than the noise. Use pr-author's `wt.py` (or plain `git worktree`) to give each candidate its own checkout.

## Steps

### 1. Pick the axis

- **Runtime**: time per operation, throughput, latency, frame time, memory, allocations. The default for libraries, engines, servers, CLIs and tools.
- **Size**: bytes the user downloads (gzip or brotli), number of requests, time until the page is usable. The default for web apps and for libraries that end up in someone's bundle.
- Often both. Name the main one, and treat the other as a constraint that must not get worse.

Ask the user only when the axis is unclear and it changes the answer.

### 2. Build the harness and the baseline

Measure before changing anything. Use what the repo has first: `bench/`, `vitest bench`, `cargo bench`, `go test -bench`, `pytest-benchmark`, a size-limit config. If there is nothing, write the smallest benchmark that runs the feature on realistic input: realistic size and shape, not a toy. Keep it in the repo if the repo has a place for benchmarks, so the next change can be measured too.

Record the baseline with `bench.py` (runtime) or a production build plus `size_diff.py` (size). Note the machine and the command. See `references/measuring.md` for tools per stack.

### 3. Find where the cost is

Profile; do not guess. A CPU profile, an allocation profile, or a bundle analysis shows where the time or the bytes go. Write down the top three or four costs with their share. Optimizing something that is 2% of the total cannot give more than 2%.

### 4. Propose several options

For the top costs, write at least three candidate changes, from different kinds of fix (see `references/strategies.md`): a better algorithm, less work, less allocation, batching, caching, laziness, a lighter dependency, a build setting. For each, write:

- what changes, and where
- the expected gain, and why (from the profile)
- the cost: added complexity, size, memory, risk, maintenance
- what could make it not work

Drop the ones whose best case is too small to matter, or whose cost is clearly too high. Keep two to four to try.

### 5. Try them side by side

Build each remaining option in its own worktree from the same base. Run the tests in each; an option that breaks behavior is out. Then measure all of them in one `bench.py` run against the baseline, or one `size_diff.py` per option against the same base build. When two options are independent and both help, also try them combined.

### 6. Choose the ideal

Pick by gain for its cost, not by gain alone:

- A change "within noise" is not a gain. Drop it, even if it looks clever.
- A small gain that adds a cache, a new dependency or a second code path is usually not worth it.
- Prefer the simplest option that gets most of the best option's gain.
- Check the constraint axis did not get worse (a faster version that ships 20 kB more is a trade, and the user should hear it).

Apply the chosen option on the feature branch, rerun the tests and the benchmark, and confirm the numbers hold.

### 7. Record it

Report a table, and put the same numbers in the PR's Cost section:

```
Axis: runtime (render 1,000 rows), constraint: bundle size
Baseline: 41.2 ms median (10 runs)

| Option                         | Result   | Change  | Cost                     | Verdict        |
| ------------------------------ | -------- | ------- | ------------------------ | -------------- |
| A: keyed reuse of row nodes    | 27.9 ms  | -32%    | +40 lines, no new deps   | chosen         |
| B: memoize cell formatting     | 39.8 ms  | -3%     | cache invalidation logic | within noise   |
| C: virtualize the list         | 6.1 ms   | -85%    | +9 kB gzip, new dep      | rejected: size |
| A + B                          | 27.5 ms  | -33%    | both                     | B adds nothing |
Bundle: +0.3 kB gzip with A
```

Rejected options are worth keeping. Write the measured ones into the PR description and, when the repo keeps decision records or a nested `CLAUDE.md` near the code, one line there ("virtualizing the row list was measured at +9 kB gzip for -85% render time; rejected for size"), so nobody tries them again without new information.

## Rules

- Never trade correctness for speed. The tests pass on every option that is measured.
- Never claim a gain without the command that shows it.
- One harness and one machine for all options in a comparison. Close other heavy work while measuring; parallel agents on the same machine add noise, so run benchmarks one at a time.
- Keep the benchmark input realistic. A gain that only shows on a toy input is not a gain.

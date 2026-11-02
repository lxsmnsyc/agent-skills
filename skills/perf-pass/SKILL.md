---
name: perf-pass
description: Profile the finished version of a feature and make it faster or smaller with measured evidence. Measures a baseline, analyzes the implementation's contract (inputs and outputs) and then its structure, designs a simpler and faster solution alongside targeted fixes, tries them side by side, and picks the fastest option that meets the size goal, preferring the simplest structure. Runtime speed and memory for libraries, engines, servers and tools; bundle size and load cost for web apps. Use this skill when a feature is functionally done and before its PR is opened, when the user asks to profile, optimize, speed up, shrink or benchmark something, or when a change touches a hot path or the shipped bundle, even if they do not say "performance".
---

# Perf pass

A feature that works is the right moment to make it fast or small: the behavior is pinned down by tests, and the code is still fresh. This skill turns "make it faster" into a short, measured search. Known practices (`references/principles.md`, plus a file per language) are applied without a proof of their own, so measuring goes to the choices that trade one cost for another. It first pins down what the code must do, then how it does it, and looks for a simpler structure that does the same with less work. Every claim gets a number, every option gets tried against the same harness, and the result is the fastest option that meets the size goal, with the simplest structure among equals, not the first idea that helped.

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

### 1. Set the goals

- **Speed is the priority**: time per operation, throughput, latency, frame time, memory, allocations, or for web apps the time until the page is usable. This is the number the pass exists to improve.
- **Size is a goal to meet, not a veto**: bytes the user downloads (gzip or brotli) for web apps and for libraries that end up in someone's bundle. The goal is the repo's own budget (size-limit, a performance budget) when it has one. Otherwise it is the baseline size: the result ships no more bytes than today. Bytes in a lazy chunk count for less than bytes in the initial load. Code that never ships to a browser (servers, CLIs, engines) has no size goal unless install size or cold start is the point of the change.

The two rarely conflict when the fix is structural. A simpler structure does less work and has less code, so it tends to be both faster and smaller. That is why steps 3 to 5 look for a simpler structure before they look for local tweaks.

Ask the user only when the speed metric is unclear and it changes the answer.

### 2. Build the harness and the baseline

Measure before changing anything. Use what the repo has first: `bench/`, `vitest bench`, `cargo bench`, `go test -bench`, `pytest-benchmark`, a size-limit config. If there is nothing, write the smallest benchmark that runs the feature on realistic input: realistic size and shape, not a toy. Keep it in the repo if the repo has a place for benchmarks, so the next change can be measured too.

Record the baseline with `bench.py` (speed) and, when there is a size goal, a production build plus `size_diff.py`. Note the machine and the command. Then profile: a CPU profile, an allocation profile, or a bundle analysis. Write down the top three or four costs with their share. See `references/measuring.md` for tools per stack.

### 3. Analyze the contract

Before reading how the code works, pin down what it must do. Write it in a few lines:

- **Inputs**: their shape, size and distribution in real use (how many items, how many distinct keys, sorted or not, how often it is called, with what repeating).
- **Outputs**: what callers read. Grep the call sites. Output that no caller reads, precision nobody needs, and ordering nobody relies on are all slack.
- **Invariants and edge cases**: what the tests pin down (ties, empty input, stable order), and what they leave free.

The contract is the yardstick for every option. An option is valid if it keeps the contract and passes the tests, however different its insides are.

### 4. Analyze the structure

Now describe how the current code meets that contract: its stages and passes over the data, the intermediate data it builds (copies, arrays, maps, strings), its layers and abstractions, its dependencies. Map each top cost from the profile to the stage that causes it.

Then compare the structure to the contract. Look for:

- work done for output the contract does not need (computing every row when the caller takes ten)
- repeated passes that one pass could replace (a filter per key instead of one grouping pass)
- intermediate data that exists only to be read once (clones, temporary arrays, serialized round trips)
- the wrong data structure for the access pattern (a list searched by key)
- layers or dependencies that do little for what they cost

Also check the code against `references/principles.md` and the language file it names (`references/principles-js-ts.md` for `.js` and `.ts`). Note each principle it breaks, with its id and the line. A language with no file yet gets the general principles only.

### 5. Design a simpler, faster solution

Design the simplest structure that turns the contract's inputs into its outputs: the fewest stages, passes and intermediate structures, the right data structure for each access. Write it from the contract, not as edits to the current code, and follow every principle that applies, from the general file and the language file. This is option A, the structural rewrite.

A change that only applies a listed principle is not a candidate to compare. It goes into option A, or into the current code when A keeps its structure, and cites the principle id.

Then write the candidates that a principle cannot settle (see "When a principle is not enough" in `references/principles.md`, and `references/strategies.md`): caches, workers, laziness, splitting, bit packing, a dependency swap, engine-specific tricks. For each option, write:

- what changes, and where
- its structure: stages, lines, dependencies, compared with the baseline
- the expected speed gain, and why (from the profile)
- its expected effect on size
- what could make it not work

Drop the ones whose best case is too small to matter. Keep up to three to try. When every change is principle-backed, there is nothing to try side by side: go to step 7 with option A alone.

### 6. Try them side by side

Only the candidates from step 5 that a principle cannot settle are tried here. Build each option in its own worktree from the same base. Run the tests in each. An option that breaks behavior is out. Measure all of them in one `bench.py` run against the baseline, and when there is a size goal, one `size_diff.py` per option against the same base build. When two options are independent and both help, also try them combined.

### 7. Choose

Rank in this order:

1. **Correct**: the tests pass and the contract holds.
2. **Faster**: the speed gain is real, beyond the noise. A change within noise is not a gain.
3. **Meets the size goal**.
4. **Simplest structure**: among options whose speed is close to the best (within about 10%, or within noise), pick the one with the fewest stages, lines and dependencies.

A faster option that misses the size goal is not dropped right away. First look for a simpler form of it that keeps the gain and meets the goal, for example by dropping a dependency for a few lines of code or splitting the heavy part into a lazy chunk. If none exists, report the trade to the user with both numbers and let them pick.

Apply the chosen option on the feature branch, rerun the tests, and measure it once against the baseline with the same harness (`bench.py`, and `size_diff.py` when there is a size goal). This one run covers the principle-backed changes too. If it shows no real gain, the principles were applied off the hot path: keep the change when it is simpler or smaller, and do not claim a speed gain.

### 8. Record it

Report a table, and put the same numbers in the PR's Cost section:

```
Speed: render 1,000 rows. Size goal: no larger than baseline (48.2 kB gzip initial)
Contract: rows in, DOM out; callers read only the visible rows
Baseline: 41.2 ms median (10 runs), 3 passes over the rows

| Option                             | Speed    | Change | Size      | Structure               | Verdict              |
| ---------------------------------- | -------- | ------ | --------- | ----------------------- | -------------------- |
| A: one pass, render visible rows (W3, D2, D4) | 5.8 ms | -86% | -1.1 kB | 1 pass, -60 lines | chosen       |
| B: virtualize with a library       | 6.1 ms   | -85%   | +9 kB     | 3 passes, new dep       | misses size goal; A matches it |
| C: memoize cell formatting         | 39.8 ms  | -3%    | +0.4 kB   | cache invalidation      | within noise         |
```

Rejected options are worth keeping. Write the measured ones into the PR description and, when the repo keeps decision records or a nested `CLAUDE.md` near the code, one line there ("virtualizing the row list with a library was measured at -85% render time for +9 kB gzip; a one-pass render of visible rows got the same speed for -1.1 kB"), so nobody tries them again without new information.

## Rules

- Never trade correctness for speed. The tests pass on every option that is measured.
- Never claim a gain without the command that shows it. A principle-backed change needs no proof of its own, but the final result is measured once against the baseline.
- One harness and one machine for all options in a comparison. Close other heavy work while measuring; parallel agents on the same machine add noise, so run benchmarks one at a time.
- Keep the benchmark input realistic. A gain that only shows on a toy input is not a gain.
- Speed comes first, the size goal must be met, and among options that do both the simplest structure wins. A size change below the goal never rejects a real speed gain.

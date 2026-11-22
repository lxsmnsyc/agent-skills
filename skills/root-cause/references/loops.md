# Feedback loops

A loop is one command that goes red on this bug and green once it is fixed. This file lists the kinds, in roughly the order to try them, and how to make one tight.

## Contents

- Kinds of loop
- Making it tight
- Flaky bugs
- Slowdowns
- Checking the loop with loop.py

## Kinds of loop

1. **Failing test** at the seam that reaches the bug: unit, integration or e2e. Cheapest to keep, and it becomes the regression test.
2. **HTTP script** against a running dev server. Derive the port from the worktree index (`3000 + 10 * index`) so parallel probes do not collide.
3. **CLI run** with a fixture input, its output diffed against known-good output.
4. **Browser script** (Playwright) that drives the page and asserts on the DOM, the console or the network.
5. **Replayed trace.** Save a real request, payload or event log to `.git/root-cause/<slug>/` and replay it through the code path alone. Redact auth headers first.
6. **Throwaway harness.** The smallest part of the system that reaches the bug: one module, faked dependencies, one function call.
7. **Property loop.** For "sometimes wrong output", generate inputs (fast-check in TypeScript repos) and compare against an exact computation or a reference implementation. The smallest failing input it finds becomes the regression test, and a fixed seed for the repo's property tests.
8. **Bisection.** When the bug appeared between two known states, write the loop as a script that exits 0 on good and 1 on bad, then `git bisect start <bad> <good>` and `git bisect run <script>` in a worktree. Exit 125 skips commits that do not build.
9. **Differential run.** Run the same input through two versions or two configs (`worktrees.py prepare --base <good> --head <bad>`) and diff the outputs. `repro.py` does this for a test file.
10. **Human in the loop.** Last resort, when a person must click or look. Write a short script that prints one step at a time, waits for the person, and records what they report, so the loop still has a fixed shape. Ask the user first.

## Making it tight

Treat the loop as a product. Once one works:

- **Faster**: cache setup, skip unrelated startup, run one test file instead of the suite.
- **Sharper**: assert the exact symptom, not "it did not crash". `--symptom` in `loop.py` enforces this.
- **Deterministic**: pin the time, seed random numbers, use a fresh temporary directory, fake the network.

A 30-second loop that fails 1 run in 3 barely helps. A 2-second loop that fails every run finds the cause quickly.

## Flaky bugs

The goal is a higher reproduction rate, not a clean one.

- Run the trigger many times in one process instead of starting the process each time.
- Add load: run several copies at once, or limit CPU (`taskset`, a container CPU limit).
- Narrow the window: add a sleep at the suspected point to widen a race, then remove it.
- Record the seed, order and timing of each red run, so a red run can be replayed.

Measure the rate with `loop.py --runs 100`. Raise it until it is at least 50% before probing. Below that, a probe that turns the loop green may only be luck.

## Slowdowns

Logs do not locate a slowdown. Measure:

1. Baseline on the good state and the bad state with `bench.py`, interleaved, at least 10 runs each.
2. Accept the slowdown as real only when bench.py marks it beyond the noise.
3. Profile the bad state (`--cpu-prof` for Node, `py-spy`, the browser performance panel) and find where the extra time goes.
4. Bisect with a script that exits 1 when the benchmark is over a threshold set halfway between the two medians.

## Checking the loop with loop.py

```bash
python3 <skill>/scripts/loop.py --runs 20 --symptom 'expected 1999, got 1998' -- python3 repro.py
```

- `tight`: every run red with the symptom, median under 10 seconds (`--fast` to change).
- `slow`: every run red, but too slow to iterate on.
- `flaky`: a rate between 0 and 1. Raise it.
- `wrong-failure`: runs fail without the symptom. The loop catches another bug.
- `green`: no run fails.

`--stop-after-red` measures how long a rare bug takes to appear. After the fix, the same command must report `green`.

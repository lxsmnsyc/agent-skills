---
name: root-cause
description: Find and prove the cause of a bug, flake or slowdown before anyone fixes it. Builds a tight pass/fail loop that shows the reported symptom, shrinks it to a minimal reproduction, tests 3 to 5 ranked hypotheses that can each be proven false (in parallel worktrees when probes are slow), and ends with a diagnosis, meaning the cause at file and line, the failing test, fix options with their cost and risk, and where the work goes next (a pr-author fix PR, a roadmap fix node, an issue, or security-fix). Works alone or as a parallel-roadmap `diagnose` node. Use this skill whenever the user reports something broken, throwing, failing, flaky, wrong or slow, says "debug" or "why does", when a roadmap worker or pr-review reports "not reproduced" but the symptom stands, or when pr-author finds a bug whose cause is unclear, even if they do not say "root cause".
---

# Root cause

A fix is only as good as its cause. This skill finds the cause with evidence and hands a fix-ready diagnosis to whatever ships the fix. It does not fix anything itself, except for the regression test it leaves ready.

The whole method rests on one thing: a command that goes red on this bug. With one, bisection, hypotheses and probes are mechanical. Without one, reading code produces guesses. So most of the effort goes into step 2.

## Inputs

- **A symptom from the user**: an error, a wrong output, a flake, a slow path. Quote it exactly.
- **A roadmap `diagnose` node**: the brief's Goal holds the symptom and its Evidence line holds what is known. The diagnosis goes in the node's `outcome.md`.
- **A "not reproduced" result** from a roadmap worker or from pr-review, while the user or the report still shows the symptom.
- **pr-author's "cause unclear"**: a bug found on the base with no clear cause.

## Scripts

```bash
python3 <skill>/scripts/loop.py --runs 20 --symptom '<regex>' [--cwd <dir>] -- <command>   # tight, slow, flaky, wrong-failure or green
python3 <skills>/pr-review/scripts/repro.py <base> <head> --copy <test> -- <command>      # fails on base, passes on head?
python3 <skills>/pr-review/scripts/worktrees.py prepare --base <ref> --head <ref>        # two checkouts side by side
python3 <skills>/perf-pass/scripts/bench.py --dir base=<path> --dir a=<path> -- <command> # slow paths: a cost beyond the noise
python3 <skills>/pr-author/scripts/wt.py new <branch> --base <ref>                        # one worktree per probe
```

## Rules

- Work in worktrees, never in the user's checkout. Never run `git stash`: every worktree shares one stash list.
- Keep scratch files in `.git/root-cause/<slug>/` (the diagnosis, the reproduction, captured traces). Git never commits that folder, so nothing leaks by accident. In a roadmap node, the diagnosis goes in `outcome.md` and the reproduction in `nodes/<id>/repro/` instead.
- Redact secrets in every command, output and artifact you show. Write `<REDACTED>`. Build loops on environment variables so credentials stay out of what you show.
- **A vulnerability stops the run.** Write nothing about it to the repo, an issue, a PR, a roadmap file or an inbox. Report it only to the user (or the orchestrator, as a subagent) and hand it to the security-fix skill.
- **Budget.** Use the cap the user or the brief gives. Without one, stop after five loop approaches that fail, or two rounds of hypotheses that are all ruled out. Report what you tried instead of guessing.

## Steps

### 1. Pin the symptom

Write down the exact symptom: the error text, the wrong value next to the right one, the timing, the rate of a flake. Note where it was seen: commit, version, environment, input. A report is a lead. The code may have moved since.

"A cent too low" and "a missing item" are different bugs. Every later step checks against this exact symptom, so a different failure nearby is not mistaken for it.

### 2. Build the loop

Read `references/loops.md` for the kinds of loop and how to choose. In short, start with a failing test at the seam that reaches the bug. Then try a script against a running server, a CLI run diffed against known-good output, or a browser script. Later options are a replayed trace, a throwaway harness, a property loop, a bisection and a differential run.

Run each candidate through `loop.py` with `--symptom`:

- **tight**: red on every run, fast. Go on.
- **slow**: make it faster first. Cache setup, cut unrelated startup, narrow the test.
- **flaky**: raise the rate before debugging. Loop the trigger, add load, narrow timing windows. A 50% rate is debuggable and a 1% rate is not.
- **wrong-failure**: it fails for another reason. Fix the loop, not the code.
- **green**: it does not reproduce. Look for the input that does (step 2b).

For a slowdown, the loop is a benchmark: `bench.py` on the good and bad commits, with the cost beyond the noise. Logs do not find slowdowns. Measurements do.

**2b. When nothing reproduces.** The report is usually true and the loop uses the wrong input. Match the symptom: rounding errors point to floating point, ordering errors point to unstable sorts or races. Loop over a range of inputs against an exact computation, try boundaries (0, 1, empty, halves, the largest values), and try the inputs named in the report. If it still does not show after the budget, stop. Ask for access to the environment that shows it, a captured artifact (log, HAR file, core dump, recording with timestamps), or permission to add temporary instrumentation. Do not hypothesize without a loop.

Step 2 is done when you can name one command, already run, with its output shown, that `loop.py` calls tight (or flaky at a fixed, high rate).

### 3. Shrink it

Cut inputs, callers, config, data and steps one at a time, and rerun the loop after each cut. Keep only what the failure needs. Done when removing any remaining part turns the loop green. The minimal reproduction narrows the hypotheses and becomes the regression test.

When the bug appeared between two known states (two commits, two versions, two datasets), run `git bisect run` with the loop in a worktree. A first bad commit often names the cause outright.

### 4. Rank hypotheses

Write 3 to 5 hypotheses before testing any. One hypothesis anchors on the first idea that fits. Each one states its prediction:

> If <X> is the cause, then <changing Y> makes the loop green, and <changing Z> makes it worse.

A hypothesis with no prediction is a guess: sharpen it or drop it. Rank by likelihood and by how cheap the probe is.

Show the ranked list to the user before probing, or to the orchestrator as a roadmap worker. They often know which one changed last week, or which they already ruled out. Do not block on it: proceed with your ranking if no answer comes.

### 5. Probe

Each probe tests one prediction and changes one variable.

- Prefer a debugger or REPL breakpoint over logs.
- Put logs at the boundaries that tell hypotheses apart. Never log everything and grep.
- Tag every temporary log with one prefix per run, such as `[RC-a4f2]`, so one grep removes them all.

**Parallel probes.** When three or more hypotheses are left, they touch different code, and each probe takes minutes (a build, a long suite, a bisection), test them at once. Give each its own worktree with `wt.py new` and one agent, and send each agent only its hypothesis, the loop command and the prediction. Cheap probes run one after another: an agent that loads the repo costs more than a short probe. A roadmap worker is a subagent and cannot spawn agents, so it probes one at a time.

When every hypothesis is ruled out, write a new round from what the probes showed. After two rounds, stop and report (see Budget).

### 6. Confirm the cause

A cause is confirmed when three things hold. Changing it turns the loop green. Putting it back turns the loop red. It explains the exact symptom from step 1. Then:

- **Cause, not symptom.** Name the file, line and commit of the flaw. Search the other callers of that code and similar code for the same flaw.
- **The seam.** Find where a regression test reproduces the real pattern, as it happens at the call site. Turn the minimal reproduction into a test there. In a roadmap node it stays in `nodes/<id>/repro/` until the fix node moves it into the suite. A failing test in the suite would break every check. Sometimes no seam reaches the real pattern, for example when a unit test cannot rebuild the chain of callers that triggers it. That is a finding: the architecture prevents locking this bug down.

### 7. Weigh the fix options

Write each realistic fix as an option. For each one give:

- **Change**: where and what, in one sentence.
- **Reach**: the callers, users or data the change touches. Count the call sites. Name the public API, file formats or stored data it changes.
- **Cost**: speed and size on a hot path, measured with `bench.py` or `size_diff.py` when the changed code runs often or ships to a browser. A fix that trades speed or bytes for correctness says so with numbers.
- **Undo**: can it be reverted alone, or does it change stored data, a format or a public API? Can it be tuned later (one constant, one flag) without another rewrite?

Recommend the option that fixes the cause at the smallest reach and cost. A workaround (a rounding step, a tolerance, a retry, a sleep, a special case for the reported input) is never the recommendation. List it only to say why not.

### 8. Write the diagnosis and route it

Fill in `templates/diagnosis.md`. Its Evidence part matches the Evidence line of a roadmap brief, so a fix node needs no new research.

| Verdict | Where it goes |
| --- | --- |
| `fix-small`: clear cause, small fix | pr-author: a fix PR with the regression test, against the branch the policy gives for a fix |
| `fix-large`: clear cause, large or risky fix | A roadmap fix node with a `hard` dependency on the diagnose node, or an issue when no roadmap runs, written with the issue-author skill. Ask the user before opening an issue. |
| `no-seam`: no test can reach the real pattern | The fix as above, plus a refactor node or inbox entry for the seam |
| `vulnerability`: reported, nothing written | security-fix, through the user only |
| `no-loop`: nothing reproduces within the budget | The user, with what was tried and what to send |
| `not-a-bug`: the code does what it should | The user, with the evidence. The report becomes a docs or feature question. |

### 9. Clean up

- Remove every temporary log: grep for the run's tag and expect no match.
- Remove probe worktrees with `wt.py remove`. Keep `.git/root-cause/<slug>/` until the fix merges.
- Rerun the loop on the fix branch when it exists. It must be green, and the regression test must pass.
- The fix's commit or PR names the confirmed hypothesis, so the next person learns from it.

## What the user sees

```
Symptom: cart subtotal is 1 cent low for 3 x $6.665 ("expected 1999, got 1998")
Loop: python3 .git/root-cause/subtotal/repro.py, tight (20/20 red, 0.4s)
Minimal: one line item, price 6.665, quantity 3
Hypotheses: 4 ranked, 3 ruled out; confirmed: float multiply before rounding (src/cart.ts:42, since a1b2c3d)
Seam: src/cart.test.ts, test ready
Options: integer cents (recommended: 3 call sites, no speed change, reverts alone) | round per line (changes totals users have seen)
Verdict: fix-small, next step pr-author fix/subtotal-cents -> main
Cleanup: 0 [RC-a4f2] logs left, probe worktrees removed
```

Write the diagnosis and all reports by the plain-writing rules if that skill is installed.

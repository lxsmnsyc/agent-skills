# Risk

Risk is how much breaks if the change is wrong, and how hard it is to take back. It is separate from size: a one-line change to a rounding function used by every checkout is small and high risk.

Rate it twice. A roadmap brief estimates it before the work (`risk:` in the brief, from the plan). The author measures it on the built change, before the self-review. The higher of the two decides the review and the merge.

## Contents

- The four questions
- The rating
- Measuring with risk.py
- The Risk block in the PR
- What the rating changes

## The four questions

| Question | Low | Medium | High |
| --- | --- | --- | --- |
| **Reach**: who and what runs the changed code? | its own module, 0 to 4 caller files | 5 to 19 caller files, or one exported name outside an entry file | 20+ caller files, an entry-file export, or a path every user runs (startup, request handling, checkout) |
| **Undo**: can it be taken back? | revert the commit and nothing else changes | revert needs a follow-up (a config, a cache, a dependency bump) | changes stored data, a file or wire format, or a public API that users may already rely on |
| **Trade**: does it pay speed, memory or bytes for correctness? | no measurable cost, or not on a hot path | a cost beyond the noise, under 5% on the path it touches | a cost of 5% or more on a hot path or the initial bundle |
| **Coverage**: will a wrong change fail a check? | tests exercise the changed lines and the new behavior | tests reach the file, not the changed branch | no test runs the changed code |

Measure the trade, do not guess it. For a change on code that runs often (render loops, request handlers, parsers, startup) or that ships to a browser, run perf-pass's `bench.py` on the base and the branch, or pr-review's `size_diff.py`. A fix counts too: a guard, a copy or a lock added for correctness is a trade.

**Tuning** is part of undo. A change whose behavior sits in one constant, one option or one flag can be adjusted later without a rewrite, which lowers its undo cost. Say so when it is true.

## The rating

- **high**: any question is high.
- **medium**: no high, and any question is medium.
- **low**: every question is low.

Security code (auth, input parsing at a trust boundary, crypto, permissions) and concurrency code (locks, shared state, ordering) are at least medium whatever the counts say.

## Measuring with risk.py

```bash
python3 <skill>/scripts/risk.py --base <base> [--head <branch>] [--json]
```

It reads the diff and the head tree and reports facts: changed symbols and the files that use them, exports and whether they sit in an entry file, changed migrations or schemas, changed manifests or lockfiles, changed source files no test names, and the line count. Its suggested rating covers reach, part of undo and part of coverage. It cannot see the trade, hot paths, security or concurrency. Raise the rating for those. Lower it only with a reason in the PR, for example "the 22 callers are all generated fixtures".

## The Risk block in the PR

```
## Risk
- Rating: medium (estimate in the brief: low)
- Reach: roundPrice, 6 caller files (src/cart.ts, src/invoice.ts, ...)
- Undo: reverts alone; the rounding mode is one constant
- Trade: +2.1% on bench/cart.js (median 4.71 ms -> 4.81 ms, noise 0.6%)
- Coverage: src/price.test.ts covers the new branch
```

When the measured rating is above the brief's estimate, say why in one line. The roadmap uses it to estimate better next time.

## What the rating changes

| Rating | Self-review mode | Merge |
| --- | --- | --- |
| low | the caller's mode, or self for S, docs and chore | auto-merge allowed when the policy allows it |
| medium | the caller's mode, or fresh | auto-merge allowed up to `merge.max_risk` (default `medium`) |
| high | always fresh | always the maintainer, as a pull request, never a direct commit or batch |

High risk does not block a change. It raises the bar: a fresh reviewer, tests on the changed lines, and a maintainer who sees the Risk block before merging.

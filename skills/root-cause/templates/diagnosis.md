# Diagnosis: <slug>

<!-- Standalone: .git/root-cause/<slug>/diagnosis.md. Roadmap diagnose node: the Diagnosis section of nodes/<id>/outcome.md. Never write a vulnerability here. -->

## Symptom

- Reported: <exact error text, or wrong value next to the right one, or timing, or flake rate>
- Seen at: <commit, version, environment, input>

## Loop

- Command: `<one command>`
- loop.py: <verdict>, <red>/<runs> red, median <s>s, at commit <sha>
- Minimal reproduction: <path, and the parts that remain, each needed for the failure>

## Hypotheses

| # | Hypothesis | Prediction | Probe | Result |
| --- | --- | --- | --- | --- |
| 1 | <X is the cause> | <changing Y turns the loop green> | <what was changed> | confirmed / ruled out |

## Cause

- Flaw: <file:line>, since <commit>
- Why it gives this symptom: <one or two sentences>
- Same flaw elsewhere: <other callers or similar code, or "none found">
- Confirmed by: <change that turns the loop green, and putting it back turns it red>

## Evidence

<!-- Copy this into the Evidence line of a fix node's brief, or the Proof section of the fix PR. -->

- Failing test: `<path>` (`<command>`, red on <commit>)
- Seam: <where the regression test lives, or "no seam: <why>">

## Fix options

| Option | Change | Reach | Cost | Undo |
| --- | --- | --- | --- | --- |
| A (recommended) | <where and what> | <call sites, users, data, public API> | <measured speed or size change, or "not on a hot path"> | <reverts alone? tunable later?> |
| B | | | | |

- Not recommended: <workarounds considered, and why not>

## Verdict

- <fix-small | fix-large | no-seam | no-loop | not-a-bug>
- Next: <pr-author fix PR to <branch> | fix node <id> | issue | user decision>
- Spent: <tokens or time>, budget <cap>

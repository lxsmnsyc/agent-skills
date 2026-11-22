# Blind review

An author and a reviewer who both start from the diff share its blind spots. A diff shows what was edited. It cannot show the doc that still describes the old behavior, the caller nobody updated, or the edge case nobody wrote down. A fresh reviewer that sees no reasoning still reads the same diff with the same priors, so it misses the same things.

This file gives the review three sources of expectations that do not come from the diff:

- what the reviewer expected before reading it
- what the repo still says about what changed
- what the docs promise, tested from outside

## Contents

- Expectations before the diff
- Comparing the diff against them
- Surface check with surface.py
- Docs tests
- Turning misses into checks

## Expectations before the diff

Write `expectations.md` in the review's notes folder (`notes` from `worktrees.py prepare`) before you open the diff or the list of changed files. Use `pr_info.py --blind`, which leaves the files out.

Read only:

- the claim: PR title and body, the linked issue, the roadmap brief and its acceptance criteria
- the base worktree's docs, README, examples and public API (entry files, exported types, CLI help) for the area the claim names

Then list what a complete change would include. Go through each kind:

| Kind | Ask |
| --- | --- |
| Behavior | What must work after the change? Each acceptance criterion, plus the behavior the claim implies but does not state. |
| Edge cases | Empty, one, many, the largest input, invalid input, an error from a dependency, two calls at once, a retry. Which apply here? |
| Callers | Which other code calls what the claim changes? Search the base for it. |
| Public surface | Exports, types, options, CLI flags, environment variables, error messages, defaults. Which ones should change, and which must stay the same? |
| Docs | Which README sections, docs pages, examples, doc comments and CLI help describe this area today? |
| Tests | Which tests should change, and which new ones should exist? |
| Release | A changeset, a migration, a deprecation notice, a note on a breaking change. |
| Out of scope | What the change should not touch. |

Write each item as one line that can be checked: `- docs/cli.md describes --dry-run: should mention the new --plan flag`. Ten to thirty lines is normal. Do not guess file names you have not seen. Name the area instead.

After this file exists, do not edit it. Write new thoughts in the comparison, so the record shows what was expected before the diff and what came after.

When an orchestrator runs the review, it enforces the order: it sends the claim first, waits for `expectations.md`, and only then sends the branch. When the review runs alone, the order is up to you. Do not run `git diff`, `gh pr diff` or `pr_info.py` without `--blind` until the file is written.

## Comparing the diff against them

Read the diff. For each expectation, mark it `met`, `missing` or `not needed` (with the reason the diff or the code gives). Then list what the diff does that no expectation covers.

- **Missing behavior or acceptance criterion**: blocking.
- **Missing doc, example, changeset or test for changed behavior**: should fix.
- **Missing edge case**: should fix when the code mishandles it (show the input); a question when it is unclear.
- **Unexpected change**: a question, or "outside the claim" when it changes behavior the claim does not mention.
- **Expectation that was wrong**: mark it `not needed`, with the reason. Wrong expectations are cheap. Unasked questions are not.

Put the table in the review under "What I checked" as counts (`expectations: 18 met, 2 missing, 3 not needed`) and list the missing ones as findings.

## Surface check with surface.py

```bash
python3 <skill>/scripts/surface.py --base <base> --head <head>
```

Run it in the repo or the head worktree. It reads the diff for names, flags, environment variables and messages that left the code or changed, then lists every mention outside the diff. It skips changelogs and past changesets.

- **stale**: something that left the code is still mentioned outside the diff. In docs, examples, CLI help or user-facing text, it is a should-fix finding. In code, it is a bug: check that it still runs.
- **changed**: docs or examples mention a name whose declaration changed. Read each mention and check that it still describes the new form.
- **changeset**: the repo releases with changesets and the change has none. A should-fix finding, unless the change does not affect the published package (see the changesets skill).

Its matches are leads, not verdicts. A plain-word name counts only where a line uses it as code. Drop a match that is something else, and say so in one line.

## Docs tests

Run this when the risk rating is medium or high, or when the change touches the public API or its docs. It catches the case where the docs and the code disagree, and both the author and the reviewer read the code and believe it.

A separate agent sees only the head's docs and public signatures, never the implementation, and writes tests from what the docs promise. A failing test means the code or the doc is wrong. Either way, it is a finding.

- The reviewer has read the code, so it cannot write these tests without bias. Spawn a new agent for them.
- A reviewer that is itself a subagent cannot spawn agents. It reports "docs tests needed" with the paths below, and the caller (pr-author, or the roadmap orchestrator) spawns the agent and sends back the results.

Prompt for the docs-test agent:

```
Write black-box tests for <package or module> in <head worktree>, using only these files:
<docs pages, README sections, examples, and the public type declarations or signatures>.
Do not open any other source file. Put the tests in <notes folder>/docs-tests/ using the repo's test runner.
For every promise in the docs (inputs, outputs, defaults, errors, examples), write one test.
Run them and report each failure with the doc line it tests and the actual result.
```

Turn each failure into a finding that quotes the doc line and the actual result. When the doc is right, the code is wrong (blocking or should fix by behavior). When the code is right, the doc is stale (should fix). Do not commit the docs tests. They live in the notes folder and go away at cleanup. Suggest the useful ones to the author as new tests.

## Turning misses into checks

When a bug reaches the base branch through a reviewed change, name the kind it belongs to: a stale doc, a missed caller, a changed default, a missing edge case, an untested branch. When the same kind recurs, add it to the table under "Expectations before the diff", or as a pattern in `surface.py` when a script can find it. In a roadmap, the curator records these as `miss:` lines in `CALIBRATION.md`.

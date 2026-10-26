---
name: pr-review
description: Review a pull request or a local branch with evidence. For fixes, reproduce the problem on the target branch and prove the change fixes it. For features, check the change answers a roadmap goal, or start a feedback loop on its value when it does not. For every change, run the project's checks (lint, typecheck, build, tests) locally and weigh simplicity and cost. Posts non-blocking comment reviews and hands approval to the maintainer instead of approving. Use this skill whenever the user asks to review a PR, look at a pull request, check a branch before merging, self-review work before opening a PR, or decide whether a PR can be approved, even if they only paste a PR number or link.
---

# PR review

A review answers three questions with evidence, not opinion:

1. Does the change do what it claims? For a fix, the problem exists on the target branch and is gone on the PR branch. For a feature, it meets its acceptance criteria.
2. Is it worth what it costs? Simplicity, runtime, size, dependencies, API surface, maintenance.
3. Does it pass what the project requires before merging? Lint, typecheck, build, tests.

Then it reports without blocking anyone. Feedback goes out as comments, never as "request changes". Approval goes to the maintainer, never from the reviewer.

## Inputs and modes

- **GitHub PR**: a number or URL. Needs `gh`.
- **Local branch**: two refs, for self-review before a PR exists and for the pr-author skill. Pass them as `pr_info.py --local --base <ref> --head <ref>` and `worktrees.py prepare --base <ref> --head <ref>`. Nothing is posted in this mode; findings go back to the caller.

## Scripts

All scripts are in `scripts/` and need only Python 3 and git (plus `gh` for GitHub PRs).

```bash
python3 <skill>/scripts/pr_info.py 42                       # PR facts, type hint, maintainer, CI, roadmap nodes
python3 <skill>/scripts/pr_info.py --local --base main --head fix/x
python3 <skill>/scripts/branch_policy.py --type feature --base main    # does this kind of change belong on that base?
python3 <skill>/scripts/worktrees.py prepare --pr 42         # base and head side by side in .git/review-worktrees/
python3 <skill>/scripts/checks.py <dir> [--run] [--install]  # detect and run lint, typecheck, build, tests
python3 <skill>/scripts/repro.py <base> <head> --copy <test> -- <command>   # fails on base, passes on head?
python3 <skill>/scripts/size_diff.py <base> <head> --glob 'dist/**/*.js'     # build output size, raw and gzip
python3 <skill>/scripts/worktrees.py cleanup pr-42
```

Work in the review worktrees, never in the user's own checkout. The user may be working there, and the review must not change their files.

## Steps

### 1. Gather

Run `pr_info.py`. Read the title, body, linked issues and the diff (`gh pr diff` or `git diff <merge-base>..<head>`). Decide the type: **fix**, **feature**, or **other** (refactor, docs, dependency update, chore). The type hint is a starting point; the diff decides. A PR that does two things is two reviews, and the comment should say it would be easier to merge as two PRs.

Check the base. `pr_info.py` reports `expected_base` and `base_ok` from the repo's branch policy (`branch_policy.py`): trunk-based repos send everything to the default branch, while gitflow-style repos send features and fixes to `dev` (or `develop`), hotfixes to the default branch, and promote `dev -> next -> main`. A PR against the wrong base is a blocking finding, because merging it would ship work to the wrong stage. The fix is quick: `gh pr edit <n> --base <expected>`. A hotfix against the default branch also needs back-merge PRs into the other integration branches; check they exist or are planned.

Check the repo's visibility. On a private repo, never trigger, re-run or wait on GitHub Actions: CI minutes are billed. Run the checks locally instead. Reading existing check results with `gh pr checks` is fine.

### 2. Prepare

`worktrees.py prepare` puts the base (the merge base the PR was written against) and the head side by side. Use `--tip` to test against the current tip of the base branch when the base has moved a lot since the PR was opened.

Install dependencies in each worktree only when a step needs to run code (`checks.py --install`). Installs are slow, so do it once per worktree.

### 3. Evaluate by type

Read `references/evaluation.md` for the full criteria and how to measure cost.

**Fix.**

1. Find the problem statement: the PR body, the linked issue, the commit message.
2. Reproduce it on the base. Prefer the test the PR adds: `repro.py base head --copy <that test> -- <command to run it>`. If the PR adds no test, write the smallest reproduction you can (a test file or a script in the review worktree, not committed) and run it the same way.
3. Read the verdict:
   - `proven`: fails on base, passes on head. The fix works for that case.
   - `not-reproduced`: the base passes too. The PR does not show the problem. Do not recommend approval. Before writing the comment, spend a few minutes looking for inputs that do produce the reported symptom (see "When the problem does not reproduce" in `references/evaluation.md`). A found cause turns the comment from "please send a reproduction" into "the real cause is X, shown by this input".
   - `not-fixed`: the head fails too. The fix does not work.
   - `inconclusive`: the command could not run. Fix the setup and try again before judging.
4. Check that the fix addresses the cause, not only the one reproduced case. Look at the other callers of the changed code.

**Feature.**

1. Find its roadmap node. `pr_info.py` lists nodes whose brief the body links to, or whose owned paths cover the changed files.
2. **When a node matches**: check every acceptance criterion in the brief, and run its `verify` command if it has one. Check the diff stays inside the node's owned paths. Then evaluate simplicity and cost as for any change.
3. **When no node matches**: the feature has not been agreed yet. Judge its value (see `references/features.md`) and lean toward feedback: the comment proposes it as a roadmap addition, with a suggested priority, size and the questions the maintainer must answer. Do not recommend approval until the feature has a node or the maintainer accepts it in the thread. This is the same loop the parallel-roadmap skill uses for ideas that arrive mid-roadmap.

**Other.** Refactors must not change behavior: run the tests on both sides and compare. Dependency updates need the changelog read for breaking changes. Docs need to match the code they describe.

### 4. Required checks (every PR)

Run `checks.py <head> --run --install`. Every detected check must pass: lint, format, typecheck, build, tests. When a check also fails on the base, say so; it is not this PR's fault, but it still blocks a clean merge.

On a public repo where CI already ran, `gh pr checks` results count, but still run the checks locally when CI is missing, failed for an unclear reason, or does not cover a kind of check.

### 5. Cost and simplicity

Measure what can be measured, and give numbers: build size with `size_diff.py`, benchmarks when the repo has them and the change touches a hot path, new dependencies with their size and license. Then judge simplicity: is there a smaller change that does the same? See `references/evaluation.md`.

### 6. Decide

Sort every finding into one of three kinds:

- **Blocking**: the change does not work, is not proven, breaks a check, breaks compatibility without saying so, or costs clearly more than it gives. Any blocking finding means no approval recommendation.
- **Should fix**: real problems that are small. Two or more of these, or one that touches behavior, also hold back approval.
- **Nit**: style, naming, wording. Nits never hold back approval.

Bugs you find on the base that the PR did not cause and does not touch are not findings against the PR. Mention them under a separate heading ("Found on `<base>`, not caused by this PR") and suggest a separate fix PR against the base branch, so the fix can ship on its own and this PR is not held up.

Then:

- **Clean** (no blocking or should-fix findings): no review comment is needed. Hand the approval to the maintainer (step 7). Mention nits only if the author would clearly want them, as one optional comment.
- **Not clean**: post one comment review that says why it cannot be approved yet, with each finding and what would resolve it. Use the format in `references/review-format.md`.

### 7. Post and hand off

Reviews are non-blocking: post with `gh pr review <n> --comment --body-file <file>`, never with `--request-changes`, and never `--approve`.

Before posting anything to GitHub, show the user the review text and ask, unless the user already said to post (for example "review and post", or a standing instruction). Posting is visible to others and cannot be fully undone.

A roadmap with an `auto` merge policy lets the orchestrator merge clean PRs without the maintainer; the reviewer's verdict is one of its inputs (`--review-clean` means no blocking and no should-fix findings). The reviewer still never approves. Otherwise, the approval goes to the maintainer that `pr_info.py` reports:

- **The maintainer is the user in this session**: give them the evidence summary and the exact command to approve (`gh pr review <n> --approve`), and let them run it or tell you to.
- **The maintainer is someone else**: post a short comment review that says the PR is ready for maintainer approval, with the evidence summary, and mention the maintainer's login so they are notified.

In local mode, post nothing. Return the findings and the verdict to the caller.

### 8. Clean up

The reviewer only removes its own review worktrees. It never deletes the PR's branch, locally or on the remote: that belongs to the author, who prunes it after the merge (the pr-author skill does this).


Run `worktrees.py cleanup --all`. Copy its output line into the final summary as it is printed (`cleanup: no review worktrees left`). If it lists worktrees that are still registered, say so instead of reporting the cleanup as done.

## What the user sees

End with a short summary in the chat:

```
PR #42 fix: sum skipped the first item
Verdict: ready for maintainer approval | not approvable yet | needs a decision (feature not on the roadmap)
Proof: src/sum.test.js fails on main (exit 1), passes on the branch (exit 0)
Checks: lint pass, typecheck pass, build pass, test pass (local)
Cost: +0.1kB gzip, no new dependencies
Findings: 0 blocking, 1 should fix, 2 nits
Posted: comment review (link) | not posted, waiting for your go-ahead
cleanup: no review worktrees left
```

Write all review text by the plain-writing rules if that skill is installed: short sentences, exact paths and numbers, no metaphors.

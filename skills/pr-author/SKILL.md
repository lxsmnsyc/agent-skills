---
name: pr-author
description: Write code changes as small, independent pull requests that can merge at any time. Uses git worktrees when the machine has room, splits any bug found on the base branch into its own fix PR so it ships without waiting, keeps PRs non-blocking (flags, expand and contract, owned paths), runs the project's checks locally, self-reviews with a fresh agent running the pr-review skill, and hands the PR to the maintainer. Use this skill whenever the user asks to implement a feature or fix and open a PR, work on several branches at once, split work into PRs, or when a roadmap worker from the parallel-roadmap skill builds a node, even if they do not say "pull request".
---

# PR author

Every pull request should be able to merge on its own, at any time, without waiting for another one. That is what lets several agents and people work at once without blocking each other. This skill is the habits and tools that make that true.

## Scripts

```bash
python3 <skill>/scripts/capacity.py                 # how many worktrees this machine can take now
python3 <skill>/scripts/wt.py new <branch> --base main   # worktree in .worktrees/<branch>, hidden from git status
python3 <skill>/scripts/wt.py list
python3 <skill>/scripts/wt.py remove <branch> [--delete-branch]
python3 <skill>/scripts/wt.py prune-merged --base main [--base dev] [--remote] [--dry-run]
python3 <skill>/scripts/ci_guard.py                 # will a push start billed CI? exit 2 means ask first
```

The pr-review skill provides `checks.py` (lint, typecheck, build, tests), `repro.py` (fails on base, passes on head) and the review itself. This skill uses them from `<skills>/pr-review/scripts/`.

## Steps

### 1. Decide where to work

Run `capacity.py`. It weighs free memory, CPU load, free disk and existing worktrees.

- **2 or more**: use one worktree per branch with `wt.py new`. Several branches (yours or other agents') can then be worked on and checked at the same time.
- **1**: the machine is busy. Work one branch at a time in a single worktree or the main checkout, and say why.

Never work directly in the user's main checkout when it has uncommitted changes. Those are theirs.

Each worktree has an index (shown by `wt.py new` and `wt.py list`). When a dev server or test database needs a port, derive it from the index (for example `3000 + 10 * index`) so parallel worktrees do not collide.

### 2. Branch from the right base

Find the base with `python3 <skills>/pr-review/scripts/branch_policy.py --type <feature|fix|hotfix|...>`. Trunk-based repos use the default branch for everything. Gitflow-style repos (a `dev` or `develop` branch exists, maybe `next`) send features and fixes to `dev`, hotfixes to the default branch, and promote `dev -> next -> main` in release PRs. A roadmap's `GOAL.md` or a `.github/branches.yml` file can set the policy explicitly. When a roadmap node has a `target`, that wins.

Start from the latest base: `git fetch` first, then `wt.py new <branch> --base origin/<base>` or the local base. Name branches by type: `feat/...`, `fix/...`, `hotfix/...`, `refactor/...`, `docs/...`, `release/...`. When the work starts in a worktree with a generated branch name (such as `worktree-agent-<hash>`), rename it with `git branch -m <descriptive name>` before the first commit, so the pull request does not carry the generated name. For a roadmap node, use the `branch` and `pr_title` from `plan.py ready --json`.

**Hotfix**: a fix that must reach the released branch now. Branch from the default branch, open the PR against it, and after it merges open back-merge PRs into the other integration branches (the `back_merge` list from `branch_policy.py`, for example `next` then `dev`), so the fix is not lost at the next release. A normal fix goes to `dev` and ships with the next release.

**Release**: a PR from one stage to the next (`dev -> next`, `next -> main`) with no new code in it. Its description lists the changes it promotes. In a roadmap it is a `type: release` node.

When building a roadmap node, the node's brief is the spec. Stay inside its owned paths.

### 3. Build it non-blocking

Read `references/non-blocking.md`. The short version:

- **One concern per PR.** A feature, a fix and a refactor are three PRs.
- **Small.** A reviewer reads it in one sitting.
- **Mergeable alone.** Unfinished features hide behind a flag or stay unreachable. Breaking changes go through expand, migrate, contract. Nothing depends on a PR that has not merged, unless it is stacked on purpose (step 4).
- **Touch shared files lightly.** Append to registries. Do not reformat or reorder files you do not own.

### 4. A bug in the base branch

When you find a bug that exists on the base branch (not one your branch introduced):

1. **Confirm it on the base.** Write the smallest failing test. Run it on the base with `repro.py` from pr-review, or in a worktree of the base. A bug you cannot show on the base is not ready for a fix PR.
2. **Decide.**
   - **The cause is clear and the fix is small**: fix it in its own PR. `wt.py new fix/<slug> --base <base>`, add the failing test, fix, check, self-review, open the PR against the branch the policy gives for a fix (or for a hotfix, when the bug is in released code and cannot wait for the next release). It ships on its own, without waiting for your feature.
   - **The cause is unclear or the fix is large**: do not guess. Write an issue (or a roadmap inbox entry) with the failing test and what you found, and tell the user.
3. **Your feature branch.**
   - **It does not need the fix**: leave the fix out of the feature branch entirely. The two PRs merge in either order.
   - **It is blocked by the bug**: stack it. Rebase the feature branch onto the fix branch, open the feature PR against the fix branch or the base, and write "Depends on #<fix PR>" at the top of its description. After the fix merges, rebase onto the base. GitHub retargets a PR when its base branch is deleted after merge.
   - **Never** hide the fix inside the feature PR. It would then wait for the feature's review, and a revert of the feature would bring the bug back.

### 5. Check

Run the project's checks in the worktree: `python3 <skills>/pr-review/scripts/checks.py <worktree> --run --install`. All of them must pass. When a check also fails on the base, say so in the PR and do not try to fix unrelated failures in this PR.

### 5b. Performance pass

When the change is a finished feature on code that runs often (render loops, request handlers, parsers, startup) or adds to what a browser downloads, run the perf-pass skill on it now, before the self-review: measure, try several options, keep the one with the best gain for its cost. Put its numbers in the PR's Cost section. Skip it for fixes, docs and changes with no measurable cost, and say so in the PR.

### 6. Self-review

Skip this step only for changes with no code or behavior in them, such as a typo in prose or a comment. Say in the PR that it was skipped and why. For everything else:

Spawn a fresh agent to review the branch with the pr-review skill in local mode. Give it only the repo path, the base and the branch name. Do not give it your reasoning or a summary of what you did, because a reviewer that sees your reasoning tends to agree with it.

```
Review <branch> against <base> in <repo> with the pr-review skill, in local mode. Do not post anything.
Return the verdict and the findings, sorted into blocking, should fix, nits, and bugs found on the base.
```

Then:

- **Blocking and should fix**: fix them at the cause, with the simplest correct change, and run the checks again. A fix that hides the symptom (rounding a float to some number of places, a tolerance, a retry, a special case for the reported input) is not done. Change the representation or the logic instead, for example compute money in integer cents.
- **Nits**: fix the trivial ones (a rename, a typo, a one-line change with no behavior change). Leave the rest, and list them under "Not done" in the PR description. A nit that needs restructuring or touches many files is not worth holding the PR for.
- **Bugs found on the base**: handle them as in step 4. Every fix PR you open this way gets its own self-review round before it is handed over.

Run at most two review rounds. If blocking findings remain after the second, stop and tell the user what is left instead of looping.

### 7. Open the pull request

1. Run `ci_guard.py`. On a private repo where a push would start workflows, ask the user before pushing: CI minutes there are billed. Until they say yes, keep the branch local and report the local checks.
2. Rebase onto the latest base, and rerun the checks if the base moved.
3. Write the description from `references/pr-body.md`: what and why, changes, proof (the failing test on the base and passing on the branch, for fixes), roadmap node, cost, risk, and anything not done.
4. `git push -u origin <branch>` and `gh pr create --base <base> --body-file <file>`. Do not merge it.
5. If the PR is a roadmap node and the roadmap's merge policy is `auto`, the orchestrator decides with `plan.py can-merge` and may merge it without the user (parallel-roadmap, "Auto-merge"). Otherwise, hand it to the maintainer as pr-review describes: if the user is the maintainer, give them the link, the evidence and `gh pr review <n> --approve`. Otherwise post a short comment that it is ready for maintainer approval and mention them.

Write all PR text by the plain-writing rules if that skill is installed.

### 8. Keep it mergeable

When the base moves and the PR conflicts, rebase onto the base, resolve the conflicts in the worktree, rerun the checks, and push with `--force-with-lease`. Resolve conflicts by keeping both sides' intent. When that is not clear, ask the author of the other change or the user.

### 9. Clean up

After a PR merges, run `wt.py prune-merged` with every integration branch as a `--base` (for example `--base main --base next --base dev`, the branches in the policy's `promote` list). For each merged branch it removes the worktree and the local branch. It asks GitHub for the merged pull request, so squash and rebase merges are found too, and it falls back to commit ancestry without `gh`. It keeps branches with no commits yet, branches with commits newer than their merged PR, and worktrees with uncommitted changes.

The remote branch:

- If the repo deletes head branches on merge (GitHub setting "Automatically delete head branches"), nothing more is needed.
- Otherwise add `--remote` to delete the remote branch of each merged PR. Deleting a remote branch is visible to others, so the first time in a repo, show the user what `--dry-run --remote` would delete and ask. Suggest turning the setting on with `gh repo edit --delete-branch-on-merge` (also a change others see, so ask).

GitHub moves stacked PRs onto the next base when their base branch is deleted after a merge, so deleting a merged fix branch does not break a feature stacked on it.

## What the user sees

```
Opened #57 fix: subtotal skipped the first item -> main (ready for your approval: gh pr review 57 --approve)
Opened #58 feat: sales tax on the subtotal -> main (independent of #57)
Proof (#57): src/cart.test.js fails on main, passes on fix/subtotal-first-item
Checks: lint, build, tests pass locally on both branches
Self-review: 1 round, 0 blocking, 1 nit fixed, 1 nit left (listed in #58)
Worktrees: .worktrees/fix-subtotal-first-item, .worktrees/feat-tax (pruned after merge)
```

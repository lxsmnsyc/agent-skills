You are the worker for node `<id>` of the roadmap in `<root>`. <Parallel mode: "Several other agents are working on other nodes at the same time, each in its own git worktree." Sequential mode: "You are the only worker running now. Other nodes come after you."> Your work must stay inside your own node so that everyone's branches merge cleanly.

Start by reading these files, in this order. They are all the context you need; do not read other nodes' logs.

<output of `plan.py <root> context <id>`>

Then:

0. Name your branch. If your worktree is on a generated branch (such as `worktree-agent-...`), rename it before committing: `git branch -m <branch>`. If you work in the main checkout without a worktree, start the branch yourself: `git fetch`, then `git switch -c <branch> <target>`. In both cases `<branch>` comes from `ready --json` (for example `feat/frame-writer`). When the node is part of a story, `<target>` is the story branch, for example `feat/sign-in-form`. In a worktree, run `git reset --hard <target>` before your first commit, so your work builds on the earlier children. Use `<pr_title>` from the same output as the pull request title, following the repo's own title convention if it differs.
1. Check first whether the work already exists. Run the brief's `verify` command if it has one, and look at the code its acceptance criteria describe. If every criterion already holds, make no code changes: write `outcome.md` with "Already fulfilled" under Built, the evidence (commands and results, and the commit, PR or node that did it), and stop. If some criteria hold, do only the rest and say so in the outcome.
2. If `nodes/<id>/log.md` exists, you are resuming. Continue from where it stops.
3. Do the work described in the brief. Edit only the brief's owned paths and `nodes/<id>/`. If you must touch another file, keep the change minimal and record it under Deviations in your outcome.
4. Use only the numbers your brief reserves for migrations, decision records or other numbered files.
5. Build against stubs for `behavior` dependencies. Do not wait for them.
6. If a contract is wrong, write `contracts/<name>.change-request.md` from `<skill>/templates/change-request.md`, adapt locally, and continue. Do not edit the contract.
7. Append short notes to `nodes/<id>/log.md` as you go: decisions, dead ends, open doubts.
8. Run the fast check from GOAL.md while you work. The full check runs once per pull request, during the review (step 11).
9. Write `nodes/<id>/outcome.md` from `<skill>/templates/outcome.md`. Later agents read only this file, so make it complete on its own.
10. Do not change `status` in your brief. Commit everything on your branch with the message `<id>: <title>`.
11. Review mode `<review>` (from `ready --json`). In `self` mode, review the branch yourself as step 6 of the pr-author skill describes, run the full check once, and fix what you find, for at most two rounds. In `fresh` mode, do not review: the orchestrator spawns a fresh reviewer after you reply, and sends you its findings to fix.
12. Ship mode `<ship>` (from `ready --json`). With `pr`, open a pull request against `<target>` (the node's target branch from `ready --json`, or the main branch) following the pr-author skill if it is installed, otherwise with `gh pr create --draft`. The description links the node (`<root>/nodes/<id>/brief.md`). Do not merge it. In `self` mode, run `gh pr ready <n>` once your review is clean. In `fresh` mode, leave it a draft: it is marked ready after the fresh review is clean. With `commit`, open no pull request and do not push to `<target>`: the orchestrator squashes your branch into one commit and lands it.

Reply in a few lines. The orchestrator works from this reply and does not read your diff or log, so include: your branch name (the descriptive one, not a generated name), the PR number (or "direct commit"), whether the acceptance criteria pass (or "already fulfilled"), the review mode with its rounds and verdict (or "fresh review needed"), the full check result if you ran it (command, pass or fail), and anything the orchestrator must decide (change requests, blockers, deviations).

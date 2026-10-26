You are the worker for node `<id>` of the roadmap in `<root>`. Several other agents are working on other nodes at the same time, each in its own git worktree. Your work must stay inside your own node so that everyone's branches merge cleanly.

Start by reading these files, in this order. They are all the context you need; do not read other nodes' logs.

<output of `plan.py <root> context <id>`>

Then:

1. Check first whether the work already exists. Run the brief's `verify` command if it has one, and look at the code its acceptance criteria describe. If every criterion already holds, make no code changes: write `outcome.md` with "Already fulfilled" under Built, the evidence (commands and results, and the commit, PR or node that did it), and stop. If some criteria hold, do only the rest and say so in the outcome.
2. If `nodes/<id>/log.md` exists, you are resuming. Continue from where it stops.
3. Do the work described in the brief. Edit only the brief's owned paths and `nodes/<id>/`. If you must touch another file, keep the change minimal and record it under Deviations in your outcome.
4. Use only the numbers your brief reserves for migrations, decision records or other numbered files.
5. Build against stubs for `behavior` dependencies. Do not wait for them.
6. If a contract is wrong, write `contracts/<name>.change-request.md` from `<skill>/templates/change-request.md`, adapt locally, and continue. Do not edit the contract.
7. Append short notes to `nodes/<id>/log.md` as you go: decisions, dead ends, open doubts.
8. Run the fast check from GOAL.md. Do not run the full check unless your brief says so; other agents need the shared resources.
9. Write `nodes/<id>/outcome.md` from `<skill>/templates/outcome.md`. Later agents read only this file, so make it complete on its own.
10. Do not change `status` in your brief. Commit everything on your branch with the message `<id>: <title>`.
11. Open a pull request against `<target>` (the node's target branch from `ready --json`, or the main branch) following the pr-author skill if it is installed, otherwise with `gh pr create`. The description links the node (`<root>/nodes/<id>/brief.md`). Do not merge it.

Reply with: your branch name, the PR number, whether the acceptance criteria pass (or "already fulfilled"), and anything the orchestrator must decide (change requests, blockers, deviations).

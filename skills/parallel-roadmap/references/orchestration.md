# Orchestration

How to run nodes with several agents at once, ship their work, and keep the plan correct while it runs.

## Contents

- Roles
- One pull request per node
- Rolling and waves
- The loop
- Spawning a worker
- Already fulfilled work
- Merging and verification
- Shared and exclusive resources
- Contract change requests
- Gates
- Failure handling
- Running a wave as a Workflow

## Roles

- **Orchestrator**: the main agent in the user's session. It is the only one that edits `status` fields, contracts and other shared roadmap files. A single writer for shared state removes a whole class of conflicts.
- **Workers**: one per node, each in its own git worktree on its own branch. A worker edits its owned paths and its own `nodes/<id>/` folder, and opens one pull request.
- **Reviewer**: a fresh-context agent that reviews each pull request (the pr-review skill, if installed), and reviews the plan itself during the stress test.
- **Curator**: runs at checkpoints. See `memory.md`.
- **Maintainer**: the person who approves and merges pull requests. By default the repo owner or the user. Agents never approve their own work.

## One pull request per node

Each node ships as its own pull request against its target branch: the main branch in trunk-based repos, or the branch the policy in `GOAL.md` gives for the node's type in gitflow-style repos (for example features to `dev`). This is the default because it keeps every piece of work mergeable on its own: nothing waits for a large integration branch to be finished.

What makes this safe:

- The contract wave merges first, so every later pull request builds on frozen interfaces that already exist on the main branch.
- Work that is not ready for users goes behind a feature flag, or stays unreachable until the node that wires it up lands.
- Breaking changes use expand, migrate, contract (see `decomposition.md`), so each step is safe to merge alone.
- `behavior` dependencies build against stubs, so their pull requests merge before the real implementation exists.

On a private repo, pushing a branch can start billed CI runs. Check `gh repo view --json visibility` before the first push. If the repo is private, ask the user whether to push, or to keep branches local, run the checks locally, and merge locally.

A node is `done` when its pull request is merged into its target. Track the pull request number in the brief's body (not in frontmatter) or in the outcome.

With several stages (`dev -> next -> main`), work moves on through release nodes: a `type: release` node is one promotion pull request (for example `dev` into `next`), gated for the user. When a release node into the last stage merges, the curator sets the nodes it shipped to `released`. Promotion carries everything that is on the source branch, not only the nodes the release was planned for. So before a release node runs, decide for each other open node targeting the same branch: merge it after the cut, put it behind a feature flag that stays off, or include it in the release on purpose. `plan.py check` lists those nodes as a warning on the release node.

Hotfix nodes target the released branch directly, and the worker opens the back-merge pull requests into the other stages after the hotfix merges.

Use an integration branch instead only when the user asks for it, or when the main branch must never contain partial work and flags are not an option. Then workers target `roadmap/<slug>`, and the user merges that branch at the end.

## Rolling and waves

- **Rolling** (default for interactive sessions): when a pull request merges, ask `plan.py ready` and start whatever became ready. Nothing waits for the slowest node in a wave. Run the curator after every few merges, or when an outcome reports a deviation.
- **Waves**: start all ready nodes, wait for all of them, curate, repeat. Simpler, with a clean checkpoint every round, but a wave takes as long as its slowest node. Use it with the Workflow script, or when the user wants to review each round.

Waves printed by `plan.py status` are a forecast in both modes. The decision to start a node always comes from `plan.py ready`.

## The loop

1. `python3 <skill>/scripts/plan.py <root> check`. Stop on errors.
2. `python3 <skill>/scripts/plan.py <root> verify` runs the `verify` commands of all todo nodes. Close any node whose acceptance already holds (see "Already fulfilled work").
3. `python3 <skill>/scripts/plan.py <root> ready --json`. The list is sorted by priority, then by critical path. Take up to `--max-parallel` nodes from the top.
4. Set each one to `status: active` and commit that to the main branch (or the integration branch). Keep the commit to the brief files only.
5. Spawn the workers in a single message so they run at the same time (see "Spawning a worker").
6. When a worker returns, send its pull request to review (see "Merging and verification").
7. When the pull request merges, set `status: done`, and run the curator at checkpoints.
8. Stop at gates (see "Gates"). Otherwise go to step 1.

## Spawning a worker

Use the Agent tool with `isolation: "worktree"` and the model from `ready --json`. Fill in `templates/worker-prompt.md`. The prompt names the node, the root, the base branch and the exact context files. It does not paste their contents, so the worker reads the current versions.

Before spawning, check that the base branch already contains what the worker needs: the frozen contracts and the outcomes of its dependencies.

Check the machine before a wide wave. Each worktree may need its own dependency install and dev server. If memory is tight or the load is high, lower `--max-parallel`. The pr-author skill has a capacity check for this.

## Already fulfilled work

A node can be done before anyone builds it: the code shipped before the roadmap, a planning document was stale, or another node's pull request covered it on the way. Building it again wastes a session at best and conflicts with the existing code at worst.

Three places catch it:

- **Survey and import**: check each item against the code before writing its node. Already built items become `done` nodes with `fulfilled_by:` set, or are left out with a note in `GOAL.md` under Sources.
- **Before spawning**: `plan.py verify` runs the `verify` command of every todo node. A pass means the acceptance may already hold. Look at the evidence, then close the node with `fulfilled_by:` and a short outcome.
- **Inside the worker**: the worker's first step is to check whether the work exists. If it does, the worker writes an "Already fulfilled" outcome with the evidence and makes no code changes.

When the existing code differs from what a contract assumed, rewrite the contract from the real code before freezing it, and update the briefs that use it.

Partly fulfilled nodes: if the node has not started, shrink its brief to what is left and resize it. If it is active, the worker handles it. When the remainder becomes its own follow-up node, it keeps the original node's priority. Changing priority is the user's decision, so propose it in the response instead of doing it.

A passing `verify` command is a signal, not proof. Read the code before closing a node: an empty stub or a placeholder test can make a weak check pass.

## Merging and verification

For each finished worker (closing a node also means ticking its acceptance boxes in the brief, or saying which ones the existing code covers):

1. Read its `outcome.md`. If it reports a blocker or an unresolved deviation, resolve it before review.
2. Check that the diff stays inside its owned paths and its node folder. Changes outside owned paths are the main source of merge conflicts and hidden coupling. Either accept them and note them in the outcome, or send the worker back.
3. Run the review. Spawn a fresh-context reviewer (the pr-review skill) on the pull request. Fix what it finds, for at most two rounds.
4. Run the checks required by the repo: lint, typecheck, build, tests. On a private repo, run them locally and do not trigger CI.
5. Decide who merges (see "Auto-merge" below). Without an `auto` merge policy, hand the pull request to the maintainer. Never approve it yourself.
6. If a merged pull request breaks the main branch, revert it and reopen the node with the failure in its log.

Merge conflicts still happen. Resolve them in the worker's branch, by the worker or the orchestrator, then rerun the checks.

## Auto-merge

By default every pull request waits for the maintainer. A roadmap can opt in to merging some of them without the user, in `GOAL.md`:

```yaml
merge:
  mode: auto                                   # maintainer is the default
  method: squash
  max_size: M                                  # larger nodes go to the maintainer
  exclude: [release, hotfix, contract, gate]   # always go to the maintainer
```

Only switch to `auto` when the user asks for it. Merging is visible to everyone on the repo.

With `mode: auto`, the decision is the script's, not yours:

```bash
git diff --name-only <base>...<branch> | \
  python3 <skill>/scripts/plan.py <root> can-merge <id> --review-clean --checks-pass [--proof] \
    [--ci-guard ask] --files -
```

Pass `--review-clean` only when the pr-review verdict had no blocking and no should-fix findings, `--checks-pass` only when lint, typecheck, build and tests passed on the branch rebased onto the current base, `--proof` only when a fix fails on the base and passes on the branch, and `--ci-guard ask` when pr-author's `ci_guard.py` says a merge would start billed CI. Exit code 0 (`auto`) means:

1. Merge: `gh pr merge <n> --squash --delete-branch` (or the policy's method).
2. Run the checks on the updated base. If they fail, revert the merge in a new pull request at once, merge that revert (restoring a green base is always allowed), set the node back to `todo` with the failure in its log, and tell the user.
3. Set the node to `done`.

Exit code 1 (`maintainer`) lists the reasons; hand the pull request to the maintainer with them. If branch protection on the base requires approvals, auto-merge cannot work; say so and keep the maintainer mode.

At every checkpoint, report what merged on its own, with links, so the user sees it without asking.

## Shared and exclusive resources

- **Global numbers** (migrations, decision records): reserved per node with `reserves:`. Assign placeholders at merge time only when the numbers cannot be known in advance.
- **Generated files**: regenerate once after merging, in its own small pull request if needed.
- **Exclusive resources**: some work cannot run twice at once. Load tests and benchmarks give wrong numbers when they share a machine. A database container on a fixed port cannot be started twice. Tag such nodes with `exclusive: [loadtest]` (any name). The scheduler never puts two nodes with the same tag in one wave.
- **Slow full checks**: tell workers to run only the fast check. Run the full check on the pull request, once.

## Contract change requests

A worker that finds its contract is wrong does not edit the contract. It writes `contracts/<name>.change-request.md` (from the template), adapts its own code locally, and reports the request in its outcome.

The orchestrator then decides:

- **Accept**: update the contract, bump `version`, and list every node that uses it (`plan.py impact` on each consumer helps). Active consumers finish against the old version. Add follow-up nodes to adapt them, or update the briefs of consumers that have not started.
- **Reject**: tell the requester to adapt to the contract as written. Record the reason in the request file.

Without this rule, one worker's quick fix to a shared type breaks every parallel branch that builds on it.

## Gates

Stop and show the user:

- After the stress test, before any execution.
- After the contract wave. Contracts are the most expensive thing to get wrong.
- After any node with `gate: true`.
- When an accepted change request affects more than one active node.

The user can waive gates. Record that in `GOAL.md` so later sessions know.

## Failure handling

- **Worker fails or runs out of context**: keep its branch and log. Reopen the node (`status: todo`) and spawn a new worker. It resumes from `log.md`. If it fails twice, the node is too big or its brief is unclear. Split it or rewrite the brief.
- **Node proves impossible**: set `status: dropped`, write why in its outcome, and run `plan.py check` to see which nodes are now broken. Rework those with the user.
- **Two workers conflict despite disjoint owned paths**: the owned paths were wrong. Fix them in the briefs.

## Running a wave as a Workflow

For long roadmaps, `scripts/wave.workflow.js` runs one wave: it spawns all workers in parallel, each in a worktree with its suggested model, then runs a curator agent over the results. The orchestrator still handles reviews, status changes and gates between waves, because the Workflow script cannot read or write files.

Only use it when the user has asked for workflow orchestration, or when they invoked this skill to run waves:

```
plan.py <root> ready --json        # becomes args.nodes
Workflow({ scriptPath: "<skill>/scripts/wave.workflow.js",
           args: { root: "<root>", skill: "<skill>", base: "main", nodes: [...] } })
```

It returns each worker's report (branch, pull request, status) and the curator's proposals.

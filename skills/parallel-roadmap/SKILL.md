---
name: parallel-roadmap
description: Plan and run feature roadmaps as a dependency graph so several coding agents can work at the same time without blocking each other. Covers goal discovery, breaking work into right-sized nodes with typed dependencies, blindspot review, contract-first interfaces, wave scheduling, running waves of agents in git worktrees, and keeping long-term memory in the repo. Use this skill whenever the user wants to plan a feature, write or revise a roadmap, break a big change into tasks, convert an existing plan, proposal or ADR set into parallel work, run the next batch of roadmap work with agents, check roadmap status, or asks how to make agents work concurrently, even if they never say "roadmap" or "DAG".
---

# Parallel roadmap

A linear roadmap makes every item wait for the one above it. Most of those waits are not real. A feature usually needs another feature's interface, not its finished code. This skill plans work as a graph of nodes with typed dependencies, freezes the shared interfaces first, and then runs every node whose inputs are ready at the same time, one agent per node, each in its own worktree.

## Pick the entry point

Ask yourself what the user needs right now, then go to that phase. Do not run all phases when the user asks for one thing.

| The user wants to | Start at |
| --- | --- |
| plan something new | 1. Discover |
| turn an existing plan, proposal, ADR batch or backlog into a roadmap | 0. Survey, then 2. Decompose |
| review or harden a plan | 3. Stress-test |
| run the next batch of work | 6. Execute |
| add a feature or change scope while work is running | Change (below) |
| know where things stand | run `plan.py <root> status` and summarize |
| close out a roadmap | 8. Close |

## Files

A roadmap lives in the repo, so it is versioned with the code and survives device changes. Use `docs/roadmaps/<slug>/` when the repo has a `docs/` folder, otherwise `roadmaps/<slug>/`.

```
<root>/                       # e.g. docs/roadmaps/perf-batch/
  GOAL.md                     # L0: outcome, constraints, non-goals, verification commands
  CLAUDE.md                   # L0: rules for agents working on this roadmap (short)
  contracts/<name>.md         # frozen interfaces between nodes
  contracts/<name>.change-request.md
  nodes/<id>/brief.md         # planner writes: goal, typed deps, owned paths, size, acceptance
  nodes/<id>/log.md           # worker's private notes, never read by other nodes
  nodes/<id>/outcome.md       # worker's distilled result, the only thing that flows downstream
  reviews/                    # premortem, adversarial review, wave reports
```

Templates for each file are in `templates/`. Copy them; do not invent new fields, because `scripts/plan.py` reads the frontmatter.

Status lives in exactly one place: the `status` field of each brief. `done` means the node's pull request merged into its target branch. In repos with several stages (`dev -> next -> main`), `released` means the work reached the last one; the curator sets it when a release node merges. Other documents link to the roadmap instead of restating status. Repos that track status in three places (a strategy doc, an ADR header and a proposal list) drift apart within weeks.

Use the repo's existing decision record system when there is one (for example `docs/decisions/NNNN-*.md`). Only create `<root>/decisions/` when the repo has nothing.

## The script

`scripts/plan.py` is the source of truth for the graph. Do not schedule by reading the briefs and reasoning about them, because it is easy to miss an edge or an overlap. Run the script.

```bash
python3 <skill>/scripts/plan.py <root> status          # validate, waves, critical path, parallelism
python3 <skill>/scripts/plan.py <root> check           # validation only, exit 1 on errors
python3 <skill>/scripts/plan.py <root> ready --json    # nodes that can start now, with model and context files
python3 <skill>/scripts/plan.py <root> context <id>    # the files an agent on <id> should load, with token estimates
python3 <skill>/scripts/plan.py <root> impact <id>     # what adding <id> does: overlaps, contracts, critical path
python3 <skill>/scripts/plan.py <root> verify [<id>]   # run verify commands; finds todo nodes that are already fulfilled
```

Options: `--max-parallel N` (default 4), `--budget TOKENS` (default 20000), `--upto must|should|could|later`, `--cwd DIR` (where verify commands run, the repo root).

`verify` runs project commands (tests, builds) in the directory given by `--cwd`. That is usually the user's own checkout, which they may be working in. Before the first `verify` in a session, check `git status`: if the tree has uncommitted changes, tell the user what will run and ask first, or run it in a separate worktree.

## Dependency kinds

Every dependency has a kind. The kind decides when the dependent node can start.

- `contract`: the node needs only an interface, type, schema or file format. It can start once that contract is frozen. Needs `via: <contract>`.
- `behavior`: the node needs real runtime behavior, but can be built against a stub of the contract and integrated later. It starts when the contract is frozen. The script lists it under "integration pending" until the upstream node is done. Needs `on` and `via`.
- `hard`: the node needs the other code to exist, for example a refactor of the same function. It starts when the upstream node is done. Needs `on` and a `why`.

Agents label too many dependencies as `hard`. For each one, ask: "could this start against a frozen interface and a stub?" If yes, it is `contract` or `behavior`. A `hard` dependency without a `why` is a warning.

## 0. Survey (existing repos)

Before you plan, learn how the repo already plans. Look for:

- Planning documents: strategy or roadmap files, proposals, ADRs, backlogs, `## Order` or `Next steps` sections.
- Global counters that parallel branches will collide on: ADR numbers, migration numbers, numbered step lists, generated files. Record them in `GOAL.md` under "Numbered resources".
- Verification: the check command, how long it takes, and whether two copies can run at once (shared database containers, fixed ports).
- Hot files that many features touch: route registries, config, barrel exports, the main plan document itself.
- Resources that only one task can use at a time: load tests, benchmarks, a database container on a fixed port.
- The branching model. Run pr-review's `branch_policy.py` (or look for `dev`, `develop`, `next`, `release/*` branches and CONTRIBUTING). When the repo uses more than one integration branch, write the policy into the `branches:` frontmatter of `GOAL.md`, so every node gets the right target.
- Whether the repo is private (`gh repo view --json visibility`). Pushing branches to a private repo can trigger billed CI. If the user does not want that, workers keep branches local and checks run locally.

When importing a prose plan, keep a link from each node back to the paragraph it came from. Do not rewrite the source documents.

Check each imported item against the code before writing its node. Planning documents go stale, and items listed as pending are often already built. Spend a minute per item: grep for the names it introduces, look for its tests, search `git log`. Already built items become `done` nodes with `fulfilled_by:` set, or are left out with a note in `GOAL.md`. Partly built items get a brief for the remainder only.

## 1. Discover

Work out the goal with the user in a short feedback loop. Write `GOAL.md` from the template: outcome, priorities, constraints, non-goals, verification commands, numbered resources, open questions. Keep it under about 1,500 tokens because every agent loads it.

Agree on what "must" means for this roadmap, usually a release or a user-visible milestone. Without that line, everything becomes a must and priorities stop meaning anything.

## 2. Decompose

Read `references/decomposition.md` before this step. It holds the sizing rubric, the split strategies and the merge rules.

A node is one pull request: a change a reviewer can read in one sitting and that is safe to merge on its own. That sets the size range. Most nodes are M. Many S nodes in a row on the same files mean the plan is cut too fine, and each extra node costs a worktree, a review and a merge. As a rough check, a batch of work a single developer would do in two or three weeks should give about 8 to 20 nodes, not 40.

For each node, write `nodes/<id>/brief.md` with priority, typed dependencies, owned paths (globs), size, acceptance criteria and a `verify` command when the acceptance can be checked by one. Keep briefs short: what the worker cannot get from the contracts and dependency outcomes, and nothing else. Then:

1. Prefer vertical slices over horizontal layers. "Login, full stack" runs beside "signup, full stack". "UI, then API, then DB" is a chain.
2. Name every shared interface as a contract in `contracts/`, with `status: draft` and `defined_by` set to the node that will freeze it.
3. Put contract-freezing nodes, spikes for risky unknowns, and changes to hot shared files in the first wave.
4. Set a priority on every node by weighing its value to the project against its size (see "Priority" in `references/decomposition.md`): `must` is needed now, `should` is important but the goal can be reached without it, `could` is worth doing when capacity is free, and `later` is parked and not scheduled. Propose the priorities, then let the user confirm them, because value is the user's call.
5. Give each node a `type` (feature, fix, hotfix, refactor, docs, release, ...). With a branch policy in `GOAL.md`, the type decides the branch its pull request targets, and `plan.py` shows it as `-> dev`. Set `target` only to override. Promotions between stages are `type: release` nodes with `from` and `target` (for example `from: dev`, `target: next`), gated, and depending on the work they ship; `plan.py check` warns when a release node does not wait for open work on its `from` branch.
6. Reserve global numbers up front with `reserves:` (for example `reserves: [migration 00043, adr 0067]`). The script fails when two nodes reserve the same one. Tag nodes that need a single-use resource with `exclusive:`, for example `exclusive: [loadtest]`.
7. Run `plan.py <root> status`. Fix every error. Then work on the result:
   - A long critical path means too many `hard` edges. Challenge them, or split the nodes on the path.
   - A node deferred because of an owned path overlap, or a "shared ... plan the merge order" note, means several nodes edit the same file. Prefer splitting that file by feature in an early, behavior-preserving node, so each later node owns its own module (see "Split hot files by feature first" in `references/decomposition.md`). Otherwise accept the serialization or plan the merge order.
   - An XL node must be split.
   - Parallelism under about 1.5x means the plan is still mostly linear.
   - A warning that a `could` node is needed by a `must` node means the low-priority work is really urgent. The script treats it as `must`. Either accept that and raise it, or cut the dependency so the `must` work does not wait on it.
   - "All must work placed by wave N" is the number that matters most. If it is too late, move work out of `must`, or remove `must` nodes' dependencies on lower-priority work.
   - A warning about S nodes in a hard chain on the same files means they should be one node. Merge them.

## 3. Stress-test

Read `references/blindspots.md`. Scale the effort to the plan: for a few nodes, the checklist and a short premortem are enough. For a plan of about six nodes or more, or one that touches shared core code, do all three:

1. Go through the checklist and either cover each category or mark it N/A with a reason.
2. Write a premortem in `reviews/premortem.md`: assume the roadmap failed, list the five most likely reasons, and turn each into a mitigation, a new node or a spike.
3. Spawn a reviewer agent with fresh context, using the prompt in `references/blindspots.md`. Give it only the roadmap directory and the repo, not your reasoning, because a reviewer that sees your reasoning tends to agree with it. It checks only the three areas where errors change the plan's shape: contracts against the real code, owned paths around shared files, and dependency edges. Save the result in `reviews/adversarial.md` and apply what holds up.

Show the user the plan summary and get their approval before execution. This is the cheapest point to change direction. Quote the waves, milestones and critical path from a fresh `plan.py status` run instead of restating them from memory, because the script is the source of truth and a plan edited after the last run drifts from what you remember. List the main risks and every assumption the user should confirm.

## 4. Contracts

The first wave freezes contracts: types, signatures, schemas, event names, stub or fake implementations, and contract tests that any real implementation must pass. When a contract-freezing node is done, set the contract's `status: frozen` and bump its version.

Contracts are the gate that matters most. A wrong contract wastes every parallel branch built on it, so stop for user review after the contract wave unless the user said not to.

## 5. Schedule

`plan.py status` prints the waves. Waves are a forecast; execution always asks the script what is ready now. Mark nodes that need a human review afterwards with `gate: true`.

The scheduler fills each wave by priority first and critical path second, so `must` work never waits behind `could` work, and `could` nodes use the slots that are left. Use `--upto must` to see the shortest plan that reaches the goal, and `--upto later` to include parked work.

## 6. Execute

Read `references/orchestration.md` before this step. In short:

1. `plan.py <root> verify` closes todo nodes whose acceptance already holds. Then `plan.py <root> ready --json` lists the nodes to start.
2. Set each one to `status: active` and commit that. The orchestrator is the only writer of `status`.
3. Spawn one agent per node with `isolation: worktree`, using `templates/worker-prompt.md` and the model the script suggests. Spawn them in one message so they run at the same time. Each worker first checks whether its work already exists, then builds and opens one pull request against the node's target branch (`target` in `ready --json`, or the main branch when there is no branch policy).
4. Each pull request gets a fresh-context review (the pr-review skill), passes the repo's checks, and goes to the maintainer for approval. Agents do not approve their own work. A node is `done` when its pull request merges. Run the curator (phase 7) at checkpoints.
5. Stop at gates. Then go back to step 1.

One pull request per node is the default, because every piece of work then merges on its own and nothing waits for a large integration branch. Use a single integration branch only when the user asks for it.

For long roadmaps, `scripts/wave.workflow.js` runs one wave as a Workflow (fan-out plus curator), driven by the `ready --json` output.

## 7. Curate (after every wave)

Read `references/memory.md`. One curator pass per wave:

- Read the new `outcome.md` files.
- Promote lasting code rules to nested `CLAUDE.md` files next to the code they apply to. Promote decisions to the repo's decision records.
- Turn rules that a test, type or lint rule can enforce into new nodes, instead of prose.
- Resolve contract change requests: accept (bump the version, list affected nodes) or reject (tell the requesting node to adapt).
- Update the briefs of downstream nodes whose upstream outcome deviated from the plan.
- Record estimate against actual in `<roadmaps-dir>/CALIBRATION.md`.

Write a short report to `reviews/wave-<n>.md` and tell the user what changed.

## Change: additions during development

New ideas arrive while waves are running. That is normal, and the graph makes it cheap: a new node only has to fit around the nodes it touches, not around the whole list. Read `references/changes.md` for the full procedure. In short:

1. **Triage.** Decide with the user whether the idea belongs in this roadmap, in a separate roadmap, or in `<root>/inbox.md` to look at later, and give it a priority. Base it on evidence: security problems seen in the wild, data loss, broken production behavior and blocked users are `must`. Feature ideas without such evidence are usually `should` or lower. A new `must` pushes back the must milestone, so say what it costs. If it changes the outcome in `GOAL.md`, it is a scope change, so say that plainly before adding it.
2. **Write the node.** Use the same brief template and rubric, and set `added: <date>`.
3. **Check the impact.** Run `plan.py <root> impact <id>`. It shows whether the node can start now, which nodes it overlaps (including running ones), which contracts it uses, and how it changes the critical path and the number of waves.
4. **Fit it in without disturbing running work.** Never edit the brief of an active node. If the new work changes what an active node is building, let that node finish against its brief and add a follow-up node with a `hard` dependency on it. If the new work needs a contract to change, write a change request; do not edit a frozen contract.
5. **Start it.** If `impact` says it can start now and nothing active overlaps, spawn it right away instead of waiting for the wave to end.

## 8. Close

When every node is done or dropped: check that `GOAL.md` acceptance holds, move lasting decisions out of the roadmap, make sure nested `CLAUDE.md` files hold the lasting learnings, and add a final calibration entry. Leave the roadmap directory in place as history, or delete it if the user prefers. Its outcomes should no longer be needed by anyone.

## Writing the files

- Write for an agent that has none of this conversation. A brief must make sense on its own together with the files from `plan.py context`.
- Keep `GOAL.md` and the roadmap `CLAUDE.md` short. They load for every node.
- Outcomes describe what was built, where the code is, deviations from the contract, stubs left behind, and gotchas. They do not retell the work.

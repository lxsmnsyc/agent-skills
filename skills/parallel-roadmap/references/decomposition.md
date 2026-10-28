# Decomposition

How to cut work into nodes that run in parallel, are the right size, and fit an agent's context.

## Contents

- Sizing rubric
- What the scores trigger
- Split strategies
- When not to split
- Stories
- Priority
- Shared files and global counters
- Choosing the model

## Sizing rubric

Score every node on these six questions. Write the scores in the brief's "Sizing" section, so a reviewer can disagree with a specific score rather than with a gut feeling.

| Question | Low | Medium | High |
| --- | --- | --- | --- |
| Uncertainty: has this been done before? | same pattern exists in this repo | known pattern, new to this repo | novel, or depends on an unverified library or platform behavior |
| Coupling: how many other nodes does it touch? | 0-1 dependencies, no owned-path overlap | 2-3 dependencies | 4+ dependencies, or overlaps another node |
| Blast radius: does it change shared code? | only its own files | one shared file, append-only | core types, registries, config, schema |
| Verifiability: how will we know it works? | an automated test proves it | a manual check or a benchmark | subjective, or needs real users or real load |
| Size: files and lines changed | 1-3 files, under 200 lines | 4-10 files, under 800 lines | more |
| Context load: from `plan.py context` plus the code it must read | under 8k tokens | 8-20k | over 20k |

Map to a size class:

- **S**: everything low, or at most one medium.
- **M**: mostly medium, no high.
- **L**: one high, or size medium with uncertainty medium.
- **XL**: two or more highs, or size high. XL is not schedulable; split it.

Size is about how hard the node is for an agent to finish in one session without losing track, not about calendar time.

## What the scores trigger

- **High uncertainty**: put a spike node first. The spike answers one question, has a time box, and writes its answer to `outcome.md`. The build node has a `hard` dependency on the spike. A spike can also produce a contract.
- **High coupling**: look for a seam. Usually a contract can replace several edges.
- **High blast radius**: move the shared change into its own early node, ideally in the contract wave, so later nodes only append.
- **Low verifiability**: add a node that writes the acceptance test or the benchmark harness first, or set `gate: true` so a human checks it.
- **Context over budget**: split the node, or ask the upstream nodes for tighter outcomes. A node that needs 40k tokens of background will make mistakes no matter how small its diff is.

## Split strategies

Pick the one that matches the shape of the work.

1. **Vertical slice.** Split by user-visible capability, each one full stack. Good default for features.
2. **Seam extraction.** Pull the shared interface out into a contract node. Every consumer then depends on the contract, not on each other.
3. **Spike, then build.** Separate finding out from building. The spike is small and runs early.
4. **Expand, migrate, contract.** For refactors: add the new API next to the old one (one node), migrate callers area by area (one node per area, all parallel), then remove the old API (one node, `hard` on all migrations). This turns a serial refactor into one wide wave.
5. **Test first.** One node writes the acceptance tests against the contract. Implementation nodes then have a fixed target, and the tests catch drift between parallel implementations.
6. **Measure, then change.** For performance work: one node builds the measurement and records the baseline, then each optimization is its own node that reports the before and after numbers. Optimizations in different areas run in parallel.
7. **Per area.** When the same change has to be made in many places (renames, API migrations, converted data), split by directory.

## When not to split

A node is one pull request. Every node has a fixed cost: loading context, setting up a worktree, writing an outcome, a review, a merge, and the checks. Splitting only pays when the parts can run at the same time, or when one part is risky enough to ship alone. Merge nodes when:

- Both are S and own the same files.
- One would take less effort than writing its brief.
- They form a `hard` chain of S nodes in the same module. One M node is cheaper than three S nodes in a row. `plan.py check` warns about this.
- They are consecutive steps of one design document that touch the same files. Keep the steps as a checklist inside one brief, unless a step needs to ship and be measured before the next one starts.
- The only reason to split is tidiness. A split that does not let two agents work at the same time, and does not reduce risk, is pure overhead.

Balance waves too. A wave takes as long as its slowest node, so if one L sits in a wave of S nodes, split the L first.

## Stories

A story groups the nodes of one feature on one branch (see "Stories" in `SKILL.md` for the fields). Children follow the same rules as any node. Each child is one reviewable pull request, sized by the rubric, and the split strategies above apply inside a story.

Make a story when:

- The user asked for one feature ("add a sign-in form") and it needs two or more M nodes.
- The parts are not useful to users alone. Shipping them one by one would need feature flags or leave dead code on the main branch.
- The maintainer wants to review the feature as a whole.

Do not make a story when:

- One node is enough. A story with one child is a node with an extra pull request.
- Each part is useful on its own. Separate nodes reach users sooner.
- The work is a refactor across the codebase. Expand, migrate, contract keeps each step on the main branch, so a long-lived branch only adds conflicts.

A story branch lives as long as its slowest child, and the main branch moves on meanwhile. Keep stories to a few waves. Mark a child `early` when other work needs it on the parent branch. Typical cases are hot file splits, fixes to bugs on the base, dependency bumps, and contracts used outside the story. Sizing the story node itself: its size is the whole feature, and is only used while it is an outline. Once it has children, `plan.py` counts it as one small step, the story pull request.

## Priority

Size says how hard a node is. Priority says how much the project needs it. Weigh both: a high-value S node is the best deal in the plan, and a low-value XL node is the first thing to cut.

| Priority | Meaning | Test |
| --- | --- | --- |
| `must` | needed now | The goal in GOAL.md is not reached without it. |
| `should` | important | The goal is reached without it, but clearly worse. |
| `could` | good to have | Worth doing when an agent is free. |
| `later` | parked | Not now. Stays in the plan so it is not lost, but is never scheduled. |

How to set it:

1. Start from the goal, not from the node. List what the goal needs; those nodes and everything they need are `must`.
2. Everything else starts as `should` and has to argue its way up.
3. Look at value against size. High value and S or M: keep the priority. Low value and L: lower it, or split off the valuable part.
4. Propose the priorities, then show the user the `must` list and the must line ("all must work placed by wave N"). The user decides, because value depends on things the code does not show: users, deadlines, other projects.

What the script does with it:

- **Promotion.** A node is at least as urgent as the most urgent node that needs it. If a `must` node depends on a `could` node, the `could` node is scheduled as `must`, and `check` warns. Decide whether the dependency is real; often the `must` node only needs a contract, not the whole lower-priority node.
- **Ordering.** Each wave fills with `must` work first, then `should`, then `could`. Lower-priority work uses spare slots, so it costs little calendar time while there is spare concurrency.
- **Cut lines.** `--upto must` schedules only the must work and shows the shortest path to the goal. `later` nodes are only scheduled with `--upto later`.
- **Re-prioritize at checkpoints.** Outcomes change what is valuable. The curator lists `should` and `could` nodes that now look like `must` or `later`, and the user decides.

## Verify commands

A `verify` command lets `plan.py verify` and the worker check the acceptance without judgment. It must test behavior: run the node's tests, call the endpoint, run the benchmark against its budget. A command that only checks that a file exists passes on an empty stub and closes nodes that were never built.

## Shared files and global counters

These are where parallel branches collide. Handle them in the plan, not at merge time.

### Split hot files by feature first

When two or more nodes would edit the same large file, the best fix is usually to split that file before the fan-out, so each later node owns its own module. `plan.py check` warns when four or more open nodes touch one file, and `plan.py status` prints the merge order for files shared within a wave. Add one early node that:

- Moves code into one module per feature (one file per job, per monster, per route, per event kind), and leaves the old file importing or re-exporting them so callers do not change.
- Changes no behavior. The existing tests pass unchanged. Nothing else goes into this pull request, so the review is a quick check that code only moved.
- Adds a registration point when the file is a list of features (a registry, a switch over kinds, a table). New features then add a file and one registration line, or are discovered automatically.

The later nodes depend on the split node with a `hard` dependency and own only their new modules. This also helps every roadmap after this one, since the file stops being a hot spot.

Do not split when the file is only shared within this roadmap and briefly, when the move would make a large diff unrelated to the goal, or when the repo keeps related code together on purpose. Then run the nodes in sequence, or keep them in one wave with `shared:` and plan the merge order. Splitting changes the code layout, so propose it to the user and let them decide.

- **Registries** (routes, plugin lists, barrel exports): prefer one file per feature with discovery, or make the registry change part of the contract wave so later nodes only append one line.
- **Migrations, ADR numbers, numbered steps**: reserve numbers in the brief with `reserves:`. `plan.py check` fails on duplicates. If numbers cannot be known in advance, have workers use a placeholder name and let the orchestrator assign numbers in merge order.
- **Generated files**: never commit generated output from a worker branch. Regenerate once after merging.
- **The plan document itself**: workers write only inside their own `nodes/<id>/` folder. Only the orchestrator edits `status` fields, contracts and other shared roadmap files.
- **Lockfiles and dependency manifests**: if a node adds a dependency, mark it in the brief. Two nodes adding dependencies in the same wave will conflict in the lockfile; merge them one at a time and regenerate the lockfile.

## Choosing the model

`plan.py` suggests a model per node: S and M use `sonnet`; L and spikes use `opus`. Override with `model:` in the brief when the work needs it, for example an S node that edits subtle concurrency code. Wide waves of S nodes on a cheaper model cut cost a lot without hurting quality, because S nodes are well specified by definition.

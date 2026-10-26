# Memory

How context flows between nodes during a roadmap, and how learnings outlive it.

## Contents

- Three kinds of context
- Context layers per agent
- Node lifecycle: brief, log, outcome
- Where long-term memory lives
- The curator
- Calibration

## Three kinds of context

Keep these apart. Mixing them is how context grows until agents lose track.

- **Contract (what)**: types, signatures, schemas, formats. Precise. Checked by tests where possible. Lives in `contracts/`.
- **Decision (why)**: "chose X over Y because Z". Rarely needed, but expensive when missing, because agents re-open settled questions or undo them. Lives in the repo's decision records.
- **State (where)**: status, what is stubbed, which branch. Short lived. Lives in the brief's `status` field and the outcome.

## Context layers per agent

A worker loads only what `plan.py context <id>` lists:

- **L0, always**: `GOAL.md` and the roadmap `CLAUDE.md`. Keep both short, because every agent pays for them.
- **L1, the node**: its own `brief.md`, and its `log.md` when resuming.
- **L2, direct dependencies only**: the contracts it uses or provides, and the `outcome.md` of each `hard` or `behavior` dependency.
- **L3, on demand**: code, decision records, research, linked from the brief. The agent opens these when it needs them. They are not preloaded.

L2 stops at direct dependencies on purpose. If a node two steps up matters, the direct parent's outcome should say so. That keeps context flat no matter how deep the graph gets.

When L0 + L1 + L2 goes over the budget, fix the plan, not the agent: split the node, or tighten the upstream outcomes.

## Node lifecycle: brief, log, outcome

- `brief.md` is written by the planner before the node starts. Only the orchestrator changes it afterwards, and never while the node is active.
- `log.md` is the worker's own scratch space: what it tried, what failed, what it is unsure about. Append only. No other node reads it. It exists so a resumed or replacement worker can continue, and for debugging.
- `outcome.md` is written by the worker as its last step, while it still has the full context. It is the only thing that flows downstream, so it must stand alone:
  - what was built and where (paths, public names)
  - deviations from the brief or contract, and why
  - stubs or fakes left in place, and what replaces them
  - gotchas a later node will hit
  - proposed learnings for the curator (rules about the code, each with its reason)
  - actual size against the estimate

Writing the outcome at the end is deliberate compaction, done by the agent that knows what mattered. It is far better than compaction that happens later by accident.

## Where long-term memory lives

Sort by how long it should live:

- **Lasting rules about the code** go into a nested `CLAUDE.md` next to that code, for example `server/store/CLAUDE.md`: "Migrations must be idempotent, because restore replays them." Claude Code loads a nested `CLAUDE.md` when an agent works on files in that folder, so the rule reaches exactly the agents that need it, with no search. Every worktree gets it because it is committed.
- **Decisions** go into the repo's decision records (ADRs or similar). During the roadmap, a draft can live in the node folder; the curator moves it.
- **Roadmap state** (goal, contracts, nodes, reviews) lives in `<root>`. A finished node's folder is archived once nothing open depends on it (curator step 9), so a roadmap that runs for months keeps only the work in flight and its direct inputs.
- **Calibration** lives in `<roadmaps-dir>/CALIBRATION.md` and is shared by all roadmaps in the repo.

Rules for nested `CLAUDE.md` files:

- Keep each one short. It loads whenever an agent touches that folder, so every extra line costs every agent.
- One rule per bullet, with its reason. No history, no narrative, no dates.
- If a test, type, assertion or lint rule can enforce the rule, add a node to do that, and delete the prose once it lands. Code cannot go stale silently; prose can.
- When a rule turns out wrong, delete it. Wrong memory is worse than none.

Before writing a nested `CLAUDE.md`, check whether the repo already uses another convention for this (`AGENTS.md`, module READMEs). Follow the repo.

## The curator

Run one curator pass at each checkpoint (after a wave, or after a few nodes in rolling mode). It is one agent, or the orchestrator itself. It:

1. Reads each new `outcome.md`.
2. Promotes proposed learnings: to a nested `CLAUDE.md` if lasting, to a new enforcement node if checkable, or nowhere if it only mattered once.
3. Moves decisions into the repo's decision records.
4. Resolves contract change requests (see `orchestration.md`).
5. Runs `plan.py <root> refine` and breaks the outline nodes it lists into full briefs, using what this wave's outcomes taught. An outline can become several nodes, or turn out to be unnecessary.
6. Updates downstream briefs whose upstream outcome deviated from the plan, before those nodes start.
7. Deletes or corrects memory that the new outcomes proved wrong. Check that each rule still matches the code it describes.
8. Appends calibration entries.
9. Archives finished nodes: `plan.py <root> archive` lists done nodes that no open node depends on. Once their learnings, decisions and calibration are recorded, `--apply` removes their folders and adds one line each to `archive.md` (title, pull request, milestone). `plan.py` still counts them as done, and their full text stays in git history. The first time in a roadmap, show the user the list before applying. The same command lists frozen contracts that no open node uses; remove them when the code is the better reference.
10. Lists nodes whose priority looks wrong after this wave, and inbox items worth a node, for the user to decide.
11. Writes `reviews/wave-<n>.md`: what landed, what changed in the plan, what it learned, and the current must line (the wave by which all must work is placed) and the progress of each milestone.

## Calibration

Each outcome records estimated size against actual (turns or tokens if known, rework, contract changes, surprises). The curator appends one line per node to `CALIBRATION.md`:

```
2026-10-26 perf-batch/frame-writer est M actual L: byte-equality test needed a fixture generator
```

After a few roadmaps, look for patterns ("nodes touching server/zone run one size over") and add them to the sizing rubric as repo-specific notes at the top of `CALIBRATION.md`. The planner reads those notes in the decompose phase.

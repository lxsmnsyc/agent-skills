---
branches:
  # Leave this empty when every pull request targets one branch.
  # For gitflow-style repos, fill it from pr-review's branch_policy.py, for example:
  # feature: dev
  # fix: dev
  # hotfix: main
  # promote: dev -> next -> main
---

# <Roadmap title>

## Outcome

<What is true when this roadmap is done. One short paragraph. Measurable where possible.>

## Acceptance

- <A check that proves the outcome, ideally a command.>

## Priorities

- must: <what "needed now" means for this roadmap, e.g. "required for the 1.0 release">
- should: <important, but the outcome can be reached without it>
- could: <worth doing when agents are free>
- later: <parked; listed so it is not lost>

## Constraints

- <Compatibility, performance budget, deadlines, things that must not change.>

## Non-goals

- <What this roadmap deliberately does not do.>

## Verification

- Fast check (safe to run in parallel worktrees): `<command>`
- Full check (run after merging, at checkpoints): `<command>` (<duration>, <shared resources it needs>)

## Numbered resources

- <Global counters parallel branches can collide on, and how they are assigned. Example: "Migrations: server/store/migrations/000NN_*.sql, reserved per node with `reserves: [migration 000NN]`.">

## Sources

- <Links to the proposals, ADRs or documents this roadmap was built from.>

## Coverage

Only for roadmaps imported from existing documents. One line per source step:

- <source step, e.g. "ADR 0057 step 4"> -> <node id | inbox: reason | built: commit or PR | dropped: reason>

## Open questions

- <Questions still waiting on the user, with the nodes they block.>

## Gates

- <Default gates, and any the user waived.>

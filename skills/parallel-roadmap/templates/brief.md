---
id: <id, same as the folder name>
title: <short title>
status: todo            # todo | active | done | released | dropped (only the orchestrator changes this)
priority: should        # must (needed now) | should (important, can ship without) | could (when capacity is free) | later (parked)
type: feature           # feature | fix | hotfix | refactor | docs | chore | release | spike | contract
outline: false          # true for far-off work that is not broken into a brief yet: goal, priority, rough deps and size only
milestone:              # optional group from the milestones list in GOAL.md, e.g. a quarter or a release. Required on release nodes that publish from one branch
target:                 # branch the pull request targets; empty means the branch policy for this type
from:                   # release nodes only: the branch being promoted (target is where it goes)
size: M                 # S | M | L | XL (XL must be split)
spike: false            # true for nodes that answer a question instead of shipping code
verify:                 # optional command run from the repo root; exit 0 means the acceptance holds. Test behavior (run the tests, call the code), not file existence
exclusive: []           # resources only one node may use at a time, e.g. [loadtest, db-container]
fulfilled_by:           # set when the work already exists: commit, PR or node id
gate: false             # true when a human must review the result before dependents start
added:                  # date, only for nodes added after the plan was approved
owns:
  - <path or glob this node edits>
shared:
  - <shared file this node appends to, if any>
reserves: []            # e.g. [migration 00043, adr 0067]
provides: []            # contracts this node freezes or implements
depends_on:
  - on: <node id>
    kind: contract      # contract | behavior | hard
    via: <contract name, required for contract and behavior>
    why: <required for hard: why a frozen interface is not enough>
---

# <title>

## Goal

<What this node delivers, in two or three sentences. Enough for an agent with no other context.>

## Context

<Only what the worker cannot get from GOAL.md, the contracts and dependency outcomes. Link code and documents (L3) instead of pasting them.>

- Source: <link to the proposal, ADR or paragraph this came from>

## Steps

<Optional. When the work follows a design document with ordered steps that touch the same files, list them here as a checklist instead of making one node per step. Split a step into its own node only when it must ship and be measured before the next one starts.>

- [ ] <step>

## Acceptance

- [ ] <Observable result, checked by a command where possible.>
- [ ] Fast check passes: `<command>`

## Sizing

<One line for S and M nodes: the main reason for the size. For L, list the rubric scores that are not low.>

## Notes for the worker

- <Known traps, decisions already made, things not to do.>

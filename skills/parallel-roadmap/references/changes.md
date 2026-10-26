# Changes during development

Ideas, bug reports and scope changes arrive while nodes are running. A graph handles them better than a list: a new node only has to fit around the nodes it touches. The goal of this procedure is to add work quickly without breaking work that is already running.

## 1. Capture

When the user mentions a new idea mid-roadmap, write it down first, before discussing it. Append one line to `<root>/inbox.md`:

```
- 2026-10-26: OAuth login with GitHub (user, during wave 2)
```

This keeps the idea safe even if the conversation moves on. Then triage it.

## 2. Triage

Decide with the user which of these it is:

- **Part of this roadmap**: it serves the outcome in `GOAL.md`. Add a node now with a priority (next section).
- **Scope change**: it changes the outcome itself. Say so plainly, update `GOAL.md` with the user's agreement, and add nodes.
- **Separate roadmap**: it is its own goal. Note it in the inbox with a pointer, or start a new roadmap folder.
- **Later**: leave it in the inbox. The curator lists inbox items at each checkpoint, so they are not forgotten.
- **Bug in finished work**: add a fix node with a `hard` dependency on the node that built it.

Then set the priority. Ask the user one question: "Is the goal incomplete without this?" Yes means `must`. "It makes the goal much better" means `should`. "Nice to have" means `could`. "Not now" means `later`, which keeps it in the plan without scheduling it.

Base the priority on evidence, not on how new the idea is. Security problems seen in the wild, data loss, broken production behavior and blocked users are `must` even when they arrive mid-roadmap, because the goal is not really reached while they stand. Feature ideas without that kind of evidence usually feel more urgent than they are because they are new; most of them are `should`, `could` or `later`.

`plan.py impact` shows how a new `must` moves the must line. Tell the user that cost.

## 3. Write the node

Use the brief template and the sizing rubric, the same as during planning. Set `added: <date>`. Run the blindspot checklist on this node only.

An idea for far-off work can go in as an `outline: true` node with a milestone: it is then on the roadmap and in the forecast without a full brief yet, and gets refined when it comes within the horizon.

Small additions still get a brief. The brief is what lets the node run in parallel without the user explaining it again to a worker.

## 4. Check the impact

```
python3 <skill>/scripts/plan.py <root> impact <id>
```

It reports:

- whether the node can start now, or which nodes it waits on
- owned-path overlaps with other nodes, marked when the other node is running
- contracts it uses or provides, with their status
- the nodes it blocks
- the critical path and the number of waves with and without it

Read it like this:

- **Can start now, no overlap with active nodes**: start it right away. In rolling mode it does not need to wait for anything.
- **Overlaps an active node**: do not start it yet. Either narrow its owned paths so they no longer overlap, or make it depend on the active node (`hard`, with a `why`).
- **Needs a draft contract**: it waits for that contract, like every other consumer.
- **Needs a frozen contract to change**: write a change request (see `orchestration.md`). Do not edit the frozen contract.
- **Lengthens the critical path or moves the must line**: tell the user the cost ("this pushes the must work from wave 3 to wave 4"), and look for a split that keeps it off the path, or a lower priority.
- **Low priority but needed by a must node**: the script promotes it. Decide whether the dependency is real.

## 5. Never disturb active nodes

An active node's worker read its brief when it started. Editing that brief now changes nothing for the worker and makes the record wrong. Instead:

- If the new work changes what an active node is building, let the node finish. Add a follow-up node with a `hard` dependency on it that makes the change.
- If the change makes an active node pointless, stop that worker, set the node to `dropped`, and write why in its outcome.

Briefs of nodes that have not started can be edited freely.

## 6. Track scope growth

Nodes with `added:` set are mid-roadmap additions. At each checkpoint the curator counts them and their size points against the original plan, and writes the number in the wave report. Growth is fine when it is chosen. This makes sure it is visible.

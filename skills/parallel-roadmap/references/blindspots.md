# Blindspots

Plans fail in the places nobody looked. This file has three tools: a checklist of categories, a premortem, and a fresh-context reviewer. Use all three before execution, and the checklist again whenever a node is added mid-roadmap.

## Checklist

For each category, either point to the node that covers it or write "N/A" with a reason in `reviews/checklist.md`. "Not thought about" is not N/A.

- **Data and migrations**: schema changes, backfills, data written by the old code that the new code must read, rollback of a migration.
- **Compatibility**: public APIs, file formats, protocol versions, saved state, config files, plugins or mods written by others.
- **Auth and permissions**: who may call the new thing, new permission names, audit logging.
- **Failure modes**: errors, timeouts, partial failure, retries, idempotency, what the user sees when it breaks.
- **Concurrency**: races, ordering, locks, two requests at once, two tabs, two servers.
- **Limits**: large inputs, empty inputs, many users, slow networks, memory.
- **Security**: untrusted input, injection, secrets, new attack surface.
- **Observability**: logs, metrics, how to tell in production that it works.
- **Performance**: baseline, budget, how it is measured, which benchmark proves it.
- **Testing**: unit, integration, end to end; what the contract tests check; whether the checks can run in parallel worktrees.
- **Local files**: gitignored files the checks need (such as `.env`), listed in `.worktreeinclude` so new worktrees get a copy.
- **Developer experience**: error messages, docs, types, examples, generated reference docs.
- **Rollout**: feature flags, staged release, how to turn it off.
- **Cleanup**: stubs left behind, old code paths to remove, temporary flags.
- **Coverage** (imported plans): every step of the source documents maps to a node, an inbox entry, already built work, or an explicit drop, in `GOAL.md` under "Coverage".
- **Dependencies**: new libraries, licenses, versions, maintenance status.

## Premortem

Write `reviews/premortem.md`:

> It is some weeks from now. The roadmap failed or shipped late. Why?

List the five most likely reasons. Be specific to this repo and plan, not generic ("the frame writer's byte layout differs from the old path and the client misreads move events", not "bugs"). For each reason, write what in the plan changes: a new node, a spike, a stronger acceptance criterion, a contract test, a gate, or "accept the risk" with a reason.

## Fresh-context reviewer

Spawn one agent. Give it the roadmap directory and access to the repo, and nothing else from this conversation.

Keep it on the risky parts. A review of the whole plan reads the whole repo and takes many minutes, while the findings that change a plan's shape come from three places: contracts, shared files and dependency edges. Smaller problems (a wrong test path, a size off by one class) get caught later by the worker's verify step and by pull request review.

Prompt:

```
Review the roadmap in <root>. You did not write it. Your job is to find what is wrong with it, not to approve it. Stay inside the three areas below and do not review anything else.

Run `python3 <skill>/scripts/plan.py <root> status` first.

1. Contracts in <root>/contracts/. Compare each one with the real code it describes or replaces. Report types, signatures or formats that do not match the code, and contracts too vague to build two sides against.
2. Shared files. For the files that more than one node is likely to edit (registries, config, core modules, migrations), check the real code and report nodes whose owned paths miss a file they will have to change.
3. Dependency edges. Report `hard` dependencies that could start from a frozen contract, `contract` dependencies that really need finished behavior, and missing edges between nodes that change the same function.

Read only the code needed to check these. Report at most 8 findings, ranked by how much damage each would do. For each: the node or contract, the problem, the evidence (a file path and line, or a quote), and a fix.
```

Save the answer to `reviews/adversarial.md`. Check each finding yourself before acting on it, since the reviewer can also be wrong. Note the ones you rejected and why, so the next reviewer does not raise them again.

## When to repeat

- A node is added mid-roadmap: run the checklist on that node only.
- A contract change request is accepted: rerun the reviewer on the affected nodes.
- A wave finished with surprises: add a line to the premortem saying what was missed and why.

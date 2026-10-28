# Evidence per axis

Measure first, then argue. Every command here only reads, unless it says otherwise. Save long output under `<dir>/evidence/` and cite the file.

## Device

What the machine has:

```bash
python3 <skills>/pr-author/scripts/capacity.py --json       # free memory, CPU load, disk, recommended worktrees
df -h .                                                       # free disk where the repo lives
sysctl -n hw.memsize hw.ncpu 2>/dev/null || nproc; free -m    # total RAM and cores (macOS, Linux)
system_profiler SPDisplaysDataType 2>/dev/null | head -20     # GPU on macOS; nvidia-smi on Linux
```

What the work needs:

- Repo and dependencies: `du -sh .git node_modules target .venv 2>/dev/null`. A new worktree usually needs its own dependency install, so multiply by the number of parallel worktrees.
- Build output and caches: the size of `dist/`, `target/`, `.next/` and the like after the last build.
- Running services: a dev server, a database container, a browser for end-to-end tests. Check `docker stats --no-stream` or the process list when they are already running.
- Models and datasets: the file size of the weights or data, and RAM peak from the model card or a short sample run.

Peak RAM of one command: `/usr/bin/time -l <cmd>` on macOS (maximum resident set size), `/usr/bin/time -v <cmd>` on Linux. Ask the user before running anything that takes more than a minute or installs something.

## Time

- `CALIBRATION.md` in the roadmaps folder: past estimates against actual time per node size. The best source when it exists.
- Git history for similar past work: `git log --since=... --stat` around comparable features, and how long their pull requests stayed open.
- Check duration: how long the project's checks take (`time <check command>` when it is short, or from CI logs). Every pull request pays it, and parallel worktrees on one machine slow each other down.
- Waits that no agent can shorten: reviews by people, outside approvals, service quotas, data that arrives later. Ask the user about these.
- When a roadmap exists: `plan.py <root> status` gives the critical path and the number of waves.

## Tokens

- When a roadmap exists: `plan.py <root> context <id>` estimates the context each worker loads. Multiply by turns: a worker reads its context again on every turn.
- Without a roadmap: estimate the files an agent would read, at about 4 characters per token (`wc -c` on them).
- Per node, count: one worker, one review (fresh or self, see parallel-roadmap's `review:` setting), and fix rounds.
- The orchestrator: in one measured run of 33 nodes it used more than half of all tokens, with a median context of about 470k (parallel-roadmap's `references/orchestration.md`). Long runs that keep one orchestrator session pay that again on every turn.
- Prices: use the claude-api skill for current model prices. Do not quote prices from memory.
- The debate itself: record each round in `spend`. A debate that costs more than the savings it can find should be short.

## Prior art

Search before arguing. Give each search a few minutes, not an afternoon.

- Papers: search for the method and the task together, and look for benchmark tables on the same metric. Note the setup (data size, hardware) next to the number, because a result on 8 GPUs says little about a laptop.
- Code: public repos that implement it, their issue trackers (open issues often show where it breaks), and package download counts when picking a dependency.
- The lab's record: `grep -ril` for the method's names across the repo's `docs/`, past `debate.md` files, experiment outcomes (`nodes/*/outcome.md`, `archive.md`) and decision records. Ask the user which other repos hold the lab's past work. A negative result found here can save the whole debate.

Record each finding as a `fact` with `prior-art` evidence: the citation in `source`, what it found in `detail`. Do not cite a paper you have not read the relevant part of.

## When it cannot be measured

Write an `estimate` with its basis in `detail` ("3 similar endpoints took 1 day each, git log"). Then either ask the user, plan a spike, or let the judge rule it `open`. Do not dress a guess up as a measurement.

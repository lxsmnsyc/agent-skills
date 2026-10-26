# agent-skills

Skills for Claude Code and other agents that support the Agent Skills format.

## Skills

- [`parallel-roadmap`](skills/parallel-roadmap/SKILL.md): plan and run a roadmap as a dependency graph, so several agents can work at the same time without blocking each other.
- [`pr-author`](skills/pr-author/SKILL.md): write changes as small pull requests that merge on their own. Works in worktrees when the machine has room, splits bugs found on the base into their own fix PRs, self-reviews with pr-review, and asks before a push would start billed CI.
- [`pr-review`](skills/pr-review/SKILL.md): review a pull request or branch with evidence. Fixes are reproduced on the base and proven on the head, features are checked against the roadmap, checks run locally, and approval goes to the maintainer.
- [`plain-writing`](skills/plain-writing/SKILL.md): rules for short, exact prose that people and agents can both scan, with a checker script and an optional hook for commits and PRs.

## Install

As a Claude Code plugin:

```
/plugin marketplace add lxsmnsyc/agent-skills
/plugin install agent-skills@lxsmnsyc-agent-skills
```

Or copy a skill folder into `~/.claude/skills/` (all projects) or `.claude/skills/` (one project).

## parallel-roadmap

Linear roadmaps make every item wait for the one above it. Most of those waits are not real, because a feature usually needs another feature's interface, not its finished code. This skill:

- breaks a goal into nodes with typed dependencies (`contract`, `behavior`, `hard`), owned file paths, a size and a priority
- freezes shared interfaces first, so dependent work can start against stubs
- schedules nodes into waves with `scripts/plan.py`, which checks the graph, detects file overlaps and number collisions, and reports the critical path
- runs one agent per ready node, each in its own git worktree
- keeps context small: each agent loads the goal, its own brief, and only the contracts and outcomes of its direct dependencies
- moves lasting learnings into nested `CLAUDE.md` files next to the code
- handles ideas added mid-roadmap with an impact check
- orders work by priority (`must`, `should`, `could`, `later`) and reports when the must work is done

`plan.py` needs only Python 3.

```
python3 skills/parallel-roadmap/scripts/plan.py docs/roadmaps/<slug> status
```

## pr-author

- `scripts/capacity.py` recommends how many worktrees the machine can take, from free memory, CPU load and disk.
- `scripts/wt.py` keeps one worktree per branch in `.worktrees/`, hidden from `git status`, and prunes merged ones.
- `scripts/ci_guard.py` reads workflow triggers and repo visibility, and says "ask" when a push to a private repo would start CI.
- Bugs found on the base branch are proven there and fixed in their own PR, so they ship without waiting for the feature.
- A fresh agent reviews each branch with pr-review, for at most two rounds, before the PR goes to the maintainer.

## pr-review

Reviews answer three questions with evidence: does the change work, is it worth what it costs, and does it pass the project's checks.

- Fixes: `scripts/repro.py` runs the reproduction on the base and the head, in worktrees under `.git/review-worktrees/`, and reports `proven`, `not-reproduced`, `not-fixed` or `inconclusive`.
- Features: checked against their roadmap node's acceptance criteria and owned paths. Features with no node get a roadmap proposal for the maintainer instead of an approval.
- Every change: `scripts/checks.py` finds and runs lint, typecheck, build and tests locally, so private repos never start billed CI. `scripts/size_diff.py` measures build size.
- Reviews are posted as comments, never as "request changes". The reviewer never approves. Approval goes to the maintainer, found by `scripts/pr_info.py`.

## plain-writing

Rules for comments, commits, PRs, reviews, docs and roadmap files. `scripts/check_prose.py` flags dashes, stock phrases, common metaphors, wordy phrases, long sentences and size claims without numbers.

The plugin also registers a hook that checks `git commit` messages and `gh pr` and `gh issue` text before they run. It is off by default. Turn it on with an environment variable, for example in `~/.claude/settings.json`:

```json
{ "env": { "PLAIN_WRITING_HOOK": "block" } }
```

`block` stops the command and tells Claude what to fix. `warn` only logs findings.

## License

MIT

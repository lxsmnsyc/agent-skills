# agent-skills

Skills for Claude Code and other agents that support the Agent Skills format.

## Skills

- [`parallel-roadmap`](skills/parallel-roadmap/SKILL.md): plan and run a roadmap as a dependency graph, so several agents can work at the same time without blocking each other.
- [`goal-debate`](skills/goal-debate/SKILL.md): weigh a goal against its cost before planning it. A proponent agent and an opponent agent argue over device, time and token cost, the orchestrator judges each claim with evidence, and the user answers what cannot be measured.
- [`pr-author`](skills/pr-author/SKILL.md): write changes as small pull requests that merge on their own. Works in worktrees when the machine has room, splits bugs found on the base into their own fix PRs, self-reviews with pr-review, and asks before a push would start billed CI.
- [`pr-review`](skills/pr-review/SKILL.md): review a pull request or branch with evidence. Fixes are reproduced on the base and proven on the head, features are checked against the roadmap, checks run locally, and approval goes to the maintainer.
- [`perf-pass`](skills/perf-pass/SKILL.md): profile a finished feature, try several optimizations side by side, and keep the one with the best measured gain for its cost. Runtime for libraries and servers, bundle size for web apps.
- [`changesets`](skills/changesets/SKILL.md): write the changeset for a change. The bump level follows whether the thing existed before; `major` only with the maintainer's approval.
- [`repo-setup`](skills/repo-setup/SKILL.md): set up a new or old npm library repo: pnpm, changesets, tsdown, vitest, oxlint and oxfmt. Adds a check workflow and a release workflow with trusted publishing.
- [`security-fix`](skills/security-fix/SKILL.md): fix a vulnerability on a branch that is never pushed. The fix goes public when CI publishes the release, so npm provenance stays.
- [`ts-style`](skills/ts-style/SKILL.md): style rules for `.ts` and `.js` code. for-of loops instead of callback Array methods, function declarations, and the repo's linter after each edit.
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
- plans long roadmaps in layers: near work as full briefs, far work as outline nodes grouped into milestones, refined as it comes within reach
- orders work by priority (`must`, `should`, `could`, `later`) and reports when the must work is done
- tracks token spend per node against a `budget:` in `GOAL.md`, with a forecast at the current rate
- runs `experiment` nodes against a hypothesis fixed by goal-debate, gated until the user sees the result

`plan.py` needs only Python 3.

```
python3 skills/parallel-roadmap/scripts/plan.py docs/roadmaps/<slug> status
```

## goal-debate

A plan breaks a goal into work, but never asks whether the goal in its current shape is worth what it costs. This skill:

- runs a proponent, who proposes and expands the idea, and an opponent with fresh context, who looks for costs and weak points
- weighs every claim on device capability (storage, RAM, compute), time to deliver and token spend, plus up to two axes the plan needs
- has the orchestrator judge each claim, measuring to settle disputes, and send only unmeasurable questions to the user
- keeps every claim, ruling and question in `ledger.json`; `scripts/debate.py` validates it and says when the debate has settled or hit its round cap
- counts prior art (papers, repos, the lab's past attempts) as evidence, and settles feasibility with small proofs capped at 30 minutes and 100k tokens
- fixes the hypothesis, metric and success threshold of a research goal before any run. parallel-roadmap runs it as a gated `experiment` node
- weighs an existing roadmap too, with `cut` claims that drop, park or merge nodes
- ends with `debate.md`: the settled structure, a budget per axis, rejected alternatives and open risks, which parallel-roadmap turns into `GOAL.md`

```
python3 skills/goal-debate/scripts/debate.py docs/roadmaps/<slug>/debate status
```

## pr-author

- `scripts/capacity.py` recommends how many worktrees the machine can take, from free memory, CPU load and disk.
- `scripts/wt.py` keeps one worktree per branch in `.worktrees/`, hidden from `git status`, and prunes merged ones.
- `wt.py prune-merged --agent-worktrees` also sweeps `.claude/worktrees/` left by agents, skipping locked and recently used ones.
- `scripts/ci_guard.py` reads workflow triggers and repo visibility, and says "ask" when a push to a private repo would start CI.
- Bugs found on the base branch are proven there and fixed in their own PR, so they ship without waiting for the feature.
- A fresh agent reviews each branch with pr-review, for at most two rounds, before the PR goes to the maintainer.

## pr-review

Reviews answer three questions with evidence: does the change work, is it worth what it costs, and does it pass the project's checks.

- Fixes: `scripts/repro.py` runs the reproduction on the base and the head, in worktrees under `.git/review-worktrees/`, and reports `proven`, `not-reproduced`, `not-fixed` or `inconclusive`.
- Features: checked against their roadmap node's acceptance criteria and owned paths. Features with no node get a roadmap proposal for the maintainer instead of an approval.
- Every change: `scripts/checks.py` finds and runs lint, typecheck, build and tests locally, so private repos never start billed CI. `scripts/size_diff.py` measures build size.
- Reviews are posted as comments, never as "request changes". The reviewer never approves. Approval goes to the maintainer, found by `scripts/pr_info.py`.

## perf-pass

- Picks the axis (runtime, or size for web apps), measures a baseline with a realistic benchmark, and profiles before changing anything.
- Proposes at least three options from different kinds of fix, tries the promising ones in separate worktrees, and measures them side by side.
- `scripts/bench.py` interleaves runs across checkouts and marks a change as real only when it beats the noise.
- Reports a table with the chosen option and the rejected ones, so measured dead ends are not tried again.

## repo-setup

One setup for every npm library repo the user owns, taken from their newest repos:

- `scripts/audit.py` lists what a repo has and lacks (`ok`, `missing`, `migrate`), and which packages are not on npm yet
- `templates/` holds the workflows, configs and license to copy; tool versions are read from npm at setup time
- new packages get a manual `0.0.0-stage` publish with `--otp`, then trusted publishing on npmjs.com, then `0.1.0` from CI
- GitHub environments only when a release has more than one target, such as npm and the VS Code marketplace
- old repos get one setup pull request through pr-author, and nothing is pushed to a private repo without asking

```
python3 skills/repo-setup/scripts/audit.py <repo>
```

## security-fix

A public pull request or pushed branch reveals a vulnerability before the release that fixes it. A manual `npm publish` hides it, but drops the provenance attestation, and package managers with trust policies then refuse the version. This skill:

- works on a local branch with no upstream, and never opens a pull request
- runs the project's checks locally, because CI does not see the code before the merge
- bumps the version with changesets on the branch, so the push publishes at once instead of opening a version PR
- merges into the branch the release workflow publishes from and pushes it only after the user confirms, and only for a public repo
- checks the new version on the registry for provenance, then reminds the user to publish the advisory

## plain-writing

Rules for comments, commits, PRs, reviews, docs, interface text and roadmap files. `scripts/check_prose.py` flags dashes, stock phrases, common metaphors, wordy phrases, long sentences and size claims without numbers.

The plugin also registers a hook that checks `git commit` messages and `gh pr` and `gh issue` text before they run. It is off by default. Turn it on with an environment variable, for example in `~/.claude/settings.json`:

```json
{ "env": { "PLAIN_WRITING_HOOK": "block" } }
```

`block` stops the command and tells Claude what to fix. `warn` only logs findings.

## License

MIT

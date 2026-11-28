# agent-skills

Skills for Claude Code and other agents that support the Agent Skills format.

## Skills

- [`parallel-roadmap`](skills/parallel-roadmap/SKILL.md): plan and run a roadmap as a dependency graph, so several agents can work at the same time without blocking each other.
- [`goal-debate`](skills/goal-debate/SKILL.md): weigh a goal against its cost before planning it. A proponent agent and an opponent agent argue over device, time and token cost, the orchestrator judges each claim with evidence, and the user answers what cannot be measured.
- [`pr-author`](skills/pr-author/SKILL.md): write changes as small pull requests that merge on their own. Works in worktrees when the machine has room, splits bugs found on the base into their own fix PRs, self-reviews with pr-review, and asks before a push would start billed CI.
- [`pr-review`](skills/pr-review/SKILL.md): review a pull request or branch with evidence. It questions the premise and approach before the lines. Expectations are written before reading the diff, so the reviewer does not share the author's blind spots. Fixes are reproduced on the base and proven on the head, features are checked against the roadmap, checks run locally, and approval goes to the maintainer.
- [`root-cause`](skills/root-cause/SKILL.md): find and prove the cause of a bug, flake or slowdown before anyone fixes it. Ends with a diagnosis that pr-author or a roadmap fix node builds on.
- [`issue-author`](skills/issue-author/SKILL.md): write and open issues a maintainer can act on. Searches for duplicates, follows the repo's templates, and reproduces a bug on every release line the repo still maintains. No issue for a bug only in unmaintained versions, and none for a security problem.
- [`perf-pass`](skills/perf-pass/SKILL.md): profile a finished feature, try several optimizations side by side, and keep the one with the best measured gain for its cost. Runtime for libraries and servers, bundle size for web apps.
- [`changesets`](skills/changesets/SKILL.md): write the changeset for a change. The bump level follows whether the thing existed before; `major` only with the maintainer's approval.
- [`repo-setup`](skills/repo-setup/SKILL.md): set up a new or old npm library repo: pnpm, changesets, tsdown, vitest, oxlint and oxfmt. Adds a check workflow and a release workflow with trusted publishing. Decides where property, model or oracle tests pay off, and finds implicit state machines.
- [`security-fix`](skills/security-fix/SKILL.md): fix a vulnerability on a branch that is never pushed. The fix goes public when CI publishes the release, so npm provenance stays.
- [`ts-style`](skills/ts-style/SKILL.md): style rules for `.ts` and `.js` code. for-of loops instead of callback Array methods, function declarations named with a verb, and the repo's linter after each edit.
- [`plain-writing`](skills/plain-writing/SKILL.md): rules for short, exact prose that people and agents can both scan, with a checker script and an optional hook for commits and PRs.
- [`ui-style`](skills/ui-style/SKILL.md): design rules for interfaces. Let the layout explain instead of secondary labels and descriptions.
- [`landing-page`](skills/landing-page/SKILL.md): rules for landing pages of any product. Show a demo and an animated hero visual (the product at work first, a concept animation when that shows it better, picked from proposed designs), sell the benefit and the difference from competitors, add interaction that shows what the product does, and show real proof of who uses it.
- [`docs-site`](skills/docs-site/SKILL.md): plan, write and maintain a docs site. Each page has one type (tutorial, guide, concept, feature, reference, internals and more) with a fixed template, and a checker verifies page structure, links, orphan pages and reference coverage.

## Install

As a Claude Code plugin:

```
/plugin marketplace add lxsmnsyc/agent-skills
/plugin install agent-skills@lxsmnsyc-agent-skills
```

Or copy a skill folder into `~/.claude/skills/` (all projects) or `.claude/skills/` (one project).

## parallel-roadmap

Linear roadmaps make every item wait for the one above it. Most of those waits are not real, because a feature usually needs another feature's interface, not its finished code. This skill:

- breaks a goal into nodes with typed dependencies (`contract`, `behavior`, `hard`), owned file paths, a size, a priority and a risk estimate
- freezes shared interfaces first, so dependent work can start against stubs
- schedules nodes into waves with `scripts/plan.py`, which checks the graph, detects file overlaps and number collisions, and reports the critical path
- runs one agent per ready node, each in its own git worktree
- ships each node as a pull request, or as one direct commit onto its target when the merge policy lets the orchestrator land it alone (story children on the story branch, small nodes under `merge.mode: auto`)
- keeps context small: each agent loads the goal, its own brief, and only the contracts and outcomes of its direct dependencies
- moves lasting learnings into nested `CLAUDE.md` files next to the code
- handles ideas added mid-roadmap with an impact check
- plans long roadmaps in layers: near work as full briefs, far work as outline nodes grouped into milestones, refined as it comes within reach
- orders work by priority (`must`, `should`, `could`, `later`) and reports when the must work is done
- tracks token spend per node against a `budget:` in `GOAL.md`, with a forecast at the current rate
- runs `experiment` nodes against a hypothesis fixed by goal-debate, gated until the user sees the result
- estimates risk per node and checks it against the built change: high risk gets a fresh review, skips the batch and goes to the maintainer

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
- `wt.py new` and pr-review's `worktrees.py prepare` copy the gitignored files that `.worktreeinclude` names (such as `.env`), as Claude Code does for its own worktrees.
- `wt.py prune-merged --agent-worktrees` also sweeps `.claude/worktrees/` left by agents, skipping locked and recently used ones.
- `scripts/ci_guard.py` reads workflow triggers and repo visibility, and says "ask" when a push to a private repo would start CI.
- Bugs found on the base branch are proven there and fixed in their own PR, so they ship without waiting for the feature.
- `scripts/risk.py` counts the files that use each changed symbol, and flags entry-file exports, migrations, dependency changes and untested files. Each PR gets a Risk block (reach, undo, trade, coverage) with a rating. A high rating means a fresh review and the maintainer.
- A fresh agent reviews each branch with pr-review, for at most two rounds, before the PR goes to the maintainer.

## pr-review

Reviews answer four questions with evidence: is it the right change, does it work, is it worth what it costs, and does it pass the project's checks.

- Premise first: before the diff, the reviewer writes the goal and whether the problem is real. It picks among doing nothing, reusing what exists, the smallest change and a change at another layer. A wrong approach goes at the top of the review, above line-level findings, and nits are dropped when it blocks.
- Fixes: `scripts/repro.py` runs the reproduction on the base and the head, in worktrees under `.git/review-worktrees/`, and reports `proven`, `not-reproduced`, `not-fixed` or `inconclusive`.
- Features: checked against their roadmap node's acceptance criteria and owned paths. Features with no node get a roadmap proposal for the maintainer instead of an approval.
- Blind review: the reviewer writes down what a complete change would include from the claim alone (`pr_info.py --blind`), before it reads the diff, then lists what is missing. `scripts/surface.py` finds docs, flags, env vars and messages outside the diff that still mention what the change removed or changed, and a missing changeset. For medium or high risk, or public API changes, a separate agent tests the docs without seeing the code.
- Every change: `scripts/checks.py` finds and runs lint, typecheck, build and tests locally, so private repos never start billed CI. `--changed <base>` runs each check on the changed files only. `scripts/size_diff.py` measures build size.
- Reviews are posted as comments, never as "request changes". The reviewer never approves. Approval goes to the maintainer, found by `scripts/pr_info.py`.

## root-cause

- Builds one command that goes red on the reported symptom. `scripts/loop.py` runs it many times and calls it `tight`, `slow`, `flaky`, `wrong-failure` or `green`.
- Shrinks the reproduction, ranks 3 to 5 hypotheses that can each be proven false, and probes them, in parallel worktrees when probes are slow.
- Writes a diagnosis: the cause at file and line, the regression test, and fix options with their reach, cost and undo.
- Routes it: a pr-author fix PR, a roadmap fix node, an issue, or security-fix for a vulnerability, which is never written down.
- In parallel-roadmap it runs as a `diagnose` node. `plan.py` warns until the fix node exists.

## issue-author

- Finds the repo that owns the bug, follows its issue templates, `contact_links` and labels, and searches open and closed issues and pull requests before writing.
- `scripts/versions.py` lists release lines from `SECURITY.md` or `SUPPORT.md`, maintenance branches, tags and npm dist-tags, and calls each `maintained`, `likely` or `unmaintained`.
- `scripts/affects.py` runs one reproduction on several refs in worktrees and reports which are affected. A bug that shows only in unmaintained lines gets no issue: the user gets the version to upgrade to.
- A security problem never becomes an issue. In the user's repo it goes to security-fix. In someone else's repo it becomes a private report for the user to send.

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
- `references/testing.md` says which modules need property, model or oracle tests with fast-check, and which need none
- `scripts/scan_states.py` lists flags and status strings that form an implicit state machine, and whether a database stores them
- `references/state-machines.md` says when to fix one in place and when a migration needs the user's approval
- GitHub environments only when a release has more than one target, such as npm and the VS Code marketplace
- old repos get one setup pull request through pr-author, and nothing is pushed to a private repo without asking

```
python3 skills/repo-setup/scripts/audit.py <repo>
```

## security-fix

A public pull request or pushed branch reveals a vulnerability before the release that fixes it. A manual `npm publish` hides it, but drops the provenance attestation, and package managers with trust policies then refuse the version. This skill:

- rewrites the advisory description without exploit details, and keeps the original text in a private advisory comment
- works on a local branch with no upstream, and never opens a pull request
- reproduces the vulnerability with a failing test, then comments on the advisory that it is confirmed
- closes the advisory with a comment that says why when it does not reproduce consistently or does not merit an advisory
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

A second hook checks every write to `.changeset/*.md`. It blocks the write until the agent making it, main session or subagent, has loaded the `changesets` and `plain-writing` skills. It also blocks a changeset with plain-writing errors, a sentence over 25 words, a semicolon or an entry of more than two sentences. A `major` bump asks you to approve the write. Turn it on the same way:

```json
{ "env": { "CHANGESETS_HOOK": "block" } }
```

## landing-page

A landing page that describes the product without selling its benefit does not attract users. This skill:

- requires a demo of the product or its effect: an animation, a sample UI or a snippet that runs
- ranks selling points by what the visitor cares about and how the product differs, gives the main one the hero, and cuts blocks that sell nothing
- shapes each section as a benefit headline, proof, then the feature behind it, and asks for a section on the difference from named alternatives
- holds visible text to a budget (600 words, one-sentence sections, a visual in every section), measured on the built page with `scripts/word_count.py`
- adds playful animation or interaction only when it shows what the product does, and lifts the ui-style rule against idle animation for that
- shows proof of who uses the product only when it clears a strength bar, judged against the main alternative
- has steps for libraries, CLIs, web apps, mobile apps, APIs, physical products and services in `references/product-kinds.md`
- ends with a review checklist for the finished page

## docs-site

Docs are hard to use when one page teaches, instructs, explains and lists options at once. This skill:

- splits the site by what the reader needs: getting started, guides, concepts and reference, plus examples, troubleshooting, migration, changelog and glossary, scaled down for small projects
- gives each page a `type:` in its frontmatter and a template in `templates/` for that type
- defines the feature page (what it is, why, how it works, usage, options, limits, related) and the reference entry (signature, parameters, returns, throws, example)
- separates concepts, which explain what the user observes, from internals pages, which explain the mechanism (such as a compiler's stages) for contributors and list the source paths they cover in `covers:`
- orders each section: concepts by prerequisite (`requires:` in the frontmatter), guides by project stage, and rules for reference, troubleshooting, examples, migration, glossary and internals
- specifies search as a command bar (header button, `/`, Cmd or Ctrl+K) with a build-time index that loads on first open, based on idlip's
- plans for translation from the first page: locale folders, explicit heading ids, interface strings in one file, no text in images
- covers diagrams, doc comments for generated reference, errors that link to their docs, synced tabs, shared content, callouts, voice, screenshots, accessibility and the README's role
- gives a 10-step method for writing one page, starting from the reader's question and the example
- requires examples that run as written and are tested
- audits an existing site for mixed pages, gaps and stale pages before restructuring it
- keeps docs in the same pull request as the code, and covers deprecations, versioned docs and `llms.txt` for agents
- checks pages with `scripts/docs_check.py`: required sections per type, lead sentences, code fence languages, broken links, orphan pages, exports with no reference entry, `covers:` paths that no longer exist, `requires:` entries that are missing, cyclic or out of order, exports with no doc comment, and missing or stale translations

```
python3 skills/docs-site/scripts/docs_check.py website/docs --exports src/index.ts --reference website/docs/reference
```

## License

MIT

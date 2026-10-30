# Orchestration

How to run nodes with several agents at once, ship their work, and keep the plan correct while it runs.

## Contents

- Roles
- One pull request per node
- Stories
- Releasing from one branch
- Rolling and waves
- The loop
- Keeping the orchestrator's context small
- Spawning a worker
- Sequential mode
- Already fulfilled work
- Merging and verification
- Auto-merge
- Direct commits
- Shared and exclusive resources
- Contract change requests
- Gates
- Failure handling
- Running a wave as a Workflow

## Roles

- **Orchestrator**: the main agent in the user's session. It is the only one that edits `status` fields, contracts and other shared roadmap files. A single writer for shared state removes a whole class of conflicts.
- **Workers**: one per node, each in its own git worktree on its own branch (in sequential mode, the worktree is optional). A worker edits its owned paths and its own `nodes/<id>/` folder, and opens one pull request, or none when the node ships as a direct commit.
- **Reviewer**: a fresh-context agent that reviews each pull request (the pr-review skill, if installed), and reviews the plan itself during the stress test.
- **Curator**: runs at checkpoints. See `memory.md`.
- **Maintainer**: the person who approves and merges pull requests. By default the repo owner or the user. Agents never approve their own work.

## One pull request per node

Each node ships as its own pull request against its target branch: the main branch in trunk-based repos, or the branch the policy in `GOAL.md` gives for the node's type in gitflow-style repos (for example features to `dev`). This is the default because it keeps every piece of work mergeable on its own: nothing waits for a large integration branch to be finished. A node that no person reviews on its own (a story child, or small work under `merge.mode: auto`) skips the pull request and lands as one direct commit instead (see "Direct commits"). The rules below hold for both.

What makes this safe:

- The contract wave merges first, so every later pull request builds on frozen interfaces that already exist on the main branch.
- Work that is not ready for users goes behind a feature flag, or stays unreachable until the node that wires it up lands.
- Breaking changes use expand, migrate, contract (see `decomposition.md`), so each step is safe to merge alone.
- `behavior` dependencies build against stubs, so their pull requests merge before the real implementation exists.

On a private repo, pushing a branch can start billed CI runs. Check `gh repo view --json visibility` before the first push. If the repo is private, ask the user whether to push, or to keep branches local, run the checks locally, and merge locally.

A node is `done` when its pull request is merged into its target, or its commit has landed there. Track the pull request number or commit hash in the brief's body (not in frontmatter) or in the outcome.

With several stages (`dev -> next -> main`), work moves on through release nodes: a `type: release` node is one promotion pull request (for example `dev` into `next`), gated for the user. When a release node into the last stage merges, the curator sets the nodes it shipped to `released`. Promotion carries everything that is on the source branch, not only the nodes the release was planned for. So before a release node runs, decide for each other open node targeting the same branch: merge it after the cut, put it behind a feature flag that stays off, or include it in the release on purpose. `plan.py check` lists those nodes as a warning on the release node. When the release node has a `milestone`, `check` also lists the open nodes of that milestone that it does not wait for. Waiting through other nodes counts. So a planned node cannot miss the release.

Hotfix nodes target the released branch directly, and the worker opens the back-merge pull requests into the other stages after the hotfix merges.

## Stories

A story is one feature on its own branch, `feat/<story id>`. Its children are nodes whose `target` in `ready --json` is that branch.

1. **Open the branch.** When the first child becomes ready, create the story branch from the story's target: `git branch feat/<story id> <target>`. Push it, unless the repo is private and the user keeps branches local (see "One pull request per node"). Set the story to `status: active` in the same status commit as the child.
2. **Children.** Each child runs as a normal node: worker, worktree, review, outcome. Its worktree must start from the story branch, so the worker prompt tells it to reset to `<target>` before its first commit. By default a child has `ship: commit` in `ready --json`: it opens no pull request, and the orchestrator lands it on the story branch as one commit (see "Direct commits"), so the story keeps one commit per child. A child with `ship: pr` opens a pull request against the story branch, merged with a merge commit, not a squash. With `merge.stories: auto` (the default), the orchestrator lands a child when `plan.py can-merge` allows it. This holds even when `merge.mode` is `maintainer`, because the maintainer reviews the whole story later. The exclusions still apply: a gated child or one that provides a contract goes to the maintainer.
3. **Early children.** A child with `early: true` targets the story's target, not the story branch, and follows the normal merge rules. After it merges, merge the target into the story branch so later children build on it.
4. **Keep the branch current.** At every checkpoint, merge the story's target into the story branch, and run the fast check there. Conflicts found now are cheap. Conflicts found when the story pull request opens hold up the whole feature.
5. **The story pull request.** When every child is done, `ready --json` lists the story with `"action": "story-pr"`. No worker runs. Open a pull request from the story branch into its target, titled from `pr_title`, and list the children with their outcomes in the description. Spawn one fresh reviewer with the pr-review skill for the whole branch. Then hand it to the maintainer, since `story` is in the default `merge.exclude`. When it merges, set the story to `done`.

Roadmap files written by a child (its outcome and log) reach the main branch only with the story. Curators and siblings read them from the story branch: `git show feat/<story id>:<root>/nodes/<id>/outcome.md`.

Sometimes a child cannot be done on the story branch, for example when it needs a fix that other work needs too. The worker reports this as a blocker. The orchestrator then adds an early child for that part, with the Change procedure.

## Releasing from one branch

Many repos merge every pull request into the main branch and publish from it, with changesets or a tag. Then everything merged ships with the next release, whether it was planned for that release or not. Declare this in `GOAL.md`:

```yaml
milestones: [core, skill, ui]
release:
  publish: changesets     # or tag: what cuts a release
  paths: [packages/**]    # what ships; work outside these paths never waits
  fence: merge            # merge (the default): build now, hold the merge. start: do not start
```

Each release is a `type: release` node with a `milestone`, gated, without `from` or `target`. It ships its own milestone and every earlier milestone that has no release node of its own. So a release on `skill` above ships `core` and `skill`. `plan.py check` warns about open nodes of those milestones that the release does not wait for.

Until the first open release is done, nodes of later milestones that touch the release paths are held:

- `fence: merge`: they can start, but `plan.py can-merge` refuses them with "waits for release <id>". Hand those pull requests to the maintainer with that reason, and in maintainer mode, tell the maintainer to hold them too. Building early keeps the work in parallel, at the cost of a rebase after the release.
- `fence: start`: `plan.py ready` leaves them out until the release is done.

`ready --json` gives `held_by` for each held node, and `publish` for a release node. Do not spawn a worker for a release node with `publish: changesets`. Stop at its gate: link the release pull request the changesets bot keeps open, and list the nodes it ships. The maintainer merges it. When it merges, set the release node to `done`, and the curator sets the shipped nodes to `released`. The next release becomes the fence, and the held pull requests can merge after a rebase.

Work that must ship early in spite of its milestone moves to the earlier milestone, or goes behind a flag that stays off.

Use an integration branch instead only when the user asks for it, or when the main branch must never contain partial work and flags are not an option. Then workers target `roadmap/<slug>`, and the user merges that branch at the end.

## Rolling and waves

- **Rolling** (default for interactive sessions): when a pull request merges, ask `plan.py ready` and start whatever became ready. Nothing waits for the slowest node in a wave. Run the curator after every few merges, or when an outcome reports a deviation.
- **Waves**: start all ready nodes, wait for all of them, curate, repeat. Simpler, with a clean checkpoint every round, but a wave takes as long as its slowest node. Use it with the Workflow script, or when the user wants to review each round.

Waves printed by `plan.py status` are a forecast in both modes. The decision to start a node always comes from `plan.py ready`.

## The loop

1. `python3 <skill>/scripts/plan.py <root> check`. Stop on errors.
2. `python3 <skill>/scripts/plan.py <root> verify` runs the `verify` commands of all todo nodes. Close any node whose acceptance already holds (see "Already fulfilled work").
3. `python3 <skill>/scripts/plan.py <root> ready --json`. The list is sorted by priority, then by critical path. Take up to `--max-parallel` nodes from the top.
4. Set each one to `status: active` and commit that to the main branch. For a story's first child, also create the story branch and set the story `active` (see "Stories"). Keep the commit to the brief files only.
5. Spawn the workers in a single message so they run at the same time (see "Spawning a worker"). In sequential mode, spawn only the first one.
6. When a worker returns, act on its reply (see "Merging and verification"). In `self` mode the worker has already reviewed and checked it. In `fresh` mode, spawn the reviewer.
7. When the pull request merges or the commit lands, set `status: done` and `spent:` (the tokens of the worker, the reviewer and any fix rounds, added up from their usage reports), and run the curator at checkpoints.
8. Stop at gates (see "Gates"). At checkpoints, end the session (see "Keeping the orchestrator's context small"). Otherwise go to step 1.

## Keeping the orchestrator's context small

The orchestrator is usually the most expensive agent in a run. It reads its whole context again on every turn, and every worker reply, diff, log and check output it reads stays there. In one measured run of 33 nodes, it was more than half of all tokens, with a median context of about 470k.

- **Work from replies and script output.** Do not read workers' diffs, logs or full outcomes in this session. The curator reads outcomes. `plan.py` answers the questions about paths, readiness and merge rules.
- **Delegate investigation.** When a reply raises something that needs reading code, spawn an agent and ask for a short answer.
- **End the session at checkpoints.** Every piece of state is in the repo: statuses, outcomes, logs and wave reports. In waves mode, do this after each wave's curator pass. In rolling mode, do it after each curator pass or after about five merged pull requests. Check that no worker is still running, commit the roadmap files, and make sure `reviews/wave-<n>.md` says what is active and what waits on what. Then tell the user to start a new session (`/clear`) with "Continue the roadmap in `<root>`". The new session starts from `plan.py <root> status` and the last wave report.

## Spawning a worker

Use the Agent tool with `isolation: "worktree"` and the model from `ready --json`. Agent worktrees start on a generated branch such as `worktree-agent-<hash>`; the worker renames it to the `branch` from `ready --json` (`feat/<node id>`, `fix/<node id>` and so on) before its first commit, and uses `pr_title` for the pull request (or the landed commit), so branches and pull requests read like the roadmap. Fill in `templates/worker-prompt.md`. The prompt names the node, the root, the base branch and the exact context files. It does not paste their contents, so the worker reads the current versions.

Before spawning, check that the base branch already contains what the worker needs: the frozen contracts and the outcomes of its dependencies. Agent worktrees start without the gitignored files of the main checkout. Claude Code copies the ones that `.worktreeinclude` names, so when the checks need a file such as `.env`, check that its pattern is listed there.

Check the machine before a wide wave. Each worktree may need its own dependency install and dev server. If memory is tight or the load is high, lower `--max-parallel`. The pr-author skill has a capacity check for this.

## Sequential mode

A roadmap runs one node at a time when `GOAL.md` sets `run: sequential`, or when `plan.py` runs with `--max-parallel 1`. `ready --json` then reports `"mode": "sequential"` on every node. Use it when the user asks for it, when the machine has room for only one worktree, or when every node edits the same files.

Worktrees keep parallel workers apart. With one worker there is nothing to keep apart, so the worktree is optional:

- **Main checkout**: spawn the worker without `isolation`. Before the first node of a session, run `git status` and ask the user once whether the worker may switch branches in their checkout. Only use it when the tree is clean and the user agrees. The worker runs `git fetch` and `git switch -c <branch> <target>` itself. When it returns, switch the checkout back to the base branch before the next status commit.
- **One worktree**: otherwise, spawn with `isolation: "worktree"` as usual, or keep one worktree from pr-author's `wt.py` and reuse it for every node.

Everything else stays the same: one branch and one change per node, outcomes, reviews and gates. The ready list still holds every node that could start. Take the first.

## Already fulfilled work

A node can be done before anyone builds it: the code shipped before the roadmap, a planning document was stale, or another node's pull request covered it on the way. Building it again wastes a session at best and conflicts with the existing code at worst.

Three places catch it:

- **Survey and import**: check each item against the code before writing its node. Already built items become `done` nodes with `fulfilled_by:` set, or are left out with a note in `GOAL.md` under Sources.
- **Before spawning**: `plan.py verify` runs the `verify` command of every todo node. A pass means the acceptance may already hold. Look at the evidence, then close the node with `fulfilled_by:` and a short outcome.
- **Inside the worker**: the worker's first step is to check whether the work exists. If it does, the worker writes an "Already fulfilled" outcome with the evidence and makes no code changes.

When the existing code differs from what a contract assumed, rewrite the contract from the real code before freezing it, and update the briefs that use it.

Partly fulfilled nodes: if the node has not started, shrink its brief to what is left and resize it. If it is active, the worker handles it. When the remainder becomes its own follow-up node, it keeps the original node's priority. Changing priority is the user's decision, so propose it in the response instead of doing it.

A passing `verify` command is a signal, not proof. Read the code before closing a node: an empty stub or a placeholder test can make a weak check pass.

## Merging and verification

Each pull request is reviewed once and checked once, in the review mode `ready --json` gave it (`review`, from the `review:` setting in `GOAL.md`). In `self` mode the worker reviews its own branch and runs the full check. In `fresh` mode the orchestrator spawns one reviewer, because a worker running as a subagent cannot spawn agents. The orchestrator works from the replies. A `ship: commit` node has no pull request: skip the draft and ready steps below, and land it as "Direct commits" describes. For each finished worker (closing a node also means ticking its acceptance boxes in the brief, or saying which ones the existing code covers):

1. If the reply reports a blocker, an unresolved deviation or a change request, resolve it first. When that needs reading code or logs, spawn an agent to do it and keep only its answer (see "Keeping the orchestrator's context small").
2. Check the owned paths with the script instead of reading the diff: `git diff --name-only <base>...<branch> | plan.py <root> can-merge <id> --files -`. Any "changes outside the node's paths" reason matters in every merge mode. Changes outside owned paths are the main source of merge conflicts and hidden coupling. Either accept them and note them in the outcome, or send the worker back.
3. Review once. In `fresh` mode, spawn one reviewer with the pr-review skill in local mode, and give it only the repo, the base and the branch. Send its blocking and should-fix findings to the worker with SendMessage, since its context is still loaded. Ask the reviewer for a second round only after the fixes, and stop after two rounds. The pull request stays a draft during these rounds, so the fixes do not start CI. When the review is clean, mark it ready with `gh pr ready <n>`, or have the worker do it. In `self` mode, use the worker's review and do not spawn a reviewer, unless auto-merge should apply to the node (see "Auto-merge").
4. Do not run the checks again. Use the result from the review: the fresh reviewer runs them, and in self mode the worker does. Run them again only when the branch changed after the review, for example after a rebase. On a private repo, run them locally and do not trigger CI.
5. Decide who merges (see "Auto-merge" below). Without an `auto` merge policy, hand the pull request to the maintainer. Never approve it yourself.
6. If a merged pull request breaks the main branch, revert it and reopen the node with the failure in its log.

Self-review costs less because no new agent has to load the repo. A fresh reviewer cost about $1.20 per node in a measured run. But a worker tends to agree with its own reasoning. That is why `review: auto` keeps a fresh reviewer for everything except S, docs and chore nodes, and always for gates, contracts, releases and hotfixes. Set `review: fresh` in `GOAL.md` when the user wants a fresh reviewer on every node.

Merge conflicts still happen. Resolve them in the worker's branch, by the worker or the orchestrator, then rerun the checks.

## Auto-merge

By default every pull request waits for the maintainer. A roadmap can opt in to merging some of them without the user, in `GOAL.md`:

```yaml
merge:
  mode: auto                                   # maintainer is the default
  method: squash
  max_size: M                                  # larger nodes go to the maintainer
  exclude: [release, hotfix, contract, gate, story]   # always go to the maintainer
  stories: auto                                # children merge into their story branch without the maintainer
```

Only switch to `auto` when the user asks for it. Merging is visible to everyone on the repo.

With `mode: auto`, the decision is the script's, not yours:

```bash
git diff --name-only <base>...<branch> | \
  python3 <skill>/scripts/plan.py <root> can-merge <id> --review-clean --checks-pass [--proof] [--fresh-review] \
    [--ci-guard ask] --files -
```

Pass `--fresh-review` only when a fresh agent did the review. A node in self mode needs it, so a self-reviewed PR goes to the maintainer unless you run a fresh review first. Pass `--review-clean` only when the review verdict had no blocking and no should-fix findings, `--checks-pass` only when lint, typecheck, build and tests passed on the branch rebased onto the current base, `--proof` only when a fix fails on the base and passes on the branch, and `--ci-guard ask` when pr-author's `ci_guard.py` says a merge would start billed CI. Exit code 0 (`auto`) means:

1. Merge: `gh pr merge <n> --squash --delete-branch` (or the policy's method).
2. Run the checks on the updated base. If they fail, revert the merge in a new pull request at once, merge that revert (restoring a green base is always allowed), set the node back to `todo` with the failure in its log, and tell the user.
3. Set the node to `done`.

Exit code 1 (`maintainer`) lists the reasons; hand the pull request to the maintainer with them. If branch protection on the base requires approvals, auto-merge cannot work; say so and keep the maintainer mode.

At every checkpoint, report what merged on its own, with links, so the user sees it without asking.

## Direct commits

A node with `ship: commit` in `ready --json` opens no pull request. `plan.py` gives it that only when the orchestrator may land it without the maintainer (see "Pull request or direct commit" in `SKILL.md`). That covers story children on their story branch, and S, docs or chore nodes under `merge.mode: auto`. The worker builds, reviews and checks the branch as usual and replies with the branch name. Then:

1. Run `can-merge` as in "Auto-merge". A verdict of `auto` with method `commit` lets the commit land. With `maintainer`, push the branch and open a pull request against the target for the maintainer, with the reasons.
2. In the worker's worktree (or the checkout that has the branch), rebase onto the current target: `git fetch`, then `git rebase <target>` (`origin/<target>` when the branch is pushed). If the target moved, rerun the fast check.
3. Squash the branch into one commit. Use `pr_title` as the subject and link the brief in the body: `git reset --soft <target>`, then `git commit -m "<pr_title>" -m "Roadmap node: <root>/nodes/<id>/brief.md"`. Follow the repo's commit convention when it differs.
4. Fast-forward the target to it. With a remote: `git push origin HEAD:<target>`. Git rejects the push when the target moved meanwhile. Then go back to step 2. When branches stay local and a checkout has the target checked out, run `git merge --ff-only <branch>` there, only when its tree is clean. When no checkout has it, run `git fetch . <branch>:<target>`. Never force the update.
5. Delete the node's branch. Record the commit hash in the outcome, set the node to `done`, and run the checks on the updated target. If they fail, revert the commit on the target at once. Set the node back to `todo` with the failure in its log, and tell the user.

A push rejected by branch protection means the target requires pull requests. Open one for the node, and set `merge.commits: off` in `GOAL.md`, or `ship: pr` on the nodes that target that branch.

On a private repo, a push to the target can start billed CI, the same as a merge. Pass `--ci-guard ask` to `can-merge` when pr-author's `ci_guard.py` says so. The node then goes to the maintainer.

## Shared and exclusive resources

- **Global numbers** (migrations, decision records): reserved per node with `reserves:`. Assign placeholders at merge time only when the numbers cannot be known in advance.
- **Generated files**: regenerate once after merging, in its own small pull request if needed.
- **Exclusive resources**: some work cannot run twice at once. Load tests and benchmarks give wrong numbers when they share a machine. A database container on a fixed port cannot be started twice. Tag such nodes with `exclusive: [loadtest]` (any name). The scheduler never puts two nodes with the same tag in one wave.
- **Slow full checks**: tell workers to run only the fast check. Run the full check on the pull request, once.

## Contract change requests

A worker that finds its contract is wrong does not edit the contract. It writes `contracts/<name>.change-request.md` (from the template), adapts its own code locally, and reports the request in its outcome.

The orchestrator then decides:

- **Accept**: update the contract, bump `version`, and list every node that uses it (`plan.py impact` on each consumer helps). Active consumers finish against the old version. Add follow-up nodes to adapt them, or update the briefs of consumers that have not started.
- **Reject**: tell the requester to adapt to the contract as written. Record the reason in the request file.

Without this rule, one worker's quick fix to a shared type breaks every parallel branch that builds on it.

## Gates

Stop and show the user:

- After the stress test, before any execution.
- After the contract wave. Contracts are the most expensive thing to get wrong.
- After any node with `gate: true`.
- When an accepted change request affects more than one active node.

The user can waive gates. Record that in `GOAL.md` so later sessions know.

## Failure handling

- **Worker fails or runs out of context**: keep its branch and log. Reopen the node (`status: todo`) and spawn a new worker. It resumes from `log.md`. If it fails twice, the node is too big or its brief is unclear. Split it or rewrite the brief.
- **Node proves impossible**: set `status: dropped`, write why in its outcome, and run `plan.py check` to see which nodes are now broken. Rework those with the user.
- **Two workers conflict despite disjoint owned paths**: the owned paths were wrong. Fix them in the briefs.

## Running a wave as a Workflow

For long roadmaps, `scripts/wave.workflow.js` runs one wave: it spawns all workers in parallel, each in a worktree with its suggested model, then runs a curator agent over the results. In sequential mode (`sequential: true` in args) it runs the workers one after another, and `isolation: "none"` runs them in the current checkout instead of worktrees. After each worker in `fresh` mode, it runs one reviewer and returns its findings with the worker's report. Self mode workers review their own branches. The orchestrator still sends findings back to workers, merges, and handles status changes and gates between waves, because the Workflow script cannot read or write files.

Only use it when the user has asked for workflow orchestration, or when they invoked this skill to run waves:

```
plan.py <root> ready --json        # becomes args.nodes
Workflow({ scriptPath: "<skill>/scripts/wave.workflow.js",
           args: { root: "<root>", skill: "<skill>", base: "main", nodes: [...] } })
// sequential mode: add sequential: true, and isolation: "none" to use the current checkout
```

It returns each worker's report (branch, pull request or empty for `ship: commit` nodes, status) and the curator's proposals. The orchestrator lands commits and merges pull requests afterwards.

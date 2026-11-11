export const meta = {
  name: 'parallel-roadmap-wave',
  description: 'Run one wave of a parallel roadmap: one worker per ready node in its own worktree, then a curator pass',
  whenToUse: 'Driven by the parallel-roadmap skill. Pass args from `plan.py <root> ready --json`.',
  phases: [
    { title: 'Work', detail: 'one worker per node, each in a git worktree' },
    { title: 'Curate', detail: 'read outcomes, propose learnings and plan updates' },
  ],
}

// args: { root, skill, base, nodes: [{ id, title, model, branch, pr_title, mode, review, ship, target, story, action,
//         context: [paths] }], sequential?, isolation? }
// `base` is the branch pull requests target (usually main). Check it out before running,
// so worktrees start from it. A node with a `target` (a story child or a batched node) builds on that branch instead.
// Nodes with `action: story-pr` are skipped: the orchestrator opens a story's pull request itself. `sequential: true` (or `mode: sequential` on the nodes) runs
// the workers one after another. `isolation: 'none'` then runs them in the current checkout
// instead of worktrees; only use it when the tree is clean and the user agreed. Each worker reviews
// its own pull request in its `review` mode. Nodes with `ship: commit` open no pull request: the
// orchestrator squashes and lands their branch as one commit. The orchestrator merges, lands commits,
// updates status and handles gates after this returns.

const REPORT = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    branch: { type: 'string' },
    pr: { type: 'string' },
    already_fulfilled: { type: 'boolean' },
    not_reproduced: { type: 'boolean' },
    proof: { type: 'string' },
    acceptance_pass: { type: 'boolean' },
    review_mode: { type: 'string', enum: ['fresh', 'self', 'none'] },
    review_rounds: { type: 'integer' },
    review_clean: { type: 'boolean' },
    checks_pass: { type: 'boolean' },
    outcome_written: { type: 'boolean' },
    change_requests: { type: 'array', items: { type: 'string' } },
    blockers: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
  required: ['id', 'branch', 'pr', 'already_fulfilled', 'not_reproduced', 'proof', 'acceptance_pass', 'review_mode', 'review_rounds', 'review_clean', 'checks_pass', 'outcome_written', 'change_requests', 'blockers', 'summary'],
}

const CURATION = {
  type: 'object',
  properties: {
    learnings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          rule: { type: 'string' },
          reason: { type: 'string' },
          folder: { type: 'string' },
          enforce_with_test: { type: 'boolean' },
        },
        required: ['rule', 'reason', 'folder', 'enforce_with_test'],
      },
    },
    brief_updates: { type: 'array', items: { type: 'string' } },
    change_requests: { type: 'array', items: { type: 'string' } },
    new_nodes: { type: 'array', items: { type: 'string' } },
    calibration: { type: 'array', items: { type: 'string' } },
    report: { type: 'string' },
  },
  required: ['learnings', 'brief_updates', 'change_requests', 'new_nodes', 'calibration', 'report'],
}

const { root, skill, base } = args
const stories = (args.nodes || []).filter(n => n.action === 'story-pr').map(n => n.id)
if (stories.length) log(`Stories ready for their pull request, not run here: ${stories.join(', ')}`)
const nodes = (args.nodes || []).filter(n => n.action !== 'story-pr')
const baseOf = n => n.target || base
const sequential = args.sequential === true || (Array.isArray(nodes) && nodes.some(n => n.mode === 'sequential'))
const isolation = sequential && args.isolation === 'none' ? 'none' : 'worktree'
if (!Array.isArray(nodes) || nodes.length === 0) {
  log('No ready nodes were passed in args.nodes; nothing to run.')
  return { reports: [], curation: null }
}

function workerPrompt(n) {
  return `You are the worker for node \`${n.id}\` ("${n.title}") of the roadmap in \`${root}\`. ${sequential
    ? 'You are the only worker running now. Other nodes come after you.'
    : 'Several other agents are working on other nodes at the same time, each in its own git worktree.'} Your work must stay inside your own node so that everyone's branches merge cleanly.

${isolation === 'none'
    ? `You work in the main checkout, not a worktree. Start your branch: \`git fetch\`, then \`git switch -c ${n.branch || 'feat/' + n.id} ${baseOf(n)}\`. When you are done, switch back to \`${base}\`.`
    : `First give your branch a descriptive name: \`git branch -m ${n.branch || 'feat/' + n.id}\` (your worktree may start on a generated name such as worktree-agent-...).${baseOf(n) !== base ? ` Your work builds on \`${baseOf(n)}\`${n.story ? `, the branch of story ${n.story}` : ', the batch branch'}: run \`git reset --hard ${baseOf(n)}\` before your first commit.` : ''}`} Use "${n.pr_title || n.title}" as the pull request title, following the repo's own title convention if it differs.

Read these files in this order. They are all the context you need; do not read other nodes' logs.
${n.context.map(p => `- ${p}`).join('\n')}

Then:
0. Check first whether the work already exists. Run the brief's \`verify\` command if it has one, and look at the code its acceptance criteria describe. If every criterion already holds, make no code changes: write the outcome with "Already fulfilled" and the evidence, commit it, skip the pull request, and report already_fulfilled=true. If some criteria hold, do only the rest.
1. Prove the problem first, if the node fixes one. That covers \`fix\` and \`hotfix\` nodes, and any node that removes a bug, a slow path, a memory or size cost, or a flake. Prove it on the current \`${baseOf(n)}\` before you change any code. For a bug, write the smallest test that fails there. For a cost, run the brief's benchmark there. The cost must exceed the noise, and a profile must place it in the code the node changes. Numbers in the brief are leads, not proof: they may come from an older commit. If the problem does not show, make no code changes. Write the outcome with "Not reproduced" and the evidence, commit only that, skip the pull request, and report not_reproduced=true. Report as proof the command, the commit and the result on each side, or "" for a node that fixes no problem.
2. If \`${root}/nodes/${n.id}/log.md\` exists, you are resuming. Continue from where it stops.
3. Do the work in the brief. Edit only the brief's owned paths and \`${root}/nodes/${n.id}/\`. If you must touch another file, keep the change minimal and record it under Deviations in your outcome. Never run \`git stash\`: every worktree of the repo shares one stash list, so another worker can pop or drop your stash, or you theirs. To set work aside, commit it on your branch.
4. Use only the numbers your brief reserves for migrations, decision records or other numbered files.
5. Build against stubs for \`behavior\` dependencies. Do not wait for them.
6. If a contract is wrong, write \`${root}/contracts/<name>.change-request.md\` from \`${skill}/templates/change-request.md\`, adapt locally, and continue. Do not edit the contract.
7. Append short notes to \`${root}/nodes/${n.id}/log.md\` as you go.
8. Run the fast check from GOAL.md while you work. The full check runs once, during the review in step 11.
9. Write \`${root}/nodes/${n.id}/outcome.md\` from \`${skill}/templates/outcome.md\`. Later agents read only this file.
10. Do not change \`status\` in your brief. Commit everything on your branch with the message "${n.id}: ${n.title}".
11. ${(n.review || 'fresh') === 'self'
    ? "Review the branch yourself, as step 6 of the pr-author skill describes: read your own diff as a reviewer would, go through pr-review's references/evaluation.md, and run the full checks once. Fix what you find, for at most two rounds. Report review_mode self, review_rounds, review_clean and checks_pass."
    : 'Do not review the branch: a fresh reviewer runs after you. Report review_mode none, review_rounds 0, review_clean false, and checks_pass for the fast check.'}
12. ${n.ship === 'commit'
    ? `Open no pull request and do not push to \`${baseOf(n)}\`: the orchestrator squashes your branch into one commit and lands it on \`${baseOf(n)}\`. Report pr as "".`
    : `Open a pull request only when the acceptance holds. For a node from step 1, the same proof must also pass on your branch: the test passes, or the measured gain exceeds the noise. If not, push nothing, record the result in the outcome, and report pr as "". Otherwise push the branch and open a pull request against \`${baseOf(n)}\` (follow the pr-author skill if it is installed). Link \`${root}/nodes/${n.id}/brief.md\` in the description. Do not merge or approve it. Report its number as pr, or "" if you made no pull request.`}`
}

function runWorker(n) {
  return agent(workerPrompt(n), {
    label: `node:${n.id}`,
    phase: 'Work',
    ...(isolation === 'worktree' ? { isolation: 'worktree' } : {}),
    schema: REPORT,
    ...(n.model ? { model: n.model } : {}),
  })
}

const REVIEW = {
  type: 'object',
  properties: {
    verdict: { type: 'string' },
    checks_pass: { type: 'boolean' },
    blocking: { type: 'array', items: { type: 'string' } },
    should_fix: { type: 'array', items: { type: 'string' } },
    nits: { type: 'array', items: { type: 'string' } },
    base_bugs: { type: 'array', items: { type: 'string' } },
  },
  required: ['verdict', 'checks_pass', 'blocking', 'should_fix', 'nits', 'base_bugs'],
}

// A worker runs as a subagent and cannot spawn its own reviewer, so fresh reviews start here.
async function workAndReview(n) {
  const r = await runWorker(n)
  if (!r || r.already_fulfilled || r.not_reproduced || (n.review || 'fresh') === 'self') return r
  // A fix whose proof failed on the branch opened no pull request, so there is nothing to review.
  if (r.proof && !r.acceptance_pass) return r
  const review = await agent(`Review ${r.branch} against ${baseOf(n)} in the current repo with the pr-review skill, in local mode. Do not post anything. Return the verdict, whether the full checks pass, and the findings, sorted into blocking, should fix, nits, and bugs found on the base.`,
    { label: `review:${n.id}`, phase: 'Work', schema: REVIEW })
  if (!review) return r
  return {
    ...r, review_mode: 'fresh', review_rounds: 1, checks_pass: review.checks_pass,
    review_clean: review.blocking.length === 0 && review.should_fix.length === 0, review,
  }
}

phase('Work')
let reports = []
if (sequential) {
  // One at a time: in the main checkout, two workers would switch branches under each other.
  for (const n of nodes) {
    reports.push(await workAndReview(n))
  }
} else {
  reports = await parallel(nodes.map(n => () => workAndReview(n)))
}

const done = reports.filter(Boolean)
const missing = nodes.filter(n => !done.some(r => r.id === n.id)).map(n => n.id)
if (missing.length) log(`No report from: ${missing.join(', ')}. Reopen these nodes.`)

// Barrier on purpose: the curator compares all outcomes of the wave together.
phase('Curate')
const curation = await agent(`You are the curator for the roadmap in \`${root}\`. A wave of workers just finished. Their branches are not merged yet, so read their files with \`git show <branch>:<path>\`.

Worker reports:
${JSON.stringify(done, null, 2)}

Read \`${skill}/references/memory.md\` (the curator section) and follow it, with one difference: do not edit any files. Return proposals only; the orchestrator applies them after merging.

For each branch, read \`${root}/nodes/<id>/outcome.md\` and any \`${root}/contracts/*.change-request.md\` it added. Then return:
- learnings: lasting rules about the code worth a nested CLAUDE.md, with the folder they apply to. Mark the ones a test, type or lint rule could enforce instead.
- brief_updates: downstream briefs that must change because an outcome deviated from the plan, each as "<node id>: <change>".
- change_requests: each open request with your recommendation (accept or reject, and why).
- new_nodes: work the outcomes revealed that no node covers.
- calibration: one line per node, "<date placeholder> <root>/<id> est <size> actual <size>: <reason>".
- report: a short wave report for reviews/wave-<n>.md.`, { label: 'curator', phase: 'Curate', schema: CURATION })

return { reports: done, missing, curation }

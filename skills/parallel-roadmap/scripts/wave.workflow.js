export const meta = {
  name: 'parallel-roadmap-wave',
  description: 'Run one wave of a parallel roadmap: one worker per ready node in its own worktree, then a curator pass',
  whenToUse: 'Driven by the parallel-roadmap skill. Pass args from `plan.py <root> ready --json`.',
  phases: [
    { title: 'Work', detail: 'one worker per node, each in a git worktree' },
    { title: 'Curate', detail: 'read outcomes, propose learnings and plan updates' },
  ],
}

// args: { root, skill, base, nodes: [{ id, title, model, branch, pr_title, mode, review, target, story, action,
//         context: [paths] }], sequential?, isolation? }
// `base` is the branch pull requests target (usually main). Check it out before running,
// so worktrees start from it. A node with a `target` (a story child) builds on that branch instead.
// Nodes with `action: story-pr` are skipped: the orchestrator opens a story's pull request itself. `sequential: true` (or `mode: sequential` on the nodes) runs
// the workers one after another. `isolation: 'none'` then runs them in the current checkout
// instead of worktrees; only use it when the tree is clean and the user agreed. Each worker reviews
// its own pull request in its `review` mode. The orchestrator merges, updates status and handles gates
// after this returns.

const REPORT = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    branch: { type: 'string' },
    pr: { type: 'string' },
    already_fulfilled: { type: 'boolean' },
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
  required: ['id', 'branch', 'pr', 'already_fulfilled', 'acceptance_pass', 'review_mode', 'review_rounds', 'review_clean', 'checks_pass', 'outcome_written', 'change_requests', 'blockers', 'summary'],
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
    : `First give your branch a descriptive name: \`git branch -m ${n.branch || 'feat/' + n.id}\` (your worktree may start on a generated name such as worktree-agent-...).${baseOf(n) !== base ? ` Your work builds on \`${baseOf(n)}\`, the branch of story ${n.story}: run \`git reset --hard ${baseOf(n)}\` before your first commit.` : ''}`} Use "${n.pr_title || n.title}" as the pull request title, following the repo's own title convention if it differs.

Read these files in this order. They are all the context you need; do not read other nodes' logs.
${n.context.map(p => `- ${p}`).join('\n')}

Then:
0. Check first whether the work already exists. Run the brief's \`verify\` command if it has one, and look at the code its acceptance criteria describe. If every criterion already holds, make no code changes: write the outcome with "Already fulfilled" and the evidence, commit it, skip the pull request, and report already_fulfilled=true. If some criteria hold, do only the rest.
1. If \`${root}/nodes/${n.id}/log.md\` exists, you are resuming. Continue from where it stops.
2. Do the work in the brief. Edit only the brief's owned paths and \`${root}/nodes/${n.id}/\`. If you must touch another file, keep the change minimal and record it under Deviations in your outcome.
3. Use only the numbers your brief reserves for migrations, decision records or other numbered files.
4. Build against stubs for \`behavior\` dependencies. Do not wait for them.
5. If a contract is wrong, write \`${root}/contracts/<name>.change-request.md\` from \`${skill}/templates/change-request.md\`, adapt locally, and continue. Do not edit the contract.
6. Append short notes to \`${root}/nodes/${n.id}/log.md\` as you go.
7. Run the fast check from GOAL.md while you work. The full check runs once, during the review in step 10.
8. Write \`${root}/nodes/${n.id}/outcome.md\` from \`${skill}/templates/outcome.md\`. Later agents read only this file.
9. Do not change \`status\` in your brief. Commit everything on your branch with the message "${n.id}: ${n.title}".
10. ${(n.review || 'fresh') === 'self'
    ? "Review the branch yourself, as step 6 of the pr-author skill describes: read your own diff as a reviewer would, go through pr-review's references/evaluation.md, and run the full checks once. Fix what you find, for at most two rounds. Report review_mode self, review_rounds, review_clean and checks_pass."
    : 'Do not review the branch: a fresh reviewer runs after you. Report review_mode none, review_rounds 0, review_clean false, and checks_pass for the fast check.'}
11. Push the branch and open a pull request against \`${baseOf(n)}\` (follow the pr-author skill if it is installed). Link \`${root}/nodes/${n.id}/brief.md\` in the description. Do not merge or approve it. Report its number as pr, or "" if you made no pull request.`
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
  if (!r || r.already_fulfilled || (n.review || 'fresh') === 'self') return r
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

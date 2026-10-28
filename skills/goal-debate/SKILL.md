---
name: goal-debate
description: Weigh a goal against what it costs before anyone plans or builds it. A proponent agent proposes the idea and expands it, an opponent agent attacks its weak points and costs, and the orchestrator judges each claim with evidence until the two settle on the structure with the best value for its cost. Costs are weighed on three axes, device capability (storage, RAM, compute), time to deliver and token spend, plus any axis the plan needs. Prior art (papers, public repos, the lab's past attempts) counts as evidence, small capped proofs settle feasibility claims, and research goals end with a hypothesis and success threshold fixed before any run. Unknowns that cannot be measured go to the user as questions. Use this skill when the user wants to evaluate, challenge, debate or sanity-check a goal, idea, proposal or ADR, asks whether something is worth building or researching, whether it has been done before, or whether it is feasible on their machine, in their time or within a token budget, or before parallel-roadmap plans a large or costly goal, even if they never say "debate".
---

# Goal debate

A plan breaks a goal into work. It never asks whether the goal, in its current shape, is worth what it costs. This skill asks that question before the plan exists, when changing direction is cheapest. Two agents argue: a proponent who builds the strongest version of the idea, and an opponent who looks for what it costs and where it breaks. The orchestrator judges. It rules on every claim with evidence, sends the questions that only the user can answer to the user, and stops the debate once it settles.

The result is `debate.md`: the settled structure of the idea, a budget on each axis, the alternatives that lost and why, and the risks still open. The user approves it. parallel-roadmap then plans from it.

## Axes

Every cost or risk sits on one axis:

- **device**: storage, RAM and compute on the machine that builds and runs the work. Worktrees, dependency installs, dev servers, models, datasets, build caches.
- **time**: how soon the result can be delivered. Critical path, waits on people or outside services, calibration from past work.
- **tokens**: what the work costs in model spend. Agents per node, context per agent, review rounds, the orchestrator's own context, the debate itself.

The proponent may propose up to two more axes when the plan needs them, for example `security` for auth work or `maintenance` for a new dependency. It gives the reason in `extra_axes`. The judge accepts an axis only when the plan touches it and it could change a decision. The user can overrule. A claim that fits no accepted axis is out of scope.

## Files

Next to the roadmap when there is one or will be one, otherwise on its own:

```
docs/roadmaps/<slug>/debate/     # or docs/debates/<slug>/ when no roadmap follows
  ledger.json                     # every claim, ruling and question; the script reads it
  evidence/                       # raw output of the measurements claims cite
  debate.md                       # the settled result, from templates/debate.md
```

Use `roadmaps/` instead of `docs/roadmaps/` when the repo has no `docs/` folder, as parallel-roadmap does.

## The script

`scripts/debate.py` is the source of truth for the ledger. Ask it what comes next. Do not decide by rereading the claims.

```bash
python3 <skill>/scripts/debate.py <dir> init --goal "<one sentence>" [--max-rounds 3] [--research]
python3 <skill>/scripts/debate.py <dir> check     # validate the ledger, exit 1 on errors
python3 <skill>/scripts/debate.py <dir> status    # rulings, open questions, and the next step
python3 <skill>/scripts/debate.py <dir> report    # Markdown summary to build debate.md from
```

`status` names the next step: `proponent`, `opponent`, `judge`, `proof`, `ask-user`, `settle` or `fix`. Read `references/ledger.md` for the claim format.

## Scale

The debate costs tokens, which is one of the things it weighs. Match its size to the goal:

- **Short**, for a goal of a few pull requests or one that can be undone cheaply: one round. The orchestrator writes the proponent and opponent claims itself, rules on them, and asks the user what it could not measure. No subagents.
- **Full**: two subagents and up to `max_rounds` rounds (default 3). Use it when the goal takes weeks, adds infrastructure, a model, a service or a heavy dependency, or needs many agents. Also use it when the user asks for a debate.

Say which one you picked and why. If a short debate turns up a high cost that both sides could argue either way, move up to a full one.

## Steps

### 1. Frame

Write the goal in one sentence, then `debate.py init`. Pass `--research` when the goal tests an idea (does this method work, is this effect real), not when it builds something known to work. A research debate cannot settle without a hypothesis. Collect the baseline evidence before anyone argues, so both sides start from the same numbers. `references/evidence.md` lists what to measure for each axis and how. At least:

- device: pr-author's `capacity.py --json`, free disk, the size of the repo, its dependencies and build output
- time: `CALIBRATION.md` in the roadmaps folder when it exists, and the user's deadline if they gave one
- tokens: `plan.py <root> context` estimates when a roadmap exists, otherwise the size of the files an agent would need to load

Then survey prior art, so neither side argues about something already known:

- papers and public repos that tried the same goal or a close one, with their results
- the lab's own record: past `debate.md` files, experiment outcomes and decision records in this repo and the user's other repos
- a negative result counts as much as a positive one

Keep the survey short: a handful of sources that bear on the goal, not a literature review. `references/evidence.md` has the steps.

Add each measurement and each prior-art finding as a `fact` claim by the judge, with the command or the citation as its source. Save long output under `evidence/`. Do not start a long build or test run without asking the user first.

### 2. Proponent opens

Spawn the proponent with the prompt in `references/roles.md`. It writes `proposal` claims that together describe the structure of the idea, at least one `alternative` that reaches the same goal in another way, an estimate on each axis, any extra axes it wants, and questions for the user.

### 3. Opponent answers

Spawn the opponent with fresh context, using its prompt in `references/roles.md`. Give it the goal, the repo and the ledger, and nothing else from this conversation. It sees the proponent's claims, not the proponent's reasoning. An opponent that reads the reasoning tends to accept it. It writes `cost`, `risk` and `rebuttal` claims against specific proposal ids, its own `alternative` claims, and questions.

### 4. Judge

The orchestrator rules. It does not argue and does not add proposals.

1. Rule on each proposed extra axis: accepted or rejected, with the reason.
2. Rule on each claim: `upheld` (it stands and shapes the result), `rejected` (with `ruling_why`), or `open` (it could matter and no one can settle it now, with `ruling_why`).
3. Settle disputes that a measurement can settle by measuring, and add the result as a `fact`. Two estimates that disagree are a reason to measure, not to pick one.
4. Order a proof when a claim is high severity, ruled `open`, and cheap to test with a small throwaway build, for example "the 4-bit model fits in 8 GB" or "the parser handles the 2 GB file". See "Proofs" below.
5. Filter the questions. A question the repo, the machine, the docs or a quick command can answer is not for the user. The judge answers it with a `fact`. Send the rest to the user with AskUserQuestion, at most four per round. Each one stands on its own and names the claims it blocks. Typical questions: deadlines, spend limits, target hardware, which axis wins when two trade off, and plans the repo does not show.
6. Record the answers in the ledger and run `debate.py status`.

How to weigh claims is in `references/roles.md` under "Judging". In short: measured beats calibrated, calibrated beats sourced, and a guess never outweighs a measurement. A high cost upheld on an estimate alone becomes a spike or a measurement, not a verdict.

### Proofs

A proof answers one feasibility question with a small build that is thrown away afterwards. It is not the start of the project.

- Add it to `proofs` in the ledger with the claim it settles, the question, the scratch directory and a cap set before it starts. The default cap is 30 minutes and 100k tokens per proof, and at most 2 proofs per debate. A larger cap needs the user's agreement.
- Run it in a scratch directory outside the repo, by one subagent or by the judge itself. It may install packages there and download small models or datasets. Ask the user before downloads over about 1 GB.
- Stop at the cap. A proof that hits its cap is `abandoned`, and that result is itself evidence: "did not fit in 30 minutes".
- Record the result as a `measured` fact citing the proof id, then re-rule the claim.

### 5. Next round

While `status` says `proponent` or `opponent`, continue the same two agents with SendMessage, so they keep what they already read in the repo. Each gets only what is new: the rulings, the facts, and the user's answers. The proponent revises the structure against the upheld costs. It amends a proposal, cuts scope, switches to an alternative, or concedes. The opponent then answers the revision.

A side that concedes names the claim or evidence that changed its mind. A concession without a reason is agreement for its own sake, and the judge drops it from the result.

### 6. Settle

The debate settles when `status` says `settle`. That happens when a round adds nothing that stands, or when the round cap is reached. Then:

1. For a research debate, the judge writes the `hypothesis` in the ledger: the statement, the metric, the baseline, the success threshold and the kill criteria. It takes them from the upheld claims and the user's answers. This fixes what counts as success before anyone sees a result.
2. Run `debate.py report` and write `debate.md` from `templates/debate.md`: the hypothesis, the settled structure, the budget on each axis, the rejected alternatives with the claims that beat them, the proofs, the open risks, and the user's answers.
3. Turn each open risk into a spike, a measurement or an accepted risk with a reason.
4. Show the user `debate.md` and get their approval. They may overrule any ruling. Record that in the ledger with their reason.

Never move on to planning or building without that approval.

### 7. Hand off

After approval, when a roadmap follows, start parallel-roadmap at "1. Discover" with `debate.md` as input:

- the settled structure becomes the outcome
- each axis budget becomes a line under "Constraints" in `GOAL.md` (for example "at most 2 parallel worktrees: 8 GB RAM, measured", or "token ceiling of about 2M for the roadmap")
- the device budget sets `run:` and `--max-parallel`
- rejected alternatives become "Non-goals", with a link to `debate.md`
- open risks become spike nodes in the first wave
- the hypothesis becomes one or more `type: experiment` nodes whose `hypothesis:` points to `debate.md`. Their acceptance is the success threshold. A result that misses it, or meets a kill criterion, sends the goal back to a new debate with the result as a fact.

When no roadmap follows, `debate.md` is the deliverable. If the repo keeps decision records, offer to turn it into one.

## Rules

- Every claim has evidence, and the evidence names its source. An argument without evidence is not a claim.
- The two sides argue and the judge rules. In a full debate the judge never takes a side's role, and a side never rules.
- Ask the user only what cannot be observed or measured, and ask it once.
- The debate stops at the round cap. Open claims at the cap become open risks.
- Nothing gets built in the repo during a debate. Proofs and measurements write only under `evidence/` or a scratch directory, and proofs stay within their caps.
- A research debate fixes the hypothesis, metric and threshold before any run. Changing them after a result needs a new debate.

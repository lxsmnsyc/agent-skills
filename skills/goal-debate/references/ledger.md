# Ledger format

`ledger.json` holds the whole debate. Agents write claims into it. The judge writes rulings, facts and answers. `debate.py check` validates it.

```json
{
  "goal": "Caption every photo in the library with an on-device model",
  "max_rounds": 3,
  "extra_axes": [
    {"name": "privacy", "by": "proponent", "why": "photos must not leave the machine", "status": "accepted",
     "ruling_why": "the cloud alternative sends user photos to a third party"}
  ],
  "claims": [
    {"id": "J1", "round": 1, "by": "judge", "kind": "fact", "axis": "device",
     "text": "8 GB RAM, 5.4 GB free, load 5.7 on 8 cores",
     "evidence": {"type": "measured", "source": "capacity.py --json", "detail": "evidence/capacity.json"},
     "ruling": "upheld"},
    {"id": "J2", "round": 1, "by": "judge", "kind": "fact", "axis": "device",
     "text": "Proof T1: 3.4 GB peak RAM, 6.1 s per photo on 20 photos",
     "evidence": {"type": "measured", "source": "proof T1", "detail": "evidence/T1.txt"},
     "ruling": "upheld"},
    {"id": "P1", "round": 1, "by": "proponent", "kind": "proposal",
     "text": "Batch job captions photos with a 4-bit vision model, 50 at a time, resumable",
     "estimate": {"value": 3.5, "unit": "GB RAM peak"},
     "evidence": {"type": "source", "source": "model card, 4-bit weights 2.9 GB"},
     "ruling": "upheld"},
    {"id": "O1", "round": 1, "by": "opponent", "kind": "cost", "axis": "time", "severity": "high",
     "answers": ["P1"],
     "text": "20k photos at about 6 s each on this CPU is 33 hours of compute",
     "estimate": {"value": 33, "unit": "hours"},
     "evidence": {"type": "measured", "source": "scripts/caption-sample.sh on 20 photos"},
     "ruling": "upheld"},
    {"id": "P4", "round": 2, "by": "proponent", "kind": "concession", "answers": ["P1"],
     "why": "O1 measured 6 s per photo, so one run cannot finish the backlog",
     "text": "Run the batch job in overnight chunks of 3,000 photos instead of one run"}
  ],
  "questions": [
    {"id": "Q1", "by": "opponent", "blocks": ["O1"],
     "ask": "Can the backlog run overnight over several days, or must it finish in one run?",
     "answer": "Overnight is fine, done within a week"}
  ],
  "proofs": [
    {"id": "T1", "claim": "P1", "question": "Does the 4-bit model caption a photo within 4 GB peak RAM?",
     "dir": "/tmp/goal-debate/caption-proof", "cap": {"minutes": 30, "tokens": 100000},
     "status": "done", "result": "3.4 GB peak, 6.1 s per photo on 20 photos", "fact": "J2"}
  ],
  "research": false,
  "hypothesis": null,
  "spend": [
    {"round": 1, "tokens": 48000}
  ]
}
```

## Claims

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Unique. Use `P<n>` for the proponent, `O<n>` for the opponent, `J<n>` for the judge. |
| `round` | yes | Round the claim was made in, from 1. |
| `by` | yes | `proponent`, `opponent` or `judge`. |
| `kind` | yes | See below. |
| `axis` | cost, risk, fact | `device`, `time`, `tokens`, or an accepted extra axis. |
| `severity` | cost, risk | `low`, `medium` or `high`: how much it would change the decision. |
| `answers` | rebuttal, concession | Ids of the claims this one answers. Costs and risks name the proposal they attack here too. |
| `text` | yes | One or two sentences. Specific to this repo and machine. |
| `estimate` | when there is a number | `{"value": ..., "unit": ...}`. |
| `evidence` | all but concession | `{"type", "source", "detail"}`. `source` is the command, file or URL. `detail` points into `evidence/`. |
| `why` | concession | The claim or evidence that changed the side's mind. |
| `ruling` | judge sets it | `upheld`, `rejected`, `open`, or absent until ruled. |
| `ruling_why` | rejected, open | The reason, in one sentence. |

Kinds:

- `proposal`: a piece of the idea's structure. All upheld proposals together are the settled structure.
- `alternative`: another way to reach the goal. Upheld means it was adopted in place of something.
- `cost`: what a proposal takes on one axis.
- `risk`: what could go wrong, on one axis, with how likely it is in the text.
- `rebuttal`: an answer to another claim, with its own evidence.
- `concession`: drops or amends a claim of the side's own. Needs `why`.
- `fact`: a measurement the judge adds. Only the judge writes facts.

Evidence types, strongest first:

- `measured`: output of a command on this machine or this repo.
- `calibration`: past estimates against actuals, from `CALIBRATION.md` or git history.
- `source`: a file, doc, model card or price list.
- `prior-art`: a paper, a public repo, or the lab's own past debate or experiment. `source` is the citation or path, and `detail` says what it found, including negative results.
- `user`: an answered question. Set `question` to its id.
- `estimate`: a reasoned guess. Allowed, but weakest.

## Questions

`id` (`Q<n>`), `by`, `ask`, `blocks` (claim ids it affects) and `answer`, filled when the user replies. Write `ask` so it makes sense on its own, because the user sees only the question.

## Proofs

| Field | Meaning |
| --- | --- |
| `id` | `T<n>`. Unique across claims, questions and proofs. |
| `claim` | The one claim it settles. |
| `question` | What it answers, as a yes or no or a number. |
| `dir` | Scratch directory outside the repo. |
| `cap` | `{"minutes", "tokens"}`, set before it starts. Defaults 30 and 100000. |
| `status` | `planned`, `running`, `done` or `abandoned`. |
| `result` | What it found, or why it was abandoned. |
| `fact` | The judge's `fact` claim that records the result, for `done`. |

## Hypothesis

Required before a research debate (`"research": true`) can settle. All fields are text.

```json
"hypothesis": {
  "statement": "Contrastive pretraining on our 40k labeled scans beats ImageNet init on rare classes",
  "metric": "macro F1 on the 12 rarest classes, held-out split v3",
  "baseline": "ImageNet init, 0.41 macro F1 (run 2026-09-12)",
  "threshold": "at least 0.46, mean of 3 seeds",
  "kill": "below 0.43 after the 3-seed run, or pretraining over 40 GPU hours",
  "claims": ["P1", "O4", "Q2"]
}
```

`claims` lists the claims and questions it rests on. Change the hypothesis only through a new debate.

## Spend

Optional. One entry per round with the tokens it took, read from the agents' usage reports. `status` adds them up so the debate's own cost stays visible.

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
- `user`: an answered question. Set `question` to its id.
- `estimate`: a reasoned guess. Allowed, but weakest.

## Questions

`id` (`Q<n>`), `by`, `ask`, `blocks` (claim ids it affects) and `answer`, filled when the user replies. Write `ask` so it makes sense on its own, because the user sees only the question.

## Spend

Optional. One entry per round with the tokens it took, read from the agents' usage reports. `status` adds them up so the debate's own cost stays visible.

#!/usr/bin/env python3
"""Keep the claim ledger of a goal debate, and say what the debate needs next.

The ledger is <dir>/ledger.json. Stdlib only.

Usage:
  debate.py <dir> init --goal "..." [--max-rounds 3]   # write an empty ledger
  debate.py <dir> check                               # validation only, exit 1 on errors
  debate.py <dir> status                              # rulings, open questions, next step (default)
  debate.py <dir> report                              # Markdown summary for debate.md
Options: --json
"""
import argparse
import json
import sys
from pathlib import Path

BASE_AXES = ["device", "time", "tokens"]
MAX_EXTRA_AXES = 2
DEFAULT_MAX_ROUNDS = 3
ROLES = {"proponent", "opponent", "judge"}
# proposal: a piece of the idea's structure. alternative: another way to reach the goal.
# cost, risk: what a proposal takes or could break, on one axis. rebuttal: answers other claims.
# concession: drops or amends a claim of one's own side. fact: a measurement the judge adds.
KINDS = {"proposal", "alternative", "cost", "risk", "rebuttal", "concession", "fact"}
NEEDS_AXIS = {"cost", "risk", "fact"}
NEEDS_ANSWERS = {"rebuttal", "concession"}
SEVERITIES = {"low", "medium", "high"}
# measured: command output on this machine or repo. calibration: past estimate against actual.
# source: a file, doc or price list. user: an answered question. estimate: a reasoned guess.
EVIDENCE = {"measured", "calibration", "source", "user", "estimate"}
RULINGS = {None, "upheld", "rejected", "open"}
STANDING = {"upheld", "open"}
AXIS_STATUSES = {"proposed", "accepted", "rejected"}


def ledger_path(root):
    return root / "ledger.json"


def load(root):
    path = ledger_path(root)
    if not path.is_file():
        sys.exit(f"{path}: no ledger, run `debate.py {root} init` first")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"{path}: not valid JSON: {e}")


def axes(ledger):
    result = list(BASE_AXES)
    for extra in ledger.get("extra_axes", []):
        if extra.get("status") == "accepted":
            result.append(extra.get("name"))
    return result


def last_round(ledger):
    rounds = 0
    for claim in ledger.get("claims", []):
        if isinstance(claim.get("round"), int):
            rounds = max(rounds, claim["round"])
    return rounds


def check(ledger):
    errors, warnings = [], []
    claims = ledger.get("claims", [])
    questions = ledger.get("questions", [])
    allowed_axes = set(axes(ledger))
    max_rounds = ledger.get("max_rounds", DEFAULT_MAX_ROUNDS)

    if not ledger.get("goal"):
        errors.append("ledger: `goal` is empty")

    extra_names = set()
    accepted_extra = 0
    for extra in ledger.get("extra_axes", []):
        name = extra.get("name")
        if not name:
            errors.append("extra_axes: an entry has no name")
            continue
        if name in BASE_AXES or name in extra_names:
            errors.append(f"extra_axes: `{name}` is listed twice")
        extra_names.add(name)
        if extra.get("status") not in AXIS_STATUSES:
            errors.append(f"extra_axes {name}: status must be one of {sorted(AXIS_STATUSES)}")
        if not extra.get("why"):
            errors.append(f"extra_axes {name}: give the reason this plan needs the axis")
        if extra.get("status") == "accepted":
            accepted_extra += 1
        if extra.get("status") == "proposed":
            warnings.append(f"extra_axes {name}: proposed but not ruled on; the judge accepts or rejects it")
    if accepted_extra > MAX_EXTRA_AXES:
        warnings.append(f"{accepted_extra} extra axes accepted; more than {MAX_EXTRA_AXES} spreads the debate thin")

    ids = {}
    for claim in claims:
        cid = claim.get("id")
        if not cid:
            errors.append(f"claim without an id: {claim.get('text', '')[:40]!r}")
            continue
        if cid in ids:
            errors.append(f"{cid}: id used twice")
        ids[cid] = claim

    question_ids = {}
    for q in questions:
        qid = q.get("id")
        if not qid:
            errors.append("question without an id")
            continue
        if qid in question_ids or qid in ids:
            errors.append(f"{qid}: id used twice")
        question_ids[qid] = q
        if q.get("by") not in ROLES:
            errors.append(f"{qid}: `by` must be one of {sorted(ROLES)}")
        if not q.get("ask"):
            errors.append(f"{qid}: `ask` is empty")
        for ref in q.get("blocks", []):
            if ref not in ids:
                errors.append(f"{qid}: blocks unknown claim {ref}")

    for cid, claim in ids.items():
        kind = claim.get("kind")
        by = claim.get("by")
        rnd = claim.get("round")
        if kind not in KINDS:
            errors.append(f"{cid}: kind must be one of {sorted(KINDS)}")
        if by not in ROLES:
            errors.append(f"{cid}: `by` must be one of {sorted(ROLES)}")
        if by == "judge" and kind != "fact":
            errors.append(f"{cid}: the judge only adds facts; arguments come from the two sides")
        if kind == "fact" and by != "judge":
            errors.append(f"{cid}: facts come from the judge; a side gives a measurement as evidence on its own claim")
        if not isinstance(rnd, int) or rnd < 1:
            errors.append(f"{cid}: round must be a number from 1")
        elif rnd > max_rounds:
            warnings.append(f"{cid}: round {rnd} is past max_rounds {max_rounds}")
        if not claim.get("text"):
            errors.append(f"{cid}: text is empty")

        axis = claim.get("axis")
        if kind in NEEDS_AXIS and not axis:
            errors.append(f"{cid}: a {kind} needs an axis")
        if axis and axis not in allowed_axes:
            errors.append(f"{cid}: axis `{axis}` is not one of {allowed_axes_text(ledger)}")
        if kind in ("cost", "risk") and claim.get("severity") not in SEVERITIES:
            errors.append(f"{cid}: a {kind} needs severity low, medium or high")

        answers = claim.get("answers", [])
        if kind in NEEDS_ANSWERS and not answers:
            errors.append(f"{cid}: a {kind} must name the claims it answers")
        for ref in answers:
            target = ids.get(ref)
            if target is None:
                errors.append(f"{cid}: answers unknown claim {ref}")
                continue
            if isinstance(rnd, int) and isinstance(target.get("round"), int) and target["round"] > rnd:
                errors.append(f"{cid}: answers {ref}, which comes from a later round")
            if kind == "concession" and target.get("by") != by:
                errors.append(f"{cid}: a concession drops or amends a claim of its own side, and {ref} is not")

        evidence = claim.get("evidence")
        if kind != "concession":
            if not isinstance(evidence, dict) or evidence.get("type") not in EVIDENCE:
                errors.append(f"{cid}: evidence.type must be one of {sorted(EVIDENCE)}")
            elif evidence["type"] == "user":
                qid = evidence.get("question")
                if qid not in question_ids:
                    errors.append(f"{cid}: evidence from the user must name an answered question")
                elif not question_ids[qid].get("answer"):
                    errors.append(f"{cid}: question {qid} is not answered yet")
            elif evidence["type"] in ("measured", "calibration", "source") and not evidence.get("source"):
                errors.append(f"{cid}: {evidence['type']} evidence needs a source (the command or the file)")
        if kind == "concession" and not claim.get("why"):
            errors.append(f"{cid}: a concession says which claim or evidence changed the side's mind")

        ruling = claim.get("ruling")
        if ruling not in RULINGS:
            errors.append(f"{cid}: ruling must be upheld, rejected, open, or empty")
        if ruling in ("rejected", "open") and not claim.get("ruling_why"):
            errors.append(f"{cid}: a {ruling} ruling needs ruling_why")
        if (ruling == "upheld" and kind in ("cost", "risk") and claim.get("severity") == "high"
                and isinstance(evidence, dict) and evidence.get("type") == "estimate"):
            warnings.append(f"{cid}: a high {kind} upheld on an estimate alone; measure it or plan a spike")

    return errors, warnings


def allowed_axes_text(ledger):
    return ", ".join(axes(ledger))


def converged(ledger):
    """The latest round settled nothing new: every claim in it was rejected or concedes."""
    rnd = last_round(ledger)
    if rnd < 2:
        return False
    for claim in ledger.get("claims", []):
        if claim.get("round") != rnd:
            continue
        if claim.get("kind") == "concession":
            continue
        if claim.get("ruling") in STANDING:
            return False
    return True


def status(ledger, errors):
    claims = ledger.get("claims", [])
    rnd = last_round(ledger)
    max_rounds = ledger.get("max_rounds", DEFAULT_MAX_ROUNDS)
    unruled = []
    for claim in claims:
        if claim.get("ruling") is None and claim.get("kind") not in ("concession", "fact"):
            unruled.append(claim.get("id"))
    proposed_axes = []
    for extra in ledger.get("extra_axes", []):
        if extra.get("status") == "proposed":
            proposed_axes.append(extra.get("name"))
    unanswered = []
    for q in ledger.get("questions", []):
        if not q.get("answer"):
            unanswered.append(q.get("id"))
    counts = {}
    for claim in claims:
        key = "concession" if claim.get("kind") == "concession" else claim.get("ruling") or "unruled"
        counts[key] = counts.get(key, 0) + 1

    if errors:
        step, why = "fix", "the ledger has errors"
    elif rnd == 0:
        step, why = "proponent", "no claims yet; the proponent opens round 1"
    elif proposed_axes:
        step, why = "judge", f"rule on the proposed axes: {', '.join(proposed_axes)}"
    elif unruled:
        step, why = "judge", f"rule on {', '.join(unruled)}"
    elif unanswered:
        step, why = "ask-user", f"answer {', '.join(unanswered)} before the next round"
    elif converged(ledger):
        step, why = "settle", f"round {rnd} added nothing that stands"
    elif rnd >= max_rounds:
        step, why = "settle", f"round cap {max_rounds} reached; open claims become open risks"
    elif not has_side(ledger, rnd, "opponent"):
        step, why = "opponent", f"the opponent has not answered round {rnd}"
    else:
        step, why = "proponent", f"open round {rnd + 1}: revise the structure against the upheld costs"

    return {
        "goal": ledger.get("goal"),
        "round": rnd,
        "max_rounds": max_rounds,
        "axes": axes(ledger),
        "rulings": counts,
        "unruled": unruled,
        "unanswered_questions": unanswered,
        "converged": converged(ledger),
        "next": step,
        "why": why,
        "debate_tokens": debate_tokens(ledger),
    }


def has_side(ledger, rnd, side):
    for claim in ledger.get("claims", []):
        if claim.get("round") == rnd and claim.get("by") == side:
            return True
    return False


def debate_tokens(ledger):
    total = 0
    for spend in ledger.get("spend", []):
        total += spend.get("tokens", 0)
    return total


def estimate_text(claim):
    est = claim.get("estimate")
    if not isinstance(est, dict) or est.get("value") is None:
        return ""
    unit = f" {est['unit']}" if est.get("unit") else ""
    return f" ({est['value']}{unit})"


def evidence_text(claim):
    ev = claim.get("evidence") or {}
    kind = ev.get("type")
    if not kind:
        return ""
    if kind == "user":
        return f" [user: {ev.get('question')}]"
    if ev.get("source"):
        return f" [{kind}: `{ev['source']}`]"
    return f" [{kind}]"


def report(ledger):
    claims = ledger.get("claims", [])
    by_id = {}
    for claim in claims:
        by_id[claim.get("id")] = claim
    lines = [f"# Debate: {ledger.get('goal')}", ""]

    lines += ["## Settled structure", ""]
    structure = []
    for claim in claims:
        if claim.get("kind") in ("proposal", "alternative") and claim.get("ruling") == "upheld":
            structure.append(f"- {claim['id']}: {claim['text']}{estimate_text(claim)}")
            for other in claims:
                if other.get("kind") == "concession" and claim["id"] in other.get("answers", []):
                    structure.append(f"  - amended by {other['id']}: {other['text']}")
    lines += structure or ["- (nothing upheld)"]
    lines.append("")

    lines += ["## Budget by axis", ""]
    for axis in axes(ledger):
        rows = []
        for claim in claims:
            if claim.get("axis") != axis or claim.get("ruling") != "upheld":
                continue
            if claim.get("kind") in ("concession",):
                continue
            severity = f"{claim['severity']}: " if claim.get("severity") else ""
            rows.append(f"  - {claim['id']} {severity}{claim['text']}{estimate_text(claim)}{evidence_text(claim)}")
        lines.append(f"- {axis}")
        lines += rows or ["  - (no upheld claims)"]
    lines.append("")

    lines += ["## Rejected", ""]
    rejected = []
    for claim in claims:
        if claim.get("ruling") != "rejected" or claim.get("kind") not in ("proposal", "alternative"):
            continue
        killers = []
        for other in claims:
            if claim["id"] in other.get("answers", []) and other.get("ruling") == "upheld":
                killers.append(other["id"])
        reason = claim.get("ruling_why", "")
        by = f" (by {', '.join(killers)})" if killers else ""
        rejected.append(f"- {claim['id']}: {claim['text']}. Why not: {reason}{by}")
    lines += rejected or ["- (none)"]
    lines.append("")

    lines += ["## Open risks", ""]
    risks = []
    for claim in claims:
        if claim.get("ruling") == "open":
            risks.append(f"- {claim['id']} ({claim.get('axis') or claim.get('kind')}): {claim['text']}. "
                         f"Open because: {claim.get('ruling_why', '')}")
    lines += risks or ["- (none)"]
    lines.append("")

    lines += ["## Answers from the user", ""]
    answers = []
    for q in ledger.get("questions", []):
        if q.get("answer"):
            answers.append(f"- {q['id']} ({q.get('by')}): {q['ask']} Answer: {q['answer']}")
    lines += answers or ["- (none asked)"]
    lines.append("")

    tokens = debate_tokens(ledger)
    lines += ["## Debate cost", "", f"- {last_round(ledger)} rounds"
              + (f", about {tokens} tokens" if tokens else "")]
    return "\n".join(lines) + "\n"


def print_check(errors, warnings):
    for e in errors:
        print(f"error: {e}")
    for w in warnings:
        print(f"warning: {w}")
    if not errors and not warnings:
        print("ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("command", nargs="?", default="status", choices=["init", "check", "status", "report"])
    ap.add_argument("--goal", default="")
    ap.add_argument("--max-rounds", type=int, default=DEFAULT_MAX_ROUNDS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "init":
        path = ledger_path(args.root)
        if path.exists():
            sys.exit(f"{path}: already exists")
        if not args.goal:
            sys.exit("init needs --goal")
        args.root.mkdir(parents=True, exist_ok=True)
        ledger = {"goal": args.goal, "max_rounds": args.max_rounds, "extra_axes": [],
                  "claims": [], "questions": [], "spend": []}
        path.write_text(json.dumps(ledger, indent=2) + "\n")
        print(f"wrote {path}")
        return

    ledger = load(args.root)
    errors, warnings = check(ledger)

    if args.command == "check":
        if args.json:
            print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
        else:
            print_check(errors, warnings)
        sys.exit(1 if errors else 0)

    if args.command == "status":
        result = status(ledger, errors)
        if args.json:
            result["errors"], result["warnings"] = errors, warnings
            print(json.dumps(result, indent=2))
            return
        if errors or warnings:
            print_check(errors, warnings)
            print()
        print(f"goal: {result['goal']}")
        print(f"round {result['round']} of {result['max_rounds']}, axes: {', '.join(result['axes'])}")
        print("rulings: " + ", ".join(f"{k} {v}" for k, v in sorted(result["rulings"].items())))
        if result["debate_tokens"]:
            print(f"debate so far: about {result['debate_tokens']} tokens")
        print(f"next: {result['next']} ({result['why']})")
        return

    if errors:
        print_check(errors, warnings)
        sys.exit(1)
    print(report(ledger), end="")


if __name__ == "__main__":
    main()

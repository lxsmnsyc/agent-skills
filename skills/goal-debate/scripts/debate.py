#!/usr/bin/env python3
"""Keep the claim ledger of a goal debate, and say what the debate needs next.

The ledger is <dir>/ledger.json. Stdlib only.

Usage:
  debate.py <dir> init --goal "..." [--max-rounds 3] [--max-tokens N] [--research]
                       [--roadmap <root>] [--supersedes <earlier debate dir>]   # write an empty ledger
  debate.py <dir> check                               # validation only, exit 1 on errors
  debate.py <dir> status                              # rulings, open questions, next step (default)
  debate.py <dir> seal                                # freeze the claims of finished rounds
  debate.py <dir> report                              # Markdown summary for debate.md
Options: --json

With --roadmap the debate weighs an existing roadmap: `cut` claims name its nodes.
"""
import argparse
import json
import re
import sys
from pathlib import Path

BASE_AXES = ["device", "time", "tokens"]
MAX_EXTRA_AXES = 2
DEFAULT_MAX_ROUNDS = 3
ROLES = {"proponent", "opponent", "judge"}
# proposal: a piece of the idea's structure. alternative: another way to reach the goal.
# cost, risk: what a proposal takes or could break, on one axis. rebuttal: answers other claims.
# concession: drops or amends a claim of one's own side. fact: a measurement the judge adds.
# cut: drop, park, merge or outline nodes of an existing roadmap (needs `roadmap` in the ledger).
KINDS = {"proposal", "alternative", "cost", "risk", "rebuttal", "concession", "fact", "cut"}
CUT_ACTIONS = {"drop", "park", "merge", "outline"}
NEEDS_AXIS = {"cost", "risk", "fact"}
NEEDS_ANSWERS = {"rebuttal", "concession"}
SEVERITIES = {"low", "medium", "high"}
# measured: command output on this machine or repo. calibration: past estimate against actual.
# source: a file, doc or price list. prior-art: a paper, a public repo, or the lab's own past
# debate or experiment. user: an answered question. estimate: a reasoned guess.
EVIDENCE = {"measured", "calibration", "source", "prior-art", "user", "estimate"}
NEEDS_SOURCE = {"measured", "calibration", "source", "prior-art"}
RULINGS = {None, "upheld", "rejected", "open"}
STANDING = {"upheld", "open"}
AXIS_STATUSES = {"proposed", "accepted", "rejected"}
# A proof is a small throwaway build in a scratch directory that settles one claim.
PROOF_STATUSES = {"planned", "running", "done", "abandoned"}
PROOF_PENDING = {"planned", "running"}
MAX_PROOFS = 2
PROOF_CAP = {"minutes": 30, "tokens": 100000}
HYPOTHESIS_FIELDS = ("statement", "metric", "baseline", "threshold", "kill")
# Fields the judge or the user may still change after a round is sealed.
RULING_FIELDS = {"ruling", "ruling_why", "user_ruling", "user_why"}
SPEND_WARN = 0.8


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


def ruling(claim):
    """The ruling that counts: the user's when they overruled the judge."""
    return claim.get("user_ruling") or claim.get("ruling")


def sealed_path(root):
    return root / "sealed.json"


def roadmap_nodes(roadmap):
    """Node id -> status for an existing roadmap, from the briefs and archive.md."""
    nodes = {}
    for brief in sorted((roadmap / "nodes").glob("*/brief.md")):
        text = brief.read_text()
        nid = re.search(r"^id:\s*(\S+)", text, re.M)
        status = re.search(r"^status:\s*(\S+)", text, re.M)
        nodes[nid.group(1) if nid else brief.parent.name] = status.group(1) if status else "todo"
    archive = roadmap / "archive.md"
    if archive.is_file():
        for m in re.finditer(r"^- (\S+?):", archive.read_text(), re.M):
            nodes.setdefault(m.group(1), "done")
    return nodes


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


def check(ledger, root=None):
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
            elif evidence["type"] in NEEDS_SOURCE and not evidence.get("source"):
                errors.append(f"{cid}: {evidence['type']} evidence needs a source (the command or the file)")
        if kind == "concession" and not claim.get("why"):
            errors.append(f"{cid}: a concession says which claim or evidence changed the side's mind")

        judged = claim.get("ruling")
        if judged not in RULINGS:
            errors.append(f"{cid}: ruling must be upheld, rejected, open, or empty")
        if judged in ("rejected", "open") and not claim.get("ruling_why"):
            errors.append(f"{cid}: a {judged} ruling needs ruling_why")
        if claim.get("user_ruling") is not None:
            if claim["user_ruling"] not in RULINGS - {None}:
                errors.append(f"{cid}: user_ruling must be upheld, rejected or open")
            if not claim.get("user_why"):
                errors.append(f"{cid}: record the user's reason for overruling in user_why")
        if (ruling(claim) == "upheld" and kind in ("cost", "risk") and claim.get("severity") == "high"
                and isinstance(evidence, dict) and evidence.get("type") == "estimate"):
            warnings.append(f"{cid}: a high {kind} upheld on an estimate alone; measure it or plan a spike")

    check_proofs(ledger, ids, question_ids, errors, warnings)
    check_hypothesis(ledger, ids, question_ids, errors)
    check_cuts(ledger, ids, root, errors, warnings)
    check_sealed(ids, root, errors)
    check_links(ledger, root, warnings)
    budget = ledger.get("max_tokens")
    if budget and debate_tokens(ledger) >= budget * SPEND_WARN:
        warnings.append(f"the debate has spent {debate_tokens(ledger)} of its {budget} token budget")
    return errors, warnings


def check_cuts(ledger, ids, root, errors, warnings):
    cuts = [c for c in ids.values() if c.get("kind") == "cut"]
    if not cuts:
        return
    roadmap = ledger.get("roadmap")
    if not roadmap:
        errors.append("`cut` claims need `roadmap` in the ledger, the roadmap they cut")
        return
    path = resolve(roadmap, root)
    if path is None or not (path / "nodes").is_dir():
        errors.append(f"roadmap {roadmap}: no nodes/ directory found")
        return
    nodes = roadmap_nodes(path)
    for claim in cuts:
        cid = claim["id"]
        if claim.get("action") not in CUT_ACTIONS:
            errors.append(f"{cid}: a cut needs action drop, park, merge or outline")
        if not claim.get("nodes"):
            errors.append(f"{cid}: a cut names the nodes it cuts in `nodes`")
        for nid in claim.get("nodes", []):
            status = nodes.get(nid)
            if status is None:
                errors.append(f"{cid}: node {nid} is not in {roadmap}")
            elif status == "active":
                warnings.append(f"{cid}: node {nid} is active; let it finish and cut what follows it")
            elif status in ("done", "released"):
                errors.append(f"{cid}: node {nid} is already {status}")


def resolve(value, root):
    """A path from the ledger: as given (from the repo root), or next to the debate folder."""
    candidates = [Path(value)]
    if root is not None:
        candidates.append(root / value)
    for c in candidates:
        if c.exists():
            return c
    return None


def check_sealed(ids, root, errors):
    if root is None or not sealed_path(root).is_file():
        return
    sealed = json.loads(sealed_path(root).read_text())
    for cid, frozen in sealed.get("claims", {}).items():
        claim = ids.get(cid)
        if claim is None:
            errors.append(f"{cid}: sealed in round {frozen.get('round')} but no longer in the ledger")
            continue
        if strip_rulings(claim) != frozen:
            errors.append(f"{cid}: changed after its round was sealed; a side answers with a new claim instead")


def strip_rulings(claim):
    out = {}
    for k, v in claim.items():
        if k not in RULING_FIELDS:
            out[k] = v
    return out


def check_links(ledger, root, warnings):
    earlier = ledger.get("supersedes")
    if earlier and resolve(earlier, root) is None:
        warnings.append(f"supersedes {earlier}: not found")


def seal(ledger, root):
    """Freeze every claim of the rounds that are finished."""
    rnd = last_round(ledger)
    claims = {}
    for claim in ledger.get("claims", []):
        if isinstance(claim.get("round"), int) and claim["round"] <= rnd:
            claims[claim["id"]] = strip_rulings(claim)
    sealed_path(root).write_text(json.dumps({"round": rnd, "claims": claims}, indent=2) + "\n")
    return rnd


def sealed_round(root):
    if root is None or not sealed_path(root).is_file():
        return 0
    return json.loads(sealed_path(root).read_text()).get("round", 0)


def check_proofs(ledger, ids, question_ids, errors, warnings):
    proofs = ledger.get("proofs", [])
    if len(proofs) > MAX_PROOFS:
        warnings.append(f"{len(proofs)} proofs; more than {MAX_PROOFS} turns the debate into the project")
    seen = set()
    for proof in proofs:
        pid = proof.get("id")
        if not pid:
            errors.append("proof without an id")
            continue
        if pid in seen or pid in ids or pid in question_ids:
            errors.append(f"{pid}: id used twice")
        seen.add(pid)
        if proof.get("claim") not in ids:
            errors.append(f"{pid}: a proof settles one claim; `claim` must name it")
        if not proof.get("question"):
            errors.append(f"{pid}: `question` is empty")
        if not proof.get("dir"):
            errors.append(f"{pid}: give the scratch directory it runs in, outside the repo")
        if proof.get("status") not in PROOF_STATUSES:
            errors.append(f"{pid}: status must be one of {sorted(PROOF_STATUSES)}")
        cap = proof.get("cap")
        if not isinstance(cap, dict) or not cap.get("minutes") or not cap.get("tokens"):
            errors.append(f"{pid}: set cap.minutes and cap.tokens before it starts")
        else:
            for key, limit in PROOF_CAP.items():
                if cap[key] > limit:
                    warnings.append(f"{pid}: cap of {cap[key]} {key} is over the default {limit}; "
                                    f"the user should agree to it")
        if proof.get("status") == "done":
            fid = proof.get("fact")
            fact = ids.get(fid)
            if not proof.get("result"):
                errors.append(f"{pid}: a done proof needs `result`")
            if fact is None or fact.get("kind") != "fact":
                errors.append(f"{pid}: a done proof records its result as a judge fact; `fact` must name it")
        if proof.get("status") == "abandoned" and not proof.get("result"):
            errors.append(f"{pid}: say in `result` why it was abandoned (for example: cap reached)")


def check_hypothesis(ledger, ids, question_ids, errors):
    hyp = ledger.get("hypothesis")
    if not hyp:
        return
    for field in HYPOTHESIS_FIELDS:
        if not hyp.get(field):
            errors.append(f"hypothesis: `{field}` is empty")
    for ref in hyp.get("claims", []):
        if ref not in ids and ref not in question_ids:
            errors.append(f"hypothesis: unknown claim or question {ref}")


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
        if ruling(claim) in STANDING:
            return False
    return True


def status(ledger, errors, root=None):
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
    pending_proofs = []
    for proof in ledger.get("proofs", []):
        if proof.get("status") in PROOF_PENDING:
            pending_proofs.append(proof.get("id"))
    counts = {}
    for claim in claims:
        key = "concession" if claim.get("kind") == "concession" else ruling(claim) or "unruled"
        counts[key] = counts.get(key, 0) + 1

    if errors:
        step, why = "fix", "the ledger has errors"
    elif rnd == 0:
        step, why = "proponent", "no claims yet; the proponent opens round 1"
    elif proposed_axes:
        step, why = "judge", f"rule on the proposed axes: {', '.join(proposed_axes)}"
    elif unruled:
        step, why = "judge", f"rule on {', '.join(unruled)}"
    elif pending_proofs:
        step, why = "proof", f"finish {', '.join(pending_proofs)} within its cap, then add the result as a fact"
    elif unanswered:
        step, why = "ask-user", f"answer {', '.join(unanswered)} before the next round"
    elif ledger.get("max_tokens") and debate_tokens(ledger) >= ledger["max_tokens"]:
        step, why = "settle", f"the debate's token budget of {ledger['max_tokens']} is spent"
    elif (converged(ledger) or rnd >= max_rounds) and ledger.get("research") and not ledger.get("hypothesis"):
        step, why = "judge", "write the hypothesis (metric, baseline, threshold, kill) before settling"
    elif converged(ledger):
        step, why = "settle", f"round {rnd} added nothing that stands"
    elif rnd >= max_rounds:
        step, why = "settle", f"round cap {max_rounds} reached; open claims become open risks"
    elif not has_side(ledger, rnd, "opponent"):
        step, why = "opponent", f"the opponent has not answered round {rnd}"
    elif sealed_round(root) < rnd:
        step, why = "seal", f"seal round {rnd} before the next one opens"
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
        "pending_proofs": pending_proofs,
        "converged": converged(ledger),
        "next": step,
        "why": why,
        "debate_tokens": debate_tokens(ledger),
        "max_tokens": ledger.get("max_tokens"),
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
        if claim.get("kind") in ("proposal", "alternative") and ruling(claim) == "upheld":
            structure.append(f"- {claim['id']}: {claim['text']}{estimate_text(claim)}")
            for other in claims:
                if other.get("kind") == "concession" and claim["id"] in other.get("answers", []):
                    structure.append(f"  - amended by {other['id']}: {other['text']}")
    lines += structure or ["- (nothing upheld)"]
    lines.append("")

    hyp = ledger.get("hypothesis")
    if hyp:
        lines += ["## Hypothesis", ""]
        for field in HYPOTHESIS_FIELDS:
            lines.append(f"- {field}: {hyp.get(field)}")
        lines.append("")

    lines += ["## Budget by axis", ""]
    for axis in axes(ledger):
        rows = []
        for claim in claims:
            if claim.get("axis") != axis or ruling(claim) != "upheld":
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
        if ruling(claim) != "rejected" or claim.get("kind") not in ("proposal", "alternative"):
            continue
        killers = []
        for other in claims:
            if claim["id"] in other.get("answers", []) and ruling(other) == "upheld":
                killers.append(other["id"])
        reason = claim.get("ruling_why", "")
        by = f" (by {', '.join(killers)})" if killers else ""
        rejected.append(f"- {claim['id']}: {claim['text']}. Why not: {reason}{by}")
    lines += rejected or ["- (none)"]
    lines.append("")

    if ledger.get("roadmap"):
        lines += [f"## Scope changes to {ledger['roadmap']}", ""]
        cuts = []
        for claim in claims:
            if claim.get("kind") == "cut" and ruling(claim) == "upheld":
                cuts.append(f"- {claim.get('action')} {', '.join(claim.get('nodes', []))}: {claim['text']} ({claim['id']})")
        lines += cuts or ["- (none)"]
        lines.append("")

    lines += ["## Open risks", ""]
    risks = []
    for claim in claims:
        if ruling(claim) == "open":
            risks.append(f"- {claim['id']} ({claim.get('axis') or claim.get('kind')}): {claim['text']}. "
                         f"Open because: {claim.get('ruling_why', '')}")
    lines += risks or ["- (none)"]
    lines.append("")

    proofs = ledger.get("proofs", [])
    if proofs:
        lines += ["## Proofs", ""]
        for proof in proofs:
            cap = proof.get("cap") or {}
            lines.append(f"- {proof.get('id')} for {proof.get('claim')}: {proof.get('question')} "
                         f"({proof.get('status')}, cap {cap.get('minutes')} min, {cap.get('tokens')} tokens). "
                         f"Result: {proof.get('result') or 'none yet'}")
        lines.append("")

    lines += ["## Overruled", ""]
    overruled = []
    for claim in claims:
        if claim.get("user_ruling"):
            overruled.append(f"- {claim['id']}: judge {claim.get('ruling')}, user {claim['user_ruling']}. "
                             f"Why: {claim.get('user_why', '')}")
    lines += overruled or ["- (none)"]
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
              + (f", about {tokens} tokens" if tokens else "")
              + (f" of a {ledger['max_tokens']} budget" if ledger.get("max_tokens") else "")]
    if ledger.get("supersedes"):
        lines.append(f"- supersedes {ledger['supersedes']}")
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
    ap.add_argument("command", nargs="?", default="status", choices=["init", "check", "status", "seal", "report"])
    ap.add_argument("--goal", default="")
    ap.add_argument("--max-rounds", type=int, default=DEFAULT_MAX_ROUNDS)
    ap.add_argument("--max-tokens", type=int, default=None,
                    help="init: the debate's own token budget; status says settle once it is spent")
    ap.add_argument("--roadmap", default=None, help="init: an existing roadmap the debate weighs and may cut")
    ap.add_argument("--supersedes", default=None, help="init: the earlier debate this one replaces")
    ap.add_argument("--research", action="store_true",
                    help="init: the goal tests an idea; a hypothesis is required before settling")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "init":
        path = ledger_path(args.root)
        if path.exists():
            sys.exit(f"{path}: already exists")
        if not args.goal:
            sys.exit("init needs --goal")
        args.root.mkdir(parents=True, exist_ok=True)
        ledger = {"goal": args.goal, "research": args.research, "max_rounds": args.max_rounds,
                  "max_tokens": args.max_tokens, "roadmap": args.roadmap, "supersedes": args.supersedes,
                  "extra_axes": [], "claims": [], "questions": [], "proofs": [], "hypothesis": None,
                  "spend": []}
        path.write_text(json.dumps(ledger, indent=2) + "\n")
        print(f"wrote {path}")
        return

    ledger = load(args.root)
    errors, warnings = check(ledger, args.root)

    if args.command == "seal":
        if errors:
            print_check(errors, warnings)
            sys.exit(1)
        print(f"sealed rounds 1 to {seal(ledger, args.root)}")
        return

    if args.command == "check":
        if args.json:
            print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
        else:
            print_check(errors, warnings)
        sys.exit(1 if errors else 0)

    if args.command == "status":
        result = status(ledger, errors, args.root)
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

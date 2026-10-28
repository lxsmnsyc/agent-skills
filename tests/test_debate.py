"""Tests for skills/goal-debate/scripts/debate.py. Run: python3 -m unittest discover tests"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DEBATE = Path(__file__).resolve().parents[1] / "skills/goal-debate/scripts/debate.py"


def fact(cid, rnd, axis="device"):
    return {"id": cid, "round": rnd, "by": "judge", "kind": "fact", "axis": axis, "text": "8 GB RAM",
            "evidence": {"type": "measured", "source": "capacity.py --json"}, "ruling": "upheld"}


def proposal(cid, rnd, ruling="upheld"):
    claim = {"id": cid, "round": rnd, "by": "proponent", "kind": "proposal", "text": "batch job",
             "evidence": {"type": "estimate"}}
    if ruling:
        claim["ruling"] = ruling
    if ruling in ("rejected", "open"):
        claim["ruling_why"] = "because"
    return claim


def cost(cid, rnd, answers, ruling="upheld", axis="time", severity="high", evidence="measured"):
    claim = {"id": cid, "round": rnd, "by": "opponent", "kind": "cost", "axis": axis, "severity": severity,
             "answers": answers, "text": "33 hours", "evidence": {"type": evidence, "source": "sample run"}}
    if ruling:
        claim["ruling"] = ruling
    if ruling in ("rejected", "open"):
        claim["ruling_why"] = "because"
    return claim


class DebateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "debate"
        self.run_debate("init", "--goal", "caption photos", "--max-rounds", "3")

    def tearDown(self):
        self.tmp.cleanup()

    def run_debate(self, *args, check=True):
        return subprocess.run([sys.executable, str(DEBATE), str(self.dir), *args],
                              capture_output=True, text=True, check=check)

    def write(self, **fields):
        path = self.dir / "ledger.json"
        ledger = json.loads(path.read_text())
        ledger.update(fields)
        path.write_text(json.dumps(ledger))

    def status(self):
        return json.loads(self.run_debate("status", "--json").stdout)

    def test_empty_ledger_starts_with_proponent(self):
        self.assertEqual(self.status()["next"], "proponent")

    def test_unruled_claims_go_to_judge(self):
        self.write(claims=[proposal("P1", 1, ruling=None)])
        out = self.status()
        self.assertEqual(out["next"], "judge")
        self.assertEqual(out["unruled"], ["P1"])

    def test_opponent_answers_after_proponent(self):
        self.write(claims=[fact("J1", 1), proposal("P1", 1)])
        self.assertEqual(self.status()["next"], "opponent")

    def test_unanswered_question_goes_to_user(self):
        self.write(claims=[proposal("P1", 1), cost("O1", 1, ["P1"])],
                   questions=[{"id": "Q1", "by": "opponent", "ask": "Deadline?", "blocks": ["O1"]}])
        self.assertEqual(self.status()["next"], "ask-user")

    def test_round_with_nothing_standing_settles(self):
        concession = {"id": "P2", "round": 2, "by": "proponent", "kind": "concession", "answers": ["P1"],
                      "why": "O1", "text": "chunk it"}
        self.write(claims=[proposal("P1", 1), cost("O1", 1, ["P1"]), concession,
                           cost("O2", 2, ["P1"], ruling="rejected")])
        out = self.status()
        self.assertTrue(out["converged"])
        self.assertEqual(out["next"], "settle")

    def test_round_cap_settles(self):
        self.write(max_rounds=1, claims=[proposal("P1", 1), cost("O1", 1, ["P1"])])
        self.assertEqual(self.status()["next"], "settle")

    def test_new_standing_claim_opens_next_round(self):
        self.write(claims=[proposal("P1", 1), cost("O1", 1, ["P1"])])
        self.assertEqual(self.status()["next"], "seal")
        self.run_debate("seal")
        self.assertEqual(self.status()["next"], "proponent")

    def test_check_errors(self):
        bad_concession = {"id": "P2", "round": 1, "by": "proponent", "kind": "concession",
                          "answers": ["O1"], "text": "fine"}
        judge_proposal = dict(proposal("J1", 1), by="judge")
        self.write(claims=[proposal("P1", 1), cost("O1", 1, ["P1"], axis="security"),
                           bad_concession, judge_proposal, cost("O3", 1, ["P9"])])
        result = self.run_debate("check", "--json", check=False)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("axis `security`", errors)
        self.assertIn("own side", errors)
        self.assertIn("changed the side's mind", errors)
        self.assertIn("only adds facts", errors)
        self.assertIn("unknown claim P9", errors)

    def test_accepted_extra_axis_is_allowed(self):
        self.write(extra_axes=[{"name": "security", "by": "proponent", "why": "auth", "status": "accepted"}],
                   claims=[proposal("P1", 1), cost("O1", 1, ["P1"], axis="security")])
        self.assertEqual(self.run_debate("check").returncode, 0)

    def test_proposed_axis_goes_to_judge(self):
        self.write(extra_axes=[{"name": "security", "by": "proponent", "why": "auth", "status": "proposed"}],
                   claims=[proposal("P1", 1)])
        self.assertEqual(self.status()["next"], "judge")

    def test_high_cost_on_estimate_warns(self):
        self.write(claims=[proposal("P1", 1), cost("O1", 1, ["P1"], evidence="estimate")])
        warnings = json.loads(self.run_debate("check", "--json").stdout)["warnings"]
        self.assertTrue(any("spike" in w for w in warnings))

    def test_user_evidence_needs_answer(self):
        claim = cost("O1", 1, ["P1"])
        claim["evidence"] = {"type": "user", "question": "Q1"}
        self.write(claims=[proposal("P1", 1), claim],
                   questions=[{"id": "Q1", "by": "opponent", "ask": "Deadline?"}])
        result = self.run_debate("check", check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not answered", result.stdout)

    def test_report_lists_rejected_with_killer(self):
        alt = {"id": "P2", "round": 1, "by": "proponent", "kind": "alternative", "text": "cloud API",
               "evidence": {"type": "source", "source": "price list"}, "ruling": "rejected",
               "ruling_why": "sends photos off the machine"}
        self.write(claims=[fact("J1", 1), proposal("P1", 1), alt, cost("O1", 1, ["P2"], axis="tokens")],
                   spend=[{"round": 1, "tokens": 1000}])
        out = self.run_debate("report").stdout
        self.assertIn("- P2: cloud API. Why not: sends photos off the machine (by O1)", out)
        self.assertIn("about 1000 tokens", out)
        self.assertIn("- P1: batch job", out)


    def test_pending_proof_comes_before_user_questions(self):
        self.write(claims=[proposal("P1", 1), cost("O1", 1, ["P1"], ruling="open")],
                   questions=[{"id": "Q1", "by": "opponent", "ask": "Deadline?"}],
                   proofs=[{"id": "T1", "claim": "O1", "question": "Fits in 8 GB?", "dir": "/tmp/x",
                            "status": "planned", "cap": {"minutes": 30, "tokens": 100000}}])
        self.assertEqual(self.status()["next"], "proof")

    def test_proof_checks(self):
        self.write(claims=[proposal("P1", 1)],
                   proofs=[{"id": "T1", "claim": "P1", "question": "q", "dir": "/tmp/x", "status": "done",
                            "result": "fits", "cap": {"minutes": 90, "tokens": 100000}},
                           {"id": "T2", "claim": "P9", "question": "q", "dir": "/tmp/y", "status": "planned"}])
        out = json.loads(self.run_debate("check", "--json", check=False).stdout)
        errors, warnings = "\n".join(out["errors"]), "\n".join(out["warnings"])
        self.assertIn("T1: a done proof records its result as a judge fact", errors)
        self.assertIn("T2: a proof settles one claim", errors)
        self.assertIn("T2: set cap.minutes", errors)
        self.assertIn("over the default 30", warnings)

    def test_prior_art_needs_source(self):
        claim = proposal("P1", 1)
        claim["evidence"] = {"type": "prior-art"}
        self.write(claims=[claim])
        result = self.run_debate("check", check=False)
        self.assertIn("prior-art evidence needs a source", result.stdout)

    def test_research_goal_needs_hypothesis_to_settle(self):
        self.write(research=True, max_rounds=1, claims=[proposal("P1", 1), cost("O1", 1, ["P1"])])
        self.assertEqual(self.status()["next"], "judge")
        self.write(hypothesis={"statement": "s", "metric": "m", "baseline": "b", "threshold": "t", "kill": "k"})
        self.assertEqual(self.status()["next"], "settle")
        self.assertIn("## Hypothesis", self.run_debate("report").stdout)

    def test_sealed_claims_cannot_change(self):
        self.write(claims=[proposal("P1", 1), cost("O1", 1, ["P1"])])
        self.run_debate("seal")
        changed = cost("O1", 1, ["P1"], severity="low", ruling="rejected")
        self.write(claims=[proposal("P1", 1, ruling="open"), changed])
        result = self.run_debate("check", check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("O1: changed after its round was sealed", result.stdout)
        self.assertNotIn("P1: changed", result.stdout)

    def test_user_overrule_counts_and_is_reported(self):
        alt = {"id": "P2", "round": 1, "by": "proponent", "kind": "alternative", "text": "cloud API",
               "evidence": {"type": "source", "source": "price list"}, "ruling": "rejected",
               "ruling_why": "privacy", "user_ruling": "upheld", "user_why": "thumbnails only are fine"}
        self.write(claims=[proposal("P1", 1), alt])
        out = self.run_debate("report").stdout
        self.assertIn("- P2: cloud API", out.split("## Hypothesis")[0].split("## Budget")[0])
        self.assertIn("P2: judge rejected, user upheld. Why: thumbnails only are fine", out)
        alt.pop("user_why")
        self.write(claims=[proposal("P1", 1), alt])
        self.assertIn("user_why", self.run_debate("check", check=False).stdout)

    def test_token_budget_settles(self):
        self.write(max_tokens=1000, spend=[{"round": 1, "tokens": 1200}],
                   claims=[proposal("P1", 1), cost("O1", 1, ["P1"])])
        out = self.status()
        self.assertEqual(out["next"], "settle")
        self.assertIn("token budget", out["why"])

    def test_hypothesis_may_cite_questions(self):
        self.write(claims=[proposal("P1", 1)],
                   questions=[{"id": "Q1", "by": "opponent", "ask": "Deadline?", "answer": "2 weeks"}],
                   hypothesis={"statement": "s", "metric": "m", "baseline": "b", "threshold": "t",
                               "kill": "k", "claims": ["P1", "Q1"]})
        self.assertEqual(self.run_debate("check").returncode, 0)

    def test_cuts_check_the_roadmap(self):
        roadmap = Path(self.tmp.name) / "roadmap"
        for nid, status in (("a", "todo"), ("b", "active"), ("c", "done")):
            (roadmap / "nodes" / nid).mkdir(parents=True)
            (roadmap / "nodes" / nid / "brief.md").write_text(f"---\nid: {nid}\nstatus: {status}\n---\n")

        def cut(cid, nodes, action="park"):
            return {"id": cid, "round": 1, "by": "opponent", "kind": "cut", "action": action, "nodes": nodes,
                    "text": "no player sees it before 1.0", "evidence": {"type": "source", "source": "plan.py overview"},
                    "ruling": "upheld"}
        self.write(roadmap=str(roadmap), claims=[cut("O1", ["a"]), cut("O2", ["b"]), cut("O3", ["c", "zz"], "fly")])
        out = json.loads(self.run_debate("check", "--json", check=False).stdout)
        errors, warnings = "\n".join(out["errors"]), "\n".join(out["warnings"])
        self.assertIn("O3: node c is already done", errors)
        self.assertIn("O3: node zz is not in", errors)
        self.assertIn("O3: a cut needs action", errors)
        self.assertIn("O2: node b is active", warnings)
        self.assertNotIn("O1", errors)
        self.write(claims=[cut("O1", ["a"])])
        self.assertIn("- park a: no player sees it before 1.0 (O1)", self.run_debate("report").stdout)

if __name__ == "__main__":
    unittest.main()

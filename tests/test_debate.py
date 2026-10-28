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


if __name__ == "__main__":
    unittest.main()

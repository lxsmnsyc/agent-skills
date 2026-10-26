"""Tests for skills/parallel-roadmap/scripts/plan.py. Run: python3 -m unittest discover tests"""
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/parallel-roadmap/scripts"))
import plan  # noqa: E402


def node(root, nid, **fm):
    lines = [f"id: {nid}"]
    for k, v in fm.items():
        lines.append(f"{k}: {v}" if not isinstance(v, str) or "\n" not in v else f"{k}:\n{v}")
    d = root / "nodes" / nid
    d.mkdir(parents=True)
    (d / "brief.md").write_text("---\n" + "\n".join(lines) + "\n---\n")


def contract(root, name, status="frozen", defined_by=None):
    (root / "contracts").mkdir(exist_ok=True)
    extra = f"\ndefined_by: {defined_by}" if defined_by else ""
    (root / "contracts" / f"{name}.md").write_text(f"---\nname: {name}\nstatus: {status}{extra}\n---\n")


def dep(on, kind, via=None, why=None):
    out = f"  - on: {on}\n    kind: {kind}"
    if via:
        out += f"\n    via: {via}"
    if why:
        out += f"\n    why: {why}"
    return out


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "nodes").mkdir()
        (self.root / "contracts").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def load(self):
        nodes, contracts, errs = plan.load(self.root)
        return nodes, contracts, plan.check(nodes, contracts, errs)

    def test_frontmatter_subset(self):
        text = textwrap.dedent("""\
            ---
            id: a  # comment
            owns: [src/a/**, src/b.ts]
            depends_on:
              - on: b
                kind: hard
                why: "needs: b"
            gate: true
            ---
            """)
        fm = plan.parse_frontmatter(text, "t")
        self.assertEqual(fm["id"], "a")
        self.assertEqual(fm["owns"], ["src/a/**", "src/b.ts"])
        self.assertEqual(fm["depends_on"], [{"on": "b", "kind": "hard", "why": "needs: b"}])
        self.assertIs(fm["gate"], True)

    def test_contract_dependency_starts_after_freeze(self):
        contract(self.root, "api", status="draft", defined_by="c")
        node(self.root, "c", size="S", owns="[src/api.ts]", provides="[api]")
        node(self.root, "a", size="M", owns="[src/a/**]", depends_on=dep("c", "contract", via="api"))
        nodes, contracts, (errors, _) = self.load()
        self.assertEqual(errors, [])
        s = plan.schedule(nodes, contracts, 4)
        self.assertEqual(s["waves"], [["c"], ["a"]])

    def test_cycle_is_an_error(self):
        node(self.root, "a", size="S", owns="[a]", depends_on=dep("b", "hard", why="x"))
        node(self.root, "b", size="S", owns="[b]", depends_on=dep("a", "hard", why="x"))
        _, _, (errors, _) = self.load()
        self.assertTrue(any(e.startswith("cycle") for e in errors))

    def test_duplicate_reservation_is_an_error(self):
        node(self.root, "a", size="S", owns="[a]", reserves="[migration 0043]")
        node(self.root, "b", size="S", owns="[b]", reserves="[migration 0043]")
        _, _, (errors, _) = self.load()
        self.assertTrue(any("already reserved" in e for e in errors))

    def test_owned_path_overlap_defers(self):
        node(self.root, "a", size="M", owns="[src/auth/**]")
        node(self.root, "b", size="S", owns="[src/auth/login.ts]")
        nodes, contracts, _ = self.load()
        s = plan.schedule(nodes, contracts, 4)
        self.assertEqual(len(s["waves"]), 2)

    def test_exclusive_resource_defers(self):
        node(self.root, "a", size="S", owns="[a/**]", exclusive="[loadtest]")
        node(self.root, "b", size="S", owns="[b/**]", exclusive="[loadtest]")
        nodes, contracts, _ = self.load()
        self.assertEqual(len(plan.schedule(nodes, contracts, 4)["waves"]), 2)

    def test_priority_promotion_and_order(self):
        node(self.root, "low", size="S", owns="[low]", priority="could")
        node(self.root, "top", size="S", owns="[top]", priority="must",
             depends_on=dep("low", "hard", why="x"))
        node(self.root, "other", size="S", owns="[other]", priority="could")
        nodes, contracts, (_, warnings) = self.load()
        self.assertTrue(any("node low" in w and "must" in w for w in warnings))
        self.assertEqual(plan.ready(nodes, contracts)[0], "low")

    def test_later_is_parked(self):
        node(self.root, "a", size="S", owns="[a]", priority="later")
        nodes, contracts, _ = self.load()
        self.assertEqual(plan.schedule(nodes, contracts, 4)["parked"], ["a"])
        self.assertEqual(plan.ready(nodes, contracts), [])

    def test_impact_ignores_done_nodes(self):
        node(self.root, "old", size="S", owns="[src/**]", status="done", fulfilled_by="abc123")
        node(self.root, "new", size="S", owns="[src/x.ts]")
        nodes, contracts, _ = self.load()
        self.assertEqual(plan.impact("new", nodes, contracts, 4)["overlaps"], [])

    def test_verify_runs_command(self):
        node(self.root, "ok", size="S", owns="[a]", verify="true")
        node(self.root, "bad", size="S", owns="[b]", verify='"false"')
        nodes, _, _ = self.load()
        res = {r["id"]: r["result"] for r in plan.verify(["ok", "bad"], nodes, ".", 30)}
        self.assertEqual(res["ok"], "pass")
        self.assertTrue(res["bad"].startswith("fail"))

    def test_small_hard_chain_warns(self):
        node(self.root, "a", size="S", owns="[src/x/**]")
        node(self.root, "b", size="S", owns="[src/x/y.ts]", depends_on=dep("a", "hard", why="x"))
        _, _, (_, warnings) = self.load()
        self.assertTrue(any("merge them into one node" in w for w in warnings))

    def test_shared_file_in_same_wave_is_reported(self):
        node(self.root, "a", size="M", owns="[src/a/**]", shared="[src/core.ts]")
        node(self.root, "b", size="M", owns="[src/b/**]", shared="[src/core.ts]")
        nodes, contracts, _ = self.load()
        s = plan.schedule(nodes, contracts, 4)
        self.assertEqual(len(s["waves"]), 1)
        self.assertEqual(s["shared"][0], [("src/core.ts", ["a", "b"])])

    def test_merge_order_follows_priority(self):
        node(self.root, "low", size="M", owns="[src/l/**]", shared="[src/core.ts]", priority="could")
        node(self.root, "high", size="M", owns="[src/h/**]", shared="[src/core.ts]", priority="must")
        nodes, contracts, _ = self.load()
        s = plan.schedule(nodes, contracts, 4)
        self.assertEqual(s["shared"][0][0], ("src/core.ts", ["high", "low"]))

    def test_hot_file_warns(self):
        for i in range(plan.HOT_FILE_NODES):
            node(self.root, f"n{i}", size="M", owns=f"[src/n{i}/**]", shared="[src/zone.go]")
        _, _, (_, warnings) = self.load()
        self.assertTrue(any("src/zone.go is edited by 4 open nodes" in w for w in warnings))

    def goal_with_branches(self):
        (self.root / "GOAL.md").write_text(
            "---\nbranches:\n  feature: dev\n  fix: dev\n  hotfix: main\n"
            "  promote: dev -> next -> main\n---\n# Goal\n")

    def test_branch_policy_sets_targets(self):
        self.goal_with_branches()
        node(self.root, "f", size="M", owns="[src/f/**]", type="feature")
        node(self.root, "h", size="S", owns="[src/h/**]", type="hotfix")
        node(self.root, "x", size="S", owns="[src/x/**]", target="next")
        nodes, contracts, errs = plan.load(self.root)
        policy = plan.load_policy(self.root)
        self.assertEqual(policy["promote"], ["dev", "next", "main"])
        plan.apply_targets(nodes, policy)
        self.assertEqual({k: n["target_eff"] for k, n in nodes.items()},
                         {"f": "dev", "h": "main", "x": "next"})
        errors, warnings = plan.check(nodes, contracts, errs, policy)
        self.assertEqual(errors, [])

    def test_release_node_must_wait_for_open_work(self):
        self.goal_with_branches()
        node(self.root, "f", size="M", owns="[src/f/**]", type="feature")
        node(self.root, "rel", size="S", owns="[CHANGELOG.md]", type="release", **{"from": "dev"},
             target="next")
        nodes, contracts, errs = plan.load(self.root)
        policy = plan.load_policy(self.root)
        plan.apply_targets(nodes, policy)
        _, warnings = plan.check(nodes, contracts, errs, policy)
        self.assertTrue(any("does not wait for open work on dev: f" in w for w in warnings))

    def test_released_counts_as_done(self):
        node(self.root, "a", size="S", owns="[a]", status="released", fulfilled_by="v1.2.0")
        node(self.root, "b", size="S", owns="[b]", depends_on=dep("a", "hard", why="x"))
        nodes, contracts, (errors, _) = self.load()
        self.assertEqual(errors, [])
        self.assertEqual(plan.ready(nodes, contracts), ["b"])

    def test_large_plan_of_sized_nodes_does_not_warn(self):
        for i in range(30):
            node(self.root, f"n{i}", size="M", owns=f"[src/n{i}/**]")
        _, _, (_, warnings) = self.load()
        self.assertEqual(warnings, [])

if __name__ == "__main__":
    unittest.main()

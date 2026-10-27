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

    def test_outline_nodes_are_not_ready_and_skip_shape_checks(self):
        node(self.root, "near", size="M", owns="[src/a/**]")
        node(self.root, "far", size="XL", outline="true", depends_on=dep("near", "hard", why="x"))
        nodes, contracts, (errors, warnings) = self.load()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])  # no "split XL" or "no owned paths" for an outline
        self.assertEqual(plan.ready(nodes, contracts), ["near"])
        self.assertEqual(plan.refine_due(nodes, contracts, horizon=2), ["far"])
        self.assertEqual(plan.refine_due(nodes, contracts, horizon=1), [])

    def test_milestone_groups(self):
        (self.root / "GOAL.md").write_text("---\nmilestones: [q1, q2]\n---\n# Goal\n")
        node(self.root, "a", size="M", owns="[a/**]", milestone="q1")
        node(self.root, "b", size="M", owns="[b/**]", milestone="q2", outline="true",
             depends_on=dep("a", "hard", why="x"))
        node(self.root, "c", size="M", owns="[c/**]", milestone="q3")
        nodes, contracts, errs = plan.load(self.root)
        _, warnings = plan.check(nodes, contracts, errs, milestones=plan.goal_milestones(self.root))
        self.assertTrue(any("milestone 'q3' is not in GOAL.md" in w for w in warnings))
        groups = plan.schedule(nodes, contracts, 4)["groups"]
        self.assertEqual(groups["q1"]["last_wave"], 1)
        self.assertEqual(groups["q2"], {"open": 1, "outline": 1, "done": 0, "last_wave": 2})

    def test_overview_groups_by_milestone(self):
        (self.root / "GOAL.md").write_text(
            "---\nmilestones: [q1, q2]\n---\n# Sync\n\n## Outcome\n\nEdits sync.\n")
        node(self.root, "a", size="M", owns="[a/**]", milestone="q1", priority="must", title="API")
        node(self.root, "b", size="L", milestone="q2", outline="true", title="Offline",
             depends_on=dep("a", "hard", why="x"))
        nodes, contracts, (errors, warnings) = self.load()
        s = plan.schedule(nodes, contracts, 4)
        text = plan.overview(self.root, nodes, contracts, s, plan.goal_milestones(self.root), warnings)
        self.assertIn("# Sync", text)
        self.assertIn("Edits sync.", text)
        self.assertLess(text.index("## q1"), text.index("## q2"))
        self.assertIn("- [ ] **a**: API [must, M, wave 1]", text)
        self.assertIn("**b**: Offline [should, L, outline, wave 2] (after a)", text)

    def merge_setup(self, mode="auto"):
        (self.root / "GOAL.md").write_text(f"---\nmerge:\n  mode: {mode}\n  max_size: M\n---\n# G\n")
        node(self.root, "f", size="M", status="active", type="feature", owns="[src/f/**]")
        node(self.root, "x", size="M", status="active", type="fix", owns="[src/x/**]")
        node(self.root, "big", size="L", status="active", type="feature", owns="[src/b/**]")
        node(self.root, "g", size="S", status="active", gate="true", owns="[src/g/**]")
        nodes, _, _ = plan.load(self.root)
        return nodes, plan.merge_policy(self.root)

    def test_can_merge_clean_feature(self):
        nodes, pol = self.merge_setup()
        r = plan.can_merge("f", nodes, pol, True, True, False,
                           ["src/f/a.ts", "docs/roadmaps/r/nodes/f/outcome.md"])
        self.assertEqual(r["verdict"], "auto", r["reasons"])

    def test_can_merge_refuses(self):
        nodes, pol = self.merge_setup()
        cases = {
            "x": (True, True, False, ["src/x/a.ts"], "proof"),
            "big": (True, True, False, ["src/b/a.ts"], "above the limit"),
            "g": (True, True, False, ["src/g/a.ts"], "gated"),
            "f": (False, True, False, ["src/f/a.ts"], "review is not clean"),
        }
        for nid, (clean, checks, proof, files, why) in cases.items():
            r = plan.can_merge(nid, nodes, pol, clean, checks, proof, files)
            self.assertEqual(r["verdict"], "maintainer", nid)
            self.assertTrue(any(why in reason for reason in r["reasons"]), (nid, r["reasons"]))
        r = plan.can_merge("f", nodes, pol, True, True, False, ["src/other.ts"])
        self.assertTrue(any("outside the node's paths" in x for x in r["reasons"]))
        r = plan.can_merge("f", nodes, pol, True, True, False, ["src/f/a.ts"], ci_guard="ask")
        self.assertEqual(r["verdict"], "maintainer")

    def test_merge_mode_defaults_to_maintainer(self):
        nodes, pol = self.merge_setup(mode="maintainer")
        self.assertEqual(plan.merge_policy(self.root)["mode"], "maintainer")
        r = plan.can_merge("f", nodes, pol, True, True, False, ["src/f/a.ts"])
        self.assertEqual(r["verdict"], "maintainer")
        (self.root / "GOAL.md").write_text("# G\n")
        self.assertEqual(plan.merge_policy(self.root)["mode"], "maintainer")

    def test_run_mode(self):
        self.assertEqual(plan.run_mode(self.root, 4), "parallel")
        self.assertEqual(plan.run_mode(self.root, 1), "sequential")
        (self.root / "GOAL.md").write_text("---\nrun: sequential\n---\n# G\n")
        self.assertEqual(plan.run_mode(self.root, 4), "sequential")

    def test_review_mode(self):
        node(self.root, "small", size="S", owns="[a/**]")
        node(self.root, "mid", size="M", owns="[b/**]")
        node(self.root, "notes", size="M", owns="[c/**]", type="docs")
        node(self.root, "gated", size="S", owns="[d/**]", gate="true")
        nodes, _, _ = self.load()
        modes = {k: plan.review_mode(nodes[k]) for k in nodes}
        self.assertEqual(modes, {"small": "self", "mid": "fresh", "notes": "self", "gated": "fresh"})
        self.assertEqual(plan.review_mode(nodes["mid"], "self"), "self")
        self.assertEqual(plan.review_setting(self.root), "auto")
        (self.root / "GOAL.md").write_text("---\nreview: fresh\n---\n# G\n")
        self.assertEqual(plan.review_setting(self.root), "fresh")

    def test_self_review_blocks_auto_merge(self):
        nodes, pol = self.merge_setup()
        r = plan.can_merge("f", nodes, pol, True, True, False, ["src/f/a.ts"], review="self")
        self.assertEqual(r["verdict"], "maintainer")
        r = plan.can_merge("f", nodes, pol, True, True, False, ["src/f/a.ts"], review="self", fresh_review=True)
        self.assertEqual(r["verdict"], "auto")

    def test_archive_only_what_nothing_open_needs(self):
        contract(self.root, "api", status="frozen")
        node(self.root, "a", size="M", owns="[a/**]", status="done", milestone="q1", provides="[api]")
        (self.root / "nodes/a/outcome.md").write_text("Built in #57.\n")
        node(self.root, "b", size="M", owns="[b/**]", status="done")
        node(self.root, "c", size="M", owns="[c/**]", depends_on=dep("b", "hard", why="x"))
        nodes, contracts, _ = self.load()
        ids, unused = plan.archive_candidates(nodes, contracts)
        self.assertEqual(ids, ["a"])  # b is still needed by open node c
        self.assertEqual(unused, ["api"])
        plan.apply_archive(self.root, nodes, ids)
        self.assertFalse((self.root / "nodes/a").exists())
        self.assertIn("- a: a (done, #57, milestone q1)", (self.root / "archive.md").read_text())

    def test_archived_nodes_still_satisfy_dependencies(self):
        (self.root / "archive.md").write_text("# Archive\n\n- old: Old work (done, #12)\n")
        node(self.root, "new", size="M", owns="[n/**]", depends_on=dep("old", "hard", why="x"))
        nodes, contracts, (errors, warnings) = self.load()
        self.assertEqual(errors, [])
        self.assertTrue(nodes["old"]["archived"])
        self.assertEqual(plan.ready(nodes, contracts), ["new"])
        s = plan.schedule(nodes, contracts, 4)
        text = plan.overview(self.root, nodes, contracts, s, None, warnings)
        self.assertIn("- [x] **old**: Old work [archived]", text)

    def test_branch_and_title_from_node(self):
        node(self.root, "frame-writer", size="M", owns="[a/**]", type="feature", title="Frame writer with byte parity")
        node(self.root, "subtotal", size="S", owns="[b/**]", type="fix", title="Subtotal skips the first item")
        node(self.root, "probe", size="S", owns="[c/**]", spike="true", title="Measure a Lua state")
        nodes, _, _ = self.load()
        self.assertEqual(plan.branch_name(nodes["frame-writer"]), "feat/frame-writer")
        self.assertEqual(plan.pr_title(nodes["frame-writer"]), "feat: frame writer with byte parity")
        self.assertEqual(plan.branch_name(nodes["subtotal"]), "fix/subtotal")
        self.assertEqual(plan.branch_name(nodes["probe"]), "spike/probe")

    def test_large_plan_of_sized_nodes_does_not_warn(self):
        for i in range(30):
            node(self.root, f"n{i}", size="M", owns=f"[src/n{i}/**]")
        _, _, (_, warnings) = self.load()
        self.assertEqual(warnings, [])

if __name__ == "__main__":
    unittest.main()

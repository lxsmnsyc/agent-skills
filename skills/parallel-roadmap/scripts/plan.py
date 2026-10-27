#!/usr/bin/env python3
"""Validate a parallel roadmap, schedule it into waves, and assemble node context.

Reads <root>/nodes/*/brief.md and <root>/contracts/*.md frontmatter. Stdlib only.

Usage:
  plan.py <root> status            # check + waves + critical path (default)
  plan.py <root> check             # validation only, exit 1 on errors
  plan.py <root> waves             # wave schedule
  plan.py <root> ready             # nodes that can start now
  plan.py <root> context <id>      # files an agent working on <id> should load
  plan.py <root> impact <id>       # what adding or changing <id> does to the plan
  plan.py <root> verify [<id>]     # run the verify command of <id>, or of every todo node
  plan.py <root> refine            # outline nodes close enough to break into briefs now
  plan.py <root> overview          # readable summary of the plan, grouped by milestone
  plan.py <root> archive [--apply]   # done nodes nothing open needs: remove folders, list in archive.md
  plan.py <root> can-merge <id> --review-clean --checks-pass [--proof] [--fresh-review] --files - < changed.txt
                                   # may the orchestrator merge this node's PR itself? exit 0 = yes
Options: --json, --max-parallel N (default 4; 1, or `run: sequential` in GOAL.md, means sequential), --budget TOKENS (default 20000),
         --upto must|should|could|later (default could: schedule everything except parked work)
"""
import argparse
import fnmatch
import json
import shutil
import os
import re
import subprocess
import sys
from pathlib import Path

SIZE_POINTS = {"S": 1, "M": 2, "L": 3, "XL": 5}
DEFAULT_MODEL = {"S": "sonnet", "M": "sonnet", "L": "opus", "XL": "opus"}
KINDS = {"contract", "behavior", "hard"}
STATUSES = {"todo", "active", "done", "released", "dropped"}
DONE = {"done", "released"}
TYPES = {"feature", "fix", "hotfix", "refactor", "docs", "chore", "release", "spike", "contract"}
# must: needed for the goal now. should: important, but the goal can ship without it.
# could: worth doing when capacity is free. later: parked, not scheduled.
PRIORITIES = {"must": 0, "should": 1, "could": 2, "later": 3}
PRIORITY_NAMES = {v: k for k, v in PRIORITIES.items()}
DEFAULT_MAX_PARALLEL = 4
# Outline nodes this many waves ahead (or closer) are due to be broken into briefs.
DEFAULT_HORIZON = 2
CONTRACT_STATUSES = {"draft", "frozen"}


# ---------------------------------------------------------------------------
# Frontmatter: a small YAML subset (scalars, inline lists, block lists of
# scalars, block lists of flat maps). Avoids a PyYAML dependency.
# ---------------------------------------------------------------------------

def _strip_comment(line):
    if '"' in line or "'" in line:
        return line
    return re.sub(r"(^|\s)#.*$", "", line)


def _scalar(s):
    s = s.strip()
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [_scalar(x) for x in inner.split(",")] if inner else []
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    if s in ("true", "false"):
        return s == "true"
    if s in ("", "null", "~"):
        return None
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    return s


def parse_frontmatter(text, where):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError(f"{where}: unterminated frontmatter")
    data, key, item = {}, None, None
    for n, raw in enumerate(text[3:end].splitlines(), start=1):
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        s = line.strip()
        if indent == 0:
            k, _, v = s.partition(":")
            key, item = k.strip(), None
            data[key] = _scalar(v) if v.strip() else []
        elif s.startswith("- ") or s == "-":
            content = s[2:] if s.startswith("- ") else ""
            if key is None or not isinstance(data.get(key), list):
                raise ValueError(f"{where}: line {n}: list item without a list key")
            if re.match(r"^[\w-]+:(\s|$)", content):
                k, _, v = content.partition(":")
                item = {k.strip(): _scalar(v)}
                data[key].append(item)
            else:
                item = None
                data[key].append(_scalar(content))
        else:
            if item is None:
                # `key:` followed by indented `k: v` lines is a map, not a list.
                if key is not None and data.get(key) == []:
                    data[key] = {}
                if key is None or not isinstance(data.get(key), dict):
                    raise ValueError(f"{where}: line {n}: nested key outside a list item or map")
                item_map = data[key]
            else:
                item_map = item
            k, _, v = s.partition(":")
            val = v.strip()
            item_map[k.strip()] = ([x.strip() for x in val.split("->")] if "->" in val
                                   else _scalar(v))
    return data


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _command(v):
    """A shell command from frontmatter. YAML-ish scalars like `true` come back as strings."""
    if v is None or v == []:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


ARCHIVE_LINE = re.compile(
    r"^- (?P<id>[\w.-]+): (?P<title>.*?) \((?P<status>done|released)"
    r"(?:, (?P<ref>[^,)]+?))?(?:, milestone (?P<milestone>[^)]+))?\)\s*$")


def read_archive(root):
    """Archived nodes from <root>/archive.md: id -> {title, status, ref, milestone}."""
    f = root / "archive.md"
    out = {}
    if f.exists():
        for line in f.read_text().splitlines():
            m = ARCHIVE_LINE.match(line)
            if m:
                out[m.group("id")] = m.groupdict()
    return out


def archived_node(root, nid, entry):
    """A done node whose folder was archived: enough for dependencies and milestones."""
    return {
        "id": nid, "dir": root / "nodes" / nid, "dirname": nid, "title": entry["title"],
        "status": entry["status"], "priority": "should", "size": "S", "model": None,
        "spike": False, "gate": False, "deps": [], "owns": [], "shared": [], "provides": [],
        "reserves": [], "added": None, "exclusive": [], "verify": None,
        "fulfilled_by": entry.get("ref"), "type": None, "target": None, "from": None,
        "outline": False, "milestone": entry.get("milestone"), "archived": True,
    }


def load(root):
    nodes, contracts, errors = {}, {}, []
    for brief in sorted((root / "nodes").glob("*/brief.md")):
        try:
            fm = parse_frontmatter(brief.read_text(), brief)
        except ValueError as e:
            errors.append(str(e))
            continue
        nid = str(fm.get("id") or brief.parent.name)
        nodes[nid] = {
            "id": nid,
            "dir": brief.parent,
            "dirname": brief.parent.name,
            "title": fm.get("title") or nid,
            "status": fm.get("status") or "todo",
            "priority": fm.get("priority") or "should",
            "size": fm.get("size"),
            "model": fm.get("model"),
            "spike": bool(fm.get("spike")),
            "gate": bool(fm.get("gate")),
            "deps": [d for d in _as_list(fm.get("depends_on"))],
            "owns": [str(p) for p in _as_list(fm.get("owns"))],
            "shared": [str(p) for p in _as_list(fm.get("shared"))],
            "provides": [str(c) for c in _as_list(fm.get("provides"))],
            "reserves": [str(r) for r in _as_list(fm.get("reserves"))],
            "added": fm.get("added"),
            "exclusive": [str(x) for x in _as_list(fm.get("exclusive"))],
            "verify": _command(fm.get("verify")),
            "fulfilled_by": fm.get("fulfilled_by") or None,
            "type": fm.get("type") or None,
            "target": fm.get("target") or None,
            "from": fm.get("from") or None,
            "outline": bool(fm.get("outline")),
            "milestone": fm.get("milestone") or None,
            "archived": False,
        }
    for nid, entry in read_archive(root).items():
        if nid in nodes:
            errors.append(f"node {nid}: in archive.md and in nodes/; remove one")
            continue
        nodes[nid] = archived_node(root, nid, entry)
    for path in sorted((root / "contracts").glob("*.md")):
        if path.name.endswith(".change-request.md"):
            continue
        try:
            fm = parse_frontmatter(path.read_text(), path)
        except ValueError as e:
            errors.append(str(e))
            continue
        name = str(fm.get("name") or path.stem)
        contracts[name] = {
            "name": name,
            "path": path,
            "status": fm.get("status") or "draft",
            "version": fm.get("version"),
            "defined_by": fm.get("defined_by"),
        }
    return nodes, contracts, errors


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def goal_settings(root):
    """Frontmatter of GOAL.md, or {}."""
    goal = root / "GOAL.md"
    if not goal.exists():
        return {}
    try:
        return parse_frontmatter(goal.read_text(), goal)
    except ValueError:
        return {}


def goal_milestones(root):
    """Ordered milestone names from the `milestones:` list in GOAL.md frontmatter, or None."""
    goal = root / "GOAL.md"
    if not goal.exists():
        return None
    try:
        ms = parse_frontmatter(goal.read_text(), goal).get("milestones")
    except ValueError:
        return None
    return [str(m) for m in ms] if isinstance(ms, list) and ms else None


def load_policy(root):
    """Branch policy from the `branches:` map in GOAL.md frontmatter, or None (one base branch)."""
    goal = root / "GOAL.md"
    if not goal.exists():
        return None
    try:
        pol = parse_frontmatter(goal.read_text(), goal).get("branches")
    except ValueError:
        return None
    return pol if isinstance(pol, dict) and pol else None


def apply_targets(nodes, policy):
    """The branch each node's pull request targets: its own `target`, else the policy for its type."""
    for n in nodes.values():
        t = n["target"]
        if not t and policy:
            t = policy.get(n["type"] or "feature") or policy.get("feature") or policy.get("default")
        n["target_eff"] = t


def policy_branches(policy):
    out = set()
    for v in (policy or {}).values():
        out.update(v if isinstance(v, list) else [v])
    return {str(b) for b in out if b}


def live(nodes):
    return {k: n for k, n in nodes.items() if n["status"] != "dropped"}


def start_preds(node, nodes, contracts):
    """Nodes that must finish before `node` can start."""
    preds = set()
    for d in node["deps"]:
        if not isinstance(d, dict):
            continue
        kind = d.get("kind")
        if kind == "hard" and d.get("on") in nodes:
            preds.add(d["on"])
        elif kind in ("contract", "behavior"):
            c = contracts.get(d.get("via"))
            if c and c["status"] != "frozen" and c["defined_by"] in nodes:
                preds.add(c["defined_by"])
    preds.discard(node["id"])
    return {p for p in preds if nodes[p]["status"] != "dropped"}


def all_preds(node, nodes, contracts):
    """Nodes that must finish before `node` can start, directly or through other nodes."""
    seen, todo = set(), [node]
    while todo:
        for p in start_preds(todo.pop(), nodes, contracts):
            if p not in seen:
                seen.add(p)
                todo.append(nodes[p])
    seen.discard(node["id"])
    return seen


def integration_preds(node, nodes):
    """Nodes whose real behavior `node` was built against a stub of."""
    return {
        d["on"] for d in node["deps"]
        if isinstance(d, dict) and d.get("kind") == "behavior" and d.get("on") in nodes
    }


def effective_priority(nodes, contracts):
    """A node is at least as urgent as the most urgent node that needs it.

    Returns {id: (rank, promoted_by)} where promoted_by is the dependent that raised it.
    """
    lv = live(nodes)
    eff = {k: (PRIORITIES.get(n["priority"], 1), None) for k, n in lv.items()}
    needs = {k: start_preds(n, lv, contracts) | integration_preds(n, lv) for k, n in lv.items()}
    changed = True
    while changed:
        changed = False
        for k, ps in needs.items():
            for p in ps:
                if p in eff and eff[k][0] < eff[p][0]:
                    eff[p] = (eff[k][0], k)
                    changed = True
    return eff


def levels(lv, succs, pending):
    """Bottom level: the longest weighted path from a node to the end of the graph."""
    points = {k: SIZE_POINTS.get(lv[k]["size"], 2) for k in lv}
    level = {}

    def bottom(k):
        if k not in level:
            level[k] = (points[k] if k in pending else 0) + max(
                (bottom(s) for s in succs[k] if s in lv), default=0)
        return level[k]

    for k in lv:
        bottom(k)
    return level, points


def _glob_prefix(g):
    m = re.search(r"[*?\[]", g)
    return (g[: m.start()], True) if m else (g, False)


def paths_overlap(a, b):
    pa, wa = _glob_prefix(a)
    pb, wb = _glob_prefix(b)
    if not wa and not wb:
        return pa == pb
    if wa and wb:
        return pa.startswith(pb) or pb.startswith(pa)
    fixed, prefix = (pa, pb) if not wa else (pb, pa)
    return fixed.startswith(prefix)


def wave_conflict(x, y):
    """Why x and y cannot run in the same wave, or None."""
    shared = sorted(set(x["exclusive"]) & set(y["exclusive"]))
    if shared:
        return "exclusive " + ", ".join(shared)
    return owns_conflict(x, y)


# Three nodes appending to one config file is normal; four or more on one file is a hot spot.
HOT_FILE_NODES = 4


def hot_files(planned):
    """Single files (not globs) that HOT_FILE_NODES or more open nodes own or share."""
    out = {}
    entries = {(p, n["id"]) for n in planned for p in n["owns"] + n["shared"]}
    for path in sorted({p for p, _ in entries if not _glob_prefix(p)[1]}):
        ids = sorted({nid for q, nid in entries if paths_overlap(path, q)})
        if len(ids) >= HOT_FILE_NODES:
            out[path] = ids
    return out


def shared_in_wave(wave, lv):
    """Shared files that two or more nodes of one wave edit. They may run together,
    but their pull requests touch the same file, so plan the merge order."""
    users = {}
    for k in wave:
        for p in lv[k]["shared"] + lv[k]["owns"]:
            users.setdefault(p, set()).add(k)
    notes = []
    for k in wave:
        for p in lv[k]["shared"]:
            others = {o for q, us in users.items() if paths_overlap(p, q) for o in us} - {k}
            if others:
                # Wave order is priority, then critical path: also the order to merge in.
                notes.append((p, [w for w in wave if w in others | {k}]))
    seen, out = set(), []
    for p, ks in notes:
        key = (p, tuple(ks))
        if key not in seen:
            seen.add(key)
            out.append((p, ks))
    return out


def owns_conflict(x, y):
    for a in x["owns"]:
        for b in y["owns"]:
            if paths_overlap(a, b):
                return f"{a} ~ {b}"
    return None


def find_cycle(ids, preds):
    color, stack = {}, []

    def visit(n):
        color[n] = 1
        stack.append(n)
        for p in sorted(preds[n]):
            if color.get(p) == 1:
                return stack[stack.index(p):] + [p]
            if color.get(p) is None:
                cyc = visit(p)
                if cyc:
                    return cyc
        stack.pop()
        color[n] = 2
        return None

    for n in sorted(ids):
        if color.get(n) is None:
            cyc = visit(n)
            if cyc:
                return cyc
    return None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def check(nodes, contracts, load_errors, policy=None, milestones=None):
    errors, warnings = list(load_errors), []
    if milestones:
        for nid, n in live(nodes).items():
            if n["milestone"] and n["milestone"] not in milestones:
                warnings.append(f"node {nid}: milestone '{n['milestone']}' is not in GOAL.md "
                                f"milestones ({', '.join(milestones)})")
    if policy:
        known = policy_branches(policy)
        for nid, n in live(nodes).items():
            if n["type"] and n["type"] not in TYPES:
                warnings.append(f"node {nid}: type '{n['type']}' not in {sorted(TYPES)}")
            if n.get("target_eff") and n["target_eff"] not in known:
                warnings.append(f"node {nid}: targets '{n['target_eff']}', which is not a branch "
                                f"in the policy ({', '.join(sorted(known))})")
        for nid, n in live(nodes).items():
            if n["type"] != "release":
                continue
            if not (n["from"] and n["target"]):
                errors.append(f"node {nid}: a release node needs `from` and `target` branches")
                continue
            preds = all_preds(n, live(nodes), contracts)
            missing = sorted(k for k, o in live(nodes).items()
                             if k != nid and o.get("target_eff") == n["from"]
                             and o["status"] not in DONE and k not in preds)
            if missing:
                warnings.append(f"node {nid}: releases {n['from']} -> {n['target']} but does not wait "
                                f"for open work on {n['from']}: {', '.join(missing)}")
            unshipped = sorted(k for k, o in live(nodes).items()
                               if k != nid and n["milestone"] and o["milestone"] == n["milestone"]
                               and o["type"] != "release" and o["status"] not in DONE
                               and k not in preds)
            if unshipped:
                warnings.append(f"node {nid}: releases milestone {n['milestone']} but does not wait "
                                f"for its open nodes: {', '.join(unshipped)}")
    for nid, n in nodes.items():
        where = f"node {nid}"
        if n["dirname"] != nid:
            warnings.append(f"{where}: id differs from directory name '{n['dirname']}'")
        if n["status"] not in STATUSES:
            errors.append(f"{where}: status '{n['status']}' not in {sorted(STATUSES)}")
        if n["status"] == "dropped" or n["archived"]:
            continue
        if n["priority"] not in PRIORITIES:
            errors.append(f"{where}: priority must be one of must, should, could, later")
        if n["size"] not in SIZE_POINTS:
            errors.append(f"{where}: size must be one of S, M, L, XL")
        elif n["size"] == "XL" and n["status"] == "todo" and not n["outline"]:
            warnings.append(f"{where}: size XL, split it before scheduling")
        if not n["owns"] and n["type"] != "release" and not n["outline"]:
            warnings.append(f"{where}: no owned paths, conflicts cannot be detected")
        if (n["status"] in DONE and not n["fulfilled_by"]
                and not (n["dir"] / "outcome.md").exists()):
            warnings.append(f"{where}: done but has no outcome.md or fulfilled_by")
        for c in n["provides"]:
            if c not in contracts:
                errors.append(f"{where}: provides unknown contract '{c}'")
        for i, d in enumerate(n["deps"]):
            dw = f"{where} dep #{i + 1}"
            if not isinstance(d, dict):
                errors.append(f"{dw}: expected a map with on/kind/via/why")
                continue
            kind, on, via = d.get("kind"), d.get("on"), d.get("via")
            if kind not in KINDS:
                errors.append(f"{dw}: kind must be contract, behavior or hard")
                continue
            if on is not None and on not in nodes:
                errors.append(f"{dw}: unknown node '{on}'")
            elif on is not None and nodes[on]["status"] == "dropped":
                warnings.append(f"{dw}: depends on dropped node '{on}'")
            if kind in ("hard", "behavior") and on is None:
                errors.append(f"{dw}: {kind} dependency needs 'on'")
            if kind in ("contract", "behavior"):
                if not via:
                    errors.append(f"{dw}: {kind} dependency needs 'via' (the contract name)")
                elif via not in contracts:
                    errors.append(f"{dw}: unknown contract '{via}'")
            if kind == "hard" and not d.get("why"):
                warnings.append(f"{dw}: hard dependency without 'why'; justify it or downgrade it")
            if (kind == "hard" and on in nodes and n["size"] == "S" and nodes[on]["size"] == "S"
                    and not n["outline"] and not nodes[on]["outline"]
                    and n["status"] == "todo" and nodes[on]["status"] == "todo"
                    and owns_conflict(n, nodes[on])):
                warnings.append(f"{dw}: S node in a hard chain with S node '{on}' on the same "
                                "files; merge them into one node")
    claimed = {}
    for nid, n in live(nodes).items():
        for r in n["reserves"]:
            if r in claimed:
                errors.append(f"node {nid}: reserves '{r}', already reserved by {claimed[r]}")
            claimed[r] = nid
    for name, c in contracts.items():
        where = f"contract {name}"
        if c["status"] not in CONTRACT_STATUSES:
            errors.append(f"{where}: status must be draft or frozen")
        if c["status"] == "draft":
            if not c["defined_by"]:
                errors.append(f"{where}: draft contract needs 'defined_by' (the node that freezes it)")
            elif c["defined_by"] not in nodes:
                errors.append(f"{where}: defined_by unknown node '{c['defined_by']}'")
    if not errors:
        for k, (rank, by) in effective_priority(nodes, contracts).items():
            if by is not None:
                warnings.append(
                    f"node {k}: priority {nodes[k]['priority']}, but {by} needs it and is "
                    f"{PRIORITY_NAMES[rank]}; raise it, or remove the dependency")
        lv = live(nodes)
        for k, n in lv.items():
            waiting = sorted(p for p in start_preds(n, lv, contracts) if lv[p]["status"] not in DONE)
            if (n["status"] == "active" or n["status"] in DONE) and waiting:
                warnings.append(f"node {k}: {n['status']} but its start dependencies are not done: "
                                + ", ".join(waiting))
        # Outline nodes are not cut yet, so shape checks skip them.
        planned = [n for n in lv.values() if n["status"] not in DONE and not n["outline"]]
        for path, ids in hot_files(planned).items():
            warnings.append(
                f"{path} is edited by {len(ids)} open nodes ({', '.join(ids)}); split it by "
                "feature in an early, behavior-preserving node so each owns its own module "
                "(decomposition.md, 'Split hot files by feature first'), or say why not")
        small = [n for n in planned if n["size"] == "S"]
        if len(planned) >= 8 and len(small) * 2 > len(planned):
            warnings.append(
                f"{len(small)} of {len(planned)} open nodes are S; each node costs a worktree, a "
                "review and a merge, so merge small nodes that share files or run in sequence")
        preds = {k: start_preds(n, lv, contracts) for k, n in lv.items()}
        cyc = find_cycle(lv, preds)
        if cyc:
            errors.append("cycle: " + " -> ".join(cyc))
    return errors, warnings


def schedule(nodes, contracts, max_parallel, upto="could"):
    lv = live(nodes)
    eff = effective_priority(nodes, contracts)
    cut = PRIORITIES[upto]
    preds = {k: start_preds(n, lv, contracts) for k, n in lv.items()}
    succs = {k: set() for k in lv}
    for k, ps in preds.items():
        for p in ps:
            succs[p].add(k)

    pending = {k for k, n in lv.items() if n["status"] not in DONE and eff[k][0] <= cut}
    parked = sorted(k for k, n in lv.items() if n["status"] not in DONE and eff[k][0] > cut)
    level, points = levels(lv, succs, pending)

    waves, deferred, shared_notes = [], [], []
    placed = {k for k in lv if k not in pending}
    while pending - placed:
        avail = [k for k in pending - placed if preds[k] <= placed]
        if not avail:
            break  # cycle; reported by check
        # Running nodes come first, then by priority, then by critical path.
        avail.sort(key=lambda k: (lv[k]["status"] != "active", eff[k][0], -level[k], k))
        wave, conflicts = [], []
        for k in avail:
            if len(wave) >= max_parallel and lv[k]["status"] != "active":
                continue
            clash = next(((o, wave_conflict(lv[k], lv[o])) for o in wave
                          if wave_conflict(lv[k], lv[o])), None)
            if clash:
                conflicts.append((k, clash[0], clash[1]))
                continue
            wave.append(k)
        waves.append(wave)
        deferred.append(conflicts)
        shared_notes.append(shared_in_wave(wave, lv))
        placed |= set(wave)

    # The wave by which every node of a priority (and everything more urgent) is placed.
    milestones = {}
    for rank in range(cut + 1):
        idx = [i + 1 for i, w in enumerate(waves) for k in w if eff[k][0] <= rank]
        if any(eff[k][0] == rank for k in pending):
            milestones[PRIORITY_NAMES[rank]] = max(idx) if idx else 0

    # Critical path: follow the highest bottom level from the best start node.
    path, frontier = [], [k for k in pending if not (preds[k] & pending)]
    while frontier:
        k = max(frontier, key=lambda x: (level[x], x))
        path.append(k)
        frontier = [s for s in succs[k] if s in pending]

    integration = []
    for k, n in lv.items():
        if k not in pending and n["status"] not in DONE:
            continue
        waiting = sorted(p for p in integration_preds(n, lv) if lv[p]["status"] not in DONE)
        if waiting:
            integration.append((k, waiting))

    return {
        "priority": {k: PRIORITY_NAMES[eff[k][0]] for k in lv},
        "priority_waves": milestones,
        "groups": milestone_groups(waves, lv, pending),
        "parked": parked,
        "waves": waves,
        "deferred": deferred,
        "shared": shared_notes,
        "critical_path": path,
        "critical_points": sum(points[k] for k in path),
        "total_points": sum(points[k] for k in pending),
        "integration_pending": integration,
    }


def milestone_groups(waves, lv, pending):
    """Per named milestone: open nodes, outline nodes, and the wave its last node is placed in."""
    groups = {}
    wave_of = {k: i + 1 for i, w in enumerate(waves) for k in w}
    for k, n in lv.items():
        name = n["milestone"]
        if not name:
            continue
        g = groups.setdefault(name, {"open": 0, "outline": 0, "done": 0, "last_wave": 0})
        if n["status"] in DONE:
            g["done"] += 1
            continue
        g["open"] += 1
        g["outline"] += n["outline"]
        g["last_wave"] = max(g["last_wave"], wave_of.get(k, 0))
    return groups


def refine_due(nodes, contracts, horizon, max_parallel=DEFAULT_MAX_PARALLEL):
    """Outline nodes placed within the next `horizon` waves: break them into briefs now."""
    s = schedule(nodes, contracts, max_parallel)
    return [k for w in s["waves"][:horizon] for k in w if nodes[k]["outline"]]


def ready(nodes, contracts, upto="could"):
    """Nodes that can start now, most urgent first, then longest remaining path."""
    lv = live(nodes)
    eff = effective_priority(nodes, contracts)
    preds = {k: start_preds(n, lv, contracts) for k, n in lv.items()}
    succs = {k: {o for o in lv if k in preds[o]} for k in lv}
    pending = {k for k, n in lv.items() if n["status"] not in DONE}
    level, _ = levels(lv, succs, pending)
    out = [k for k, n in lv.items()
           if n["status"] == "todo" and n["size"] != "XL" and not n["outline"]
           and eff[k][0] <= PRIORITIES[upto]
           and all(lv[p]["status"] in DONE for p in preds[k])]
    return sorted(out, key=lambda k: (eff[k][0], -level[k], k))


def impact(nid, nodes, contracts, max_parallel):
    """Effect of node `nid` on the rest of the plan, for mid-roadmap additions."""
    n = nodes[nid]
    lv = live(nodes)
    out = {"node": nid, "overlaps": [], "contracts": [], "downstream": [], "upstream": []}
    for k, o in lv.items():
        if k == nid or o["status"] in DONE:
            continue
        why = owns_conflict(n, o)
        if why:
            out["overlaps"].append({"node": k, "status": o["status"], "paths": why})
    for d in n["deps"]:
        if isinstance(d, dict) and d.get("via") in contracts:
            c = contracts[d["via"]]
            out["contracts"].append({"name": c["name"], "status": c["status"], "use": d.get("kind")})
    for c in n["provides"]:
        if c in contracts:
            out["contracts"].append({"name": c, "status": contracts[c]["status"], "use": "provides"})
    preds = start_preds(n, lv, contracts)
    out["upstream"] = [{"node": p, "status": lv[p]["status"]} for p in sorted(preds)]
    out["downstream"] = sorted(k for k, o in lv.items() if nid in start_preds(o, lv, contracts))
    out["can_start_now"] = n["status"] == "todo" and all(lv[p]["status"] in DONE for p in preds)
    without = dict(nodes)
    without.pop(nid)
    a = schedule(nodes, contracts, max_parallel)
    b = schedule(without, contracts, max_parallel)
    out["critical_points"] = {"with": a["critical_points"], "without": b["critical_points"]}
    out["waves"] = {"with": len(a["waves"]), "without": len(b["waves"])}
    out["on_critical_path"] = nid in a["critical_path"]
    eff = effective_priority(nodes, contracts)
    out["priority"] = {"own": n["priority"], "effective": PRIORITY_NAMES[eff[nid][0]]}
    out["milestones"] = {"with": a["priority_waves"], "without": b["priority_waves"]}
    return out


def verify(nids, nodes, cwd, timeout):
    """Run each node's verify command. Exit code 0 means the acceptance holds."""
    results = []
    for k in nids:
        cmd = nodes[k]["verify"]
        if not cmd:
            results.append({"id": k, "status": nodes[k]["status"], "result": "no verify command"})
            continue
        try:
            r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True,
                               timeout=timeout)
            res = "pass" if r.returncode == 0 else f"fail (exit {r.returncode})"
            tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
        except subprocess.TimeoutExpired:
            res, tail = f"timeout after {timeout}s", []
        results.append({"id": k, "status": nodes[k]["status"], "command": cmd,
                        "result": res, "tail": tail})
    return results


def goal_heading(root):
    """Title and first paragraph of the outcome from GOAL.md."""
    goal = root / "GOAL.md"
    if not goal.exists():
        return root.name, ""
    text = goal.read_text()
    if text.startswith("---"):
        end = text.find("\n---", 3)
        text = text[end + 4:] if end != -1 else text
    title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), root.name)
    outcome = ""
    m = re.search(r"^## Outcome\s*\n+(.+?)(\n\n|\n#|$)", text, re.S | re.M)
    if m:
        outcome = " ".join(m.group(1).split())
    return title, outcome


def overview(root, nodes, contracts, s, milestones, warnings):
    """A readable summary of the plan, as markdown."""
    lv = live(nodes)
    wave_of = {k: i + 1 for i, w in enumerate(s["waves"]) for k in w}
    title, outcome = goal_heading(root)
    out = [f"# {title}", ""]
    if outcome:
        out += [outcome, ""]
    counts = {}
    for n in lv.values():
        key = "outline" if n["outline"] and n["status"] not in DONE else n["status"]
        counts[key] = counts.get(key, 0) + 1
    out.append("**Nodes:** " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
    if "must" in s["priority_waves"]:
        out.append(f"**Must line:** all must work placed by wave {s['priority_waves']['must']}")
    if s["critical_path"]:
        out.append(f"**Critical path:** {' -> '.join(s['critical_path'])}")
    due = [k for w in s["waves"][:DEFAULT_HORIZON] for k in w if lv[k]["outline"]]
    if due:
        out.append(f"**Refine next:** {', '.join(due)}")
    out.append("")

    def line(k):
        n = lv[k]
        mark = {"done": "x", "released": "x", "active": "~"}.get(n["status"], " ")
        if n["archived"]:
            return f"- [x] **{k}**: {n['title']} [archived]"
        bits = [s["priority"].get(k, n["priority"]), n["size"] or "?"]
        if n.get("target_eff"):
            bits.append(f"-> {n['target_eff']}")
        if n["outline"]:
            bits.append("outline")
        if n["status"] in ("active", "released"):
            bits.append(n["status"])
        elif n["status"] not in DONE:
            bits.append(f"wave {wave_of.get(k, '-')}")
        deps = sorted({d.get("on") for d in n["deps"] if isinstance(d, dict) and d.get("on") in lv})
        after = f" (after {', '.join(deps)})" if deps else ""
        return f"- [{mark}] **{k}**: {n['title']} [{', '.join(bits)}]{after}"

    groups = {}
    for k, n in lv.items():
        groups.setdefault(n["milestone"] or "", []).append(k)
    order = list(milestones or []) + sorted(g for g in groups if g and g not in (milestones or []))
    if "" in groups:
        order.append("")
    for name in order:
        if name not in groups:
            continue
        out.append(f"## {name}" if name else ("## Other work" if len(groups) > 1 else "## Work"))
        ids = sorted(groups[name], key=lambda k: (lv[k]["status"] not in DONE,
                                                  wave_of.get(k, 99), PRIORITIES.get(lv[k]["priority"], 1), k))
        out += [line(k) for k in ids] + [""]
    if warnings:
        out.append(f"**Warnings ({len(warnings)}):** run `plan.py check` for the list.")
    return "\n".join(out).rstrip() + "\n"


SIZE_ORDER = ["S", "M", "L", "XL"]
MERGE_DEFAULTS = {"mode": "maintainer", "method": "squash", "max_size": "M",
                  "exclude": ["release", "hotfix", "contract", "gate"]}


def merge_policy(root):
    """The `merge:` map from GOAL.md frontmatter over the defaults (mode maintainer)."""
    raw = goal_settings(root).get("merge")
    pol = dict(MERGE_DEFAULTS)
    if isinstance(raw, dict):
        pol.update({k: v for k, v in raw.items() if v not in (None, [])})
    if not isinstance(pol["exclude"], list):
        pol["exclude"] = [pol["exclude"]]
    return pol


def run_mode(root, max_parallel):
    """`sequential` when GOAL.md sets `run: sequential` or --max-parallel is 1, else `parallel`."""
    if str(goal_settings(root).get("run", "")).strip().lower() == "sequential" or max_parallel == 1:
        return "sequential"
    return "parallel"


REVIEW_MODES = {"auto", "fresh", "self"}


def review_setting(root):
    """The `review:` setting from GOAL.md frontmatter: auto (the default), fresh or self."""
    v = str(goal_settings(root).get("review") or "auto").strip().lower()
    return v if v in REVIEW_MODES else "auto"


def review_mode(n, setting="auto"):
    """Who reviews a node's pull request: `fresh` (a new agent) or `self` (the worker).

    With `auto`, S nodes and docs or chore nodes are self-reviewed. Gated nodes, contract
    providers, releases, hotfixes and every other node get a fresh reviewer.
    """
    if setting in ("fresh", "self"):
        return setting
    if n["gate"] or n["provides"] or n["type"] in ("release", "hotfix"):
        return "fresh"
    if n["size"] == "S" or n["type"] in ("docs", "chore"):
        return "self"
    return "fresh"


def can_merge(nid, nodes, policy, review_clean, checks_pass, proof, files, ci_guard="safe",
              review="fresh", fresh_review=False):
    """Decide whether the orchestrator may merge a node's pull request itself.

    Returns {"verdict": "auto" | "maintainer", "reasons": [...]}. Every reason is a
    condition that failed; an empty list with mode auto means the merge may go ahead.
    """
    n = nodes[nid]
    reasons = []
    if policy.get("mode") != "auto":
        reasons.append("merge mode is maintainer")
    excluded = set(policy.get("exclude") or [])
    if n["type"] and n["type"] in excluded:
        reasons.append(f"type {n['type']} is excluded")
    if "gate" in excluded and n["gate"]:
        reasons.append("the node is gated")
    if "contract" in excluded and n["provides"]:
        reasons.append("the node provides a contract: " + ", ".join(n["provides"]))
    if "spike" in excluded and n["spike"]:
        reasons.append("the node is a spike")
    limit = str(policy.get("max_size") or "M")
    if n["size"] in SIZE_ORDER and limit in SIZE_ORDER and \
            SIZE_ORDER.index(n["size"]) > SIZE_ORDER.index(limit):
        reasons.append(f"size {n['size']} is above the limit {limit}")
    if n["status"] != "active":
        reasons.append(f"status is {n['status']}, not active")
    if not review_clean:
        reasons.append("the review is not clean (blocking or should-fix findings)")
    if review == "self" and not fresh_review:
        reasons.append("the node was self-reviewed; auto-merge needs a fresh-agent review")
    if not checks_pass:
        reasons.append("the checks did not pass")
    if (n["type"] in ("fix", "hotfix")) and not proof:
        reasons.append("a fix needs proof: fails on base, passes on head")
    if ci_guard != "safe":
        reasons.append("merging would start billed CI on a private repo (ci_guard says ask)")
    allowed = n["owns"] + n["shared"]
    outside = [f for f in files
               if not fnmatch.fnmatch(f, f"*nodes/{nid}/*")
               and not any(fnmatch.fnmatch(f, g) or paths_overlap(f, g) for g in allowed)]
    if outside:
        reasons.append("changes outside the node's paths: " + ", ".join(outside[:5]))
    return {"node": nid, "verdict": "maintainer" if reasons else "auto", "reasons": reasons,
            "method": policy.get("method", "squash")}


def archive_candidates(nodes, contracts):
    """Done nodes nothing open still needs, and frozen contracts no open node uses."""
    lv = live(nodes)
    needed = set()
    for k, n in lv.items():
        if n["status"] in DONE:
            continue
        for d in n["deps"]:
            if isinstance(d, dict) and d.get("on"):
                needed.add(d["on"])
        needed |= start_preds(n, lv, contracts)
    ready_nodes = sorted(k for k, n in lv.items()
                         if n["status"] in DONE and not n["archived"] and k not in needed)
    used = set()
    for n in lv.values():
        if n["status"] in DONE:
            continue
        used.update(n["provides"])
        used.update(d.get("via") for d in n["deps"] if isinstance(d, dict) and d.get("via"))
    unused = sorted(c for c, v in contracts.items() if v["status"] == "frozen" and c not in used)
    return ready_nodes, unused


def archive_line(n):
    """One archive.md line. The reference is fulfilled_by, else the first PR number in the outcome."""
    ref = n["fulfilled_by"]
    outcome = n["dir"] / "outcome.md"
    if not ref and outcome.exists():
        m = re.search(r"(?<![\w/])#(\d+)\b", outcome.read_text())
        ref = f"#{m.group(1)}" if m else None
    parts = [n["status"]] + ([str(ref)] if ref else []) + \
        ([f"milestone {n['milestone']}"] if n["milestone"] else [])
    title = n["title"].replace("(", "[").replace(")", "]")
    return f"- {n['id']}: {title} ({', '.join(parts)})"


def apply_archive(root, nodes, ids):
    f = root / "archive.md"
    text = f.read_text() if f.exists() else (
        "# Archive\n\nDone nodes whose folders were removed. Their full text is in git history.\n\n")
    for k in ids:
        text += archive_line(nodes[k]) + "\n"
        shutil.rmtree(nodes[k]["dir"])
    f.write_text(text)


BRANCH_PREFIX = {"feature": "feat", "fix": "fix", "hotfix": "hotfix", "refactor": "refactor",
                 "docs": "docs", "chore": "chore", "release": "release", "spike": "spike",
                 "contract": "feat"}
TITLE_PREFIX = {"feature": "feat", "fix": "fix", "hotfix": "fix", "refactor": "refactor",
                "docs": "docs", "chore": "chore", "release": "chore", "spike": "chore",
                "contract": "feat"}


def branch_name(n):
    """A descriptive branch for a node's pull request: <type>/<node id>."""
    kind = n["type"] or ("spike" if n["spike"] else "feature")
    return f"{BRANCH_PREFIX.get(kind, 'feat')}/{n['id']}"


def pr_title(n):
    """A conventional pull request title from the node's type and title."""
    kind = n["type"] or ("spike" if n["spike"] else "feature")
    title = n["title"][:1].lower() + n["title"][1:] if n["title"] else n["id"]
    return f"{TITLE_PREFIX.get(kind, 'feat')}: {title}"


def rel(path):
    return os.path.relpath(path)


def context_files(root, nid, nodes, contracts):
    n = nodes[nid]
    files = []

    def add(layer, path, why):
        if path.exists() and all(f["path"] != rel(path) for f in files):
            files.append({"layer": layer, "path": rel(path), "why": why,
                          "tokens": len(path.read_text()) // 4})

    add("L0", root / "GOAL.md", "roadmap goal and constraints")
    add("L0", root / "CLAUDE.md", "roadmap conventions")
    add("L1", n["dir"] / "brief.md", "this node")
    for d in n["deps"]:
        if not isinstance(d, dict):
            continue
        if d.get("via") in contracts:
            add("L2", contracts[d["via"]]["path"], f"contract for {d.get('kind')} dep")
        on = d.get("on")
        if on in nodes and d.get("kind") in ("hard", "behavior"):
            add("L2", nodes[on]["dir"] / "outcome.md", f"outcome of {on}")
    for c in n["provides"]:
        if c in contracts:
            add("L2", contracts[c]["path"], "contract this node implements")
    add("L1", n["dir"] / "log.md", "this node's own working log (resume)")
    return files


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def model_for(n):
    if n["model"]:
        return n["model"]
    if n["spike"]:
        return "opus"
    return DEFAULT_MODEL.get(n["size"], "sonnet")


def print_check(errors, warnings):
    for e in errors:
        print(f"error: {e}")
    for w in warnings:
        print(f"warning: {w}")
    if not errors and not warnings:
        print("check: ok")


def print_schedule(s, nodes):
    for i, wave in enumerate(s["waves"], start=1):
        print(f"wave {i}:")
        for k in wave:
            n = nodes[k]
            pri = s["priority"][k]
            tgt = f" -> {n['target_eff']}" if n.get("target_eff") else ""
            tags = [pri if pri == n["priority"] else f"{pri} (was {n['priority']})",
                    n["size"] or "?", model_for(n)]
            if n["status"] == "active":
                tags.append("active")
            if n["size"] == "XL" and not n["outline"]:
                tags.append("split first")
            if n["spike"]:
                tags.append("spike")
            if n["outline"]:
                tags.append("outline")
            if n["gate"]:
                tags.append("gate")
            print(f"  {k}  [{', '.join(tags)}]{tgt}  {n['title']}")
        for k, other, why in s["deferred"][i - 1]:
            print(f"  (deferred {k}: conflicts with {other}: {why})")
        for path, ks in s["shared"][i - 1]:
            print(f"  (shared {path}: edited by {', '.join(ks)}; merge in this order, "
                  "or split the file by feature in an earlier node)")
    for name, g in s["groups"].items():
        if g["open"]:
            extra = f", {g['outline']} outline" if g["outline"] else ""
            print(f"milestone {name}: {g['open']} open{extra}, {g['done']} done, "
                  f"last node placed by wave {g['last_wave']}")
        else:
            print(f"milestone {name}: done ({g['done']} nodes)")
    due = [k for w in s["waves"][:DEFAULT_HORIZON] for k in w if nodes[k]["outline"]]
    if due:
        print(f"refine now (outline nodes within {DEFAULT_HORIZON} waves): " + ", ".join(due))
    for pri, wave in s["priority_waves"].items():
        print(f"all {pri} work placed by wave {wave}")
    if s["parked"]:
        print("parked (not scheduled): " + ", ".join(s["parked"]))
    print(f"critical path ({s['critical_points']} of {s['total_points']} points): "
          + " -> ".join(s["critical_path"]))
    if s["total_points"]:
        print(f"parallelism: {s['total_points'] / max(s['critical_points'], 1):.1f}x")
    for k, waiting in s["integration_pending"]:
        print(f"integration pending: {k} runs on stubs of {', '.join(waiting)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("command", nargs="?", default="status",
                    choices=["status", "check", "waves", "ready", "context", "impact", "verify", "refine",
                             "overview", "can-merge", "archive"])
    ap.add_argument("node", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-parallel", type=int, default=DEFAULT_MAX_PARALLEL)
    ap.add_argument("--budget", type=int, default=20000)
    ap.add_argument("--upto", choices=list(PRIORITIES), default="could")
    ap.add_argument("--apply", action="store_true", help="archive: remove the folders and write archive.md")
    ap.add_argument("--review-clean", action="store_true", help="can-merge: the review had no blocking or should-fix findings")
    ap.add_argument("--checks-pass", action="store_true", help="can-merge: lint, typecheck, build and tests passed")
    ap.add_argument("--proof", action="store_true", help="can-merge: the fix fails on base and passes on head")
    ap.add_argument("--files", default="", help="can-merge: changed files, comma separated, or '-' to read lines from stdin")
    ap.add_argument("--fresh-review", action="store_true", help="can-merge: a fresh agent reviewed it (needed when the node's review mode is self)")
    ap.add_argument("--ci-guard", default="safe", choices=["safe", "ask"], help="can-merge: the verdict of pr-author's ci_guard.py")
    ap.add_argument("--horizon", type=int, default=DEFAULT_HORIZON,
                    help="waves ahead within which outline nodes are due for refinement")
    ap.add_argument("--cwd", default=".", help="directory to run verify commands in (repo root)")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    if not (args.root / "nodes").is_dir():
        sys.exit(f"{args.root}: no nodes/ directory")
    nodes, contracts, load_errors = load(args.root)
    mode = run_mode(args.root, args.max_parallel)
    if mode == "sequential":
        args.max_parallel = 1
    policy = load_policy(args.root)
    apply_targets(nodes, policy)
    milestones = goal_milestones(args.root)
    errors, warnings = check(nodes, contracts, load_errors, policy, milestones)

    if args.command == "check":
        if args.json:
            print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
        else:
            print_check(errors, warnings)
        sys.exit(1 if errors else 0)

    if errors and args.command in ("status", "waves", "ready"):
        print_check(errors, warnings)
        sys.exit(1)

    if args.command == "context":
        if args.node not in nodes:
            sys.exit(f"unknown node '{args.node}'")
        files = context_files(args.root, args.node, nodes, contracts)
        total = sum(f["tokens"] for f in files)
        if args.json:
            print(json.dumps({"node": args.node, "files": files, "tokens": total,
                              "budget": args.budget, "over_budget": total > args.budget}, indent=2))
        else:
            for f in files:
                print(f"{f['layer']}  {f['path']}  (~{f['tokens']} tokens, {f['why']})")
            print(f"total ~{total} tokens of {args.budget} budget")
            if total > args.budget:
                print("over budget: split this node or tighten its dependencies' outcomes")
        return

    if args.command == "archive":
        ids, unused = archive_candidates(nodes, contracts)
        if args.json:
            print(json.dumps({"nodes": ids, "unused_contracts": unused}, indent=2))
            return
        for k in ids:
            print(("archived " if args.apply else "would archive ") + archive_line(nodes[k])[2:])
        if not ids:
            print("no done nodes to archive")
        if unused:
            print("contracts no open node uses (remove or keep as reference): " + ", ".join(unused))
        if args.apply and ids:
            apply_archive(args.root, nodes, ids)
        return

    if args.command == "can-merge":
        if args.node not in nodes:
            sys.exit(f"unknown node '{args.node}'")
        files = (sys.stdin.read().split() if args.files == "-" else
                 [f for f in args.files.split(",") if f])
        r = can_merge(args.node, nodes, merge_policy(args.root), args.review_clean,
                      args.checks_pass, args.proof, files, args.ci_guard,
                      review_mode(nodes[args.node], review_setting(args.root)), args.fresh_review)
        if args.json:
            print(json.dumps(r, indent=2))
        else:
            print(f"{args.node}: {r['verdict']}" + ("" if r["verdict"] == "auto" else ":"))
            for reason in r["reasons"]:
                print(f"  - {reason}")
        sys.exit(0 if r["verdict"] == "auto" else 1)

    if args.command == "refine":
        due = refine_due(nodes, contracts, args.horizon, args.max_parallel)
        if args.json:
            print(json.dumps(due))
            return
        for k in due:
            print(f"{k}  [{nodes[k]['priority']}, {nodes[k]['size'] or '?'}]  {nodes[k]['title']}")
        print(f"{len(due)} outline node(s) within {args.horizon} waves" if due
              else f"no outline nodes within {args.horizon} waves")
        return

    if args.command == "verify":
        if args.node:
            if args.node not in nodes:
                sys.exit(f"unknown node '{args.node}'")
            ids = [args.node]
        else:
            ids = sorted(k for k, n in live(nodes).items() if n["status"] == "todo")
        results = verify(ids, nodes, args.cwd, args.timeout)
        if args.json:
            print(json.dumps(results, indent=2))
            return
        for r in results:
            print(f"{r['id']}  {r['result']}" + (f"  ({r['command']})" if r.get("command") else ""))
            for line in r.get("tail", []):
                print(f"    {line}")
        met = [r["id"] for r in results if r["result"] == "pass" and r["status"] == "todo"]
        if met:
            print("acceptance already holds for: " + ", ".join(met)
                  + ". Check them and close as fulfilled instead of building.")
        return

    if args.command == "impact":
        if args.node not in nodes:
            sys.exit(f"unknown node '{args.node}'")
        r = impact(args.node, nodes, contracts, args.max_parallel)
        if args.json:
            print(json.dumps(r, indent=2))
            return
        pr = r["priority"]
        print(f"impact of {args.node} (priority {pr['own']}"
              + (f", effectively {pr['effective']})" if pr["effective"] != pr["own"] else ")"))
        print("  can start now" if r["can_start_now"] else
              "  waits on: " + ", ".join(f"{u['node']} ({u['status']})" for u in r["upstream"]))
        for o in r["overlaps"]:
            note = "  <- running now, wait or narrow owns" if o["status"] == "active" else ""
            print(f"  overlaps {o['node']} ({o['status']}): {o['paths']}{note}")
        for c in r["contracts"]:
            print(f"  contract {c['name']} ({c['status']}), {c['use']}")
        if r["downstream"]:
            print("  blocks: " + ", ".join(r["downstream"]))
        cp, w = r["critical_points"], r["waves"]
        print(f"  critical path {cp['without']} -> {cp['with']} points, waves {w['without']} -> {w['with']}"
              + ("  (on the critical path)" if r["on_critical_path"] else ""))
        for pri, w in r["milestones"]["with"].items():
            before = r["milestones"]["without"].get(pri)
            if before != w:
                print(f"  all {pri} work placed by wave {before or 'n/a'} -> {w}")
        return

    if args.command == "ready":
        ids = ready(nodes, contracts, args.upto)
        rs = review_setting(args.root)
        if args.json:
            print(json.dumps([{
                "id": k, "title": nodes[k]["title"], "size": nodes[k]["size"],
                "priority": nodes[k]["priority"],
                "target": nodes[k].get("target_eff"),
                "branch": branch_name(nodes[k]),
                "pr_title": pr_title(nodes[k]),
                "model": model_for(nodes[k]), "gate": nodes[k]["gate"], "mode": mode,
                "review": review_mode(nodes[k], rs),
                "brief": rel(nodes[k]["dir"] / "brief.md"),
                "context": [f["path"] for f in context_files(args.root, k, nodes, contracts)],
            } for k in ids], indent=2))
        else:
            for k in ids:
                print(f"{k}  [{nodes[k]['size']}, {model_for(nodes[k])}, {review_mode(nodes[k], rs)} review]  {nodes[k]['title']}")
            if not ids:
                print("nothing ready")
            elif mode == "sequential":
                print("sequential: start only the first; a worktree is optional")
        return

    s = schedule(nodes, contracts, args.max_parallel, args.upto)
    if milestones:
        order = {m: i for i, m in enumerate(milestones)}
        s["groups"] = dict(sorted(s["groups"].items(), key=lambda kv: order.get(kv[0], len(order))))
    if args.command == "overview":
        print(overview(args.root, nodes, contracts, s, milestones, warnings), end="")
        return
    if args.json:
        print(json.dumps({"errors": errors, "warnings": warnings, **s}, indent=2))
        return
    if args.command == "status":
        print_check(errors, warnings)
        counts = {}
        for n in nodes.values():
            counts[n["status"]] = counts.get(n["status"], 0) + 1
        print("nodes: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
    print_schedule(s, nodes)


if __name__ == "__main__":
    main()

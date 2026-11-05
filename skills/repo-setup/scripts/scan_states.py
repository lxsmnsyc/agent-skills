#!/usr/bin/env python3
"""List candidate implicit state machines in a JS or TS repo.

Usage:
  scan_states.py [root] [--json]

An implicit state machine is one state spread over several values with no list
of allowed transitions. A file that switches on its status or defines a
transition function already has that list. The scan looks for two shapes:

  flags    boolean flags in one file that conditions combine, such as
           `isLoading && !isError`, or three or more flags set to true and false
  status   a status, state, phase, mode, stage or step value assigned three or
           more string literals, in a file with no transition function or switch

Each candidate says whether its names appear in a database schema, migration or
SQL file (stored: yes), whether its file writes to storage (stored: maybe), or
neither (stored: no). The header lists the database tooling the repo uses.

The scan is a list of places to read, not a verdict. Exit code is always 0.
"""
import argparse
import json
import re
from pathlib import Path

SOURCE = {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"}
SKIP_DIRS = {"node_modules", "dist", "build", "coverage", ".git", ".worktrees", ".next", ".output",
             ".vercel", ".turbo"}
TEST_FILE = re.compile(r"\.(test|spec|bench)\.\w+$")
DB_DEPS = ["prisma", "@prisma/client", "drizzle-orm", "kysely", "knex", "typeorm", "sequelize",
           "mongoose", "mongodb", "pg", "postgres", "mysql2", "better-sqlite3", "sqlite3",
           "@libsql/client", "@supabase/supabase-js", "firebase", "redis", "ioredis", "dexie", "idb",
           "localforage"]

FLAG = r"(?:is|has|did|was|should|can)[A-Z]\w*"
FLAG_SET = re.compile(r"\b(" + FLAG + r")\s*(?::\s*boolean\s*)?(?<![=!<>])[:=](?!=)\s*(true|false)\b")
FLAG_HOOK = re.compile(r"\[\s*(" + FLAG + r")\s*,\s*set\w+\s*\]\s*=\s*(?:React\.)?"
                       r"(?:useState|createSignal|signal|ref)(?:<boolean>)?\(\s*(true|false)\b")
FLAG_SETTER = re.compile(r"\bset((?:Is|Has|Did|Was|Should|Can)[A-Z]\w*)\(\s*(true|false)\b")
FLAG_COMBO = re.compile(r"!?\s*(?:[\w$]+\.)?(" + FLAG + r")\b\s*(?:\(\))?\s*(&&|\|\|)\s*!?\s*(?:[\w$]+\.)?("
                        + FLAG + r")\b")
STATUS_FIELD = r"(state|status|phase|mode|stage|step)"
STATUS_SET = re.compile(r"(?:\.|\b)" + STATUS_FIELD + r"\s*(?<![=!<>])=(?!=)\s*(['\"`])([\w-]+)\2")
STATUS_SETTER = re.compile(r"\bset(State|Status|Phase|Mode|Stage|Step)\(\s*(['\"`])([\w-]+)\2")
SCHEMA_CODE = re.compile(r"\b(pgTable|sqliteTable|mysqlTable|defineTable|createTable)\s*\(|@Entity\s*\(|"
                         r"new\s+(?:mongoose\.)?Schema\s*\(")
TRANSITION = re.compile(r"\btransitions?\b\s*[(:=]|\bfunction\s+transition\w*\s*\(|"
                        r"\bswitch\s*\(\s*[\w$.]*\b(?:state|status|phase|mode|stage|step)\s*\)", re.I)
STORAGE = re.compile(r"\b(localStorage|sessionStorage|indexedDB|JSON\.stringify|writeFile\w*)\b|"
                     r"\.(save|insert|insertOne|upsert)\s*\(")


def walk(root):
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).parts
        if any(p in SKIP_DIRS for p in rel[:-1]) or not path.is_file():
            continue
        yield path


def snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def database(root, files):
    tools, schema_text = set(), []
    for path in files:
        if path.name == "package.json":
            try:
                pj = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            for key in ("dependencies", "devDependencies"):
                for dep in pj.get(key) or {}:
                    if dep in DB_DEPS or dep.startswith("drizzle-"):
                        tools.add(dep)
        if path.suffix in (".prisma", ".sql"):
            tools.add(path.suffix[1:] + " files")
        elif "migrations" in path.parts:
            tools.add("migrations/")
        elif path.suffix not in SOURCE:
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        if path.suffix in SOURCE and "migrations" not in path.parts:
            if not SCHEMA_CODE.search(text):
                continue
            tools.add("table definitions in code")
        schema_text.append(text.lower())
    return sorted(tools), "\n".join(schema_text)


def stored(names, text, schema):
    for name in names:
        if re.search(r"\b(" + re.escape(name.lower()) + "|" + re.escape(snake(name)) + r")\b", schema):
            return "yes"
    return "maybe" if STORAGE.search(text) else "no"


def scan_file(path, rel, schema):
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return []
    found = []
    lines = text.splitlines()

    # Collect boolean flags and the lines that set them
    flags = {}
    for no, line in enumerate(lines, 1):
        for pattern in (FLAG_SET, FLAG_HOOK, FLAG_SETTER):
            for m in pattern.finditer(line):
                name = m.group(1)
                name = name[0].lower() + name[1:]
                flags.setdefault(name, {"values": set(), "line": no})["values"].add(m.group(2))

    # Find conditions that combine two of those flags
    combo = None
    for no, line in enumerate(lines, 1):
        for m in FLAG_COMBO.finditer(line):
            a, b = m.group(1), m.group(3)
            if a != b and a in flags and b in flags:
                combo = (no, " ".join(m.group(0).split()))
                break
        if combo:
            break
    toggled = [n for n, f in flags.items() if len(f["values"]) == 2]
    if combo or len(toggled) >= 3:
        names = sorted(flags)
        line = combo[0] if combo else min(flags[n]["line"] for n in toggled)
        detail = ", ".join(names) + (f"; combined in `{combo[1]}`" if combo else "")
        found.append({"kind": "flags", "file": rel, "line": line, "detail": detail,
                      "stored": stored(names, text, schema)})

    # Count string values per status field, unless the file has a transition function
    if not TRANSITION.search(text):
        fields = {}
        for no, line in enumerate(lines, 1):
            for pattern in (STATUS_SET, STATUS_SETTER):
                for m in pattern.finditer(line):
                    field = m.group(1).lower()
                    entry = fields.setdefault(field, {"values": [], "line": no})
                    if m.group(3) not in entry["values"]:
                        entry["values"].append(m.group(3))
        for field, entry in sorted(fields.items()):
            if len(entry["values"]) >= 3:
                found.append({"kind": "status", "file": rel, "line": entry["line"],
                              "detail": f"{field} = " + " | ".join(entry["values"]),
                              "stored": stored([field] + entry["values"], text, schema)})
    return found


def scan(root):
    files = list(walk(root))
    tools, schema = database(root, files)
    found = []
    for path in files:
        if path.suffix not in SOURCE or path.name.endswith(".d.ts") or TEST_FILE.search(path.name):
            continue
        found.extend(scan_file(path, path.relative_to(root).as_posix(), schema))
    return {"database": tools, "candidates": found}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    result = scan(Path(args.root).resolve())
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    print("database: " + (", ".join(result["database"]) or "none found"))
    if not result["candidates"]:
        print("no candidates")
    for c in result["candidates"]:
        print(f"{c['kind']:<7} {c['file']}:{c['line']}  {c['detail']}  [stored: {c['stored']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

---
name: scoped-checks
description: Run tests, lint, format and typecheck on the files a change touches instead of the whole project. Lint and format take the changed file paths, tests run the tests related to them, typecheck and build run on the packages that hold them. A full run is kept for config changes, the final gate on a repo with no CI, or when the user asks. Includes `checks.py --changed`, which builds the scoped commands for npm, pnpm, yarn, bun, Python and Go projects, and an optional hook that blocks full runs. Use this skill whenever about to run tests, a linter, a formatter, a type checker or the project's checks after editing code, verifying a fix or finishing a change, even if the user does not say "scoped".
---

# Scoped checks

A full test suite, typecheck or lint run after a small edit spends minutes and reads files the change never touched. Check what the change touches. Run the full set only when a reason below applies.

## Scripts

```
python3 <skill>/scripts/checks.py <dir>                              # list the detected checks
python3 <skill>/scripts/checks.py <dir> --changed <base>             # show the scoped commands
python3 <skill>/scripts/checks.py <dir> --run --changed <base>       # run them
python3 <skill>/scripts/checks.py <dir> --run --changed --only test  # one kind, against the default branch
python3 <skill>/scripts/checks.py <dir> --run [--install]            # the full set
```

`--changed` reads the files changed since the merge base with `<base>`, plus uncommitted and untracked files. Without a value it uses the default branch.

## While editing

After each edit, check only that edit:

- Run the linter and formatter on the edited files. Take the command from the lint or format script and pass the paths, for example `pnpm exec oxlint --type-aware src/a.ts` or `pnpm exec oxfmt --check src/a.ts`.
- Run the test file that covers the edit, for example `pnpm exec vitest run src/a.test.ts`. When you do not know which tests cover a file, run `vitest related --run src/a.ts` or `jest --findRelatedTests src/a.ts`.
- Skip typecheck and build after each edit. Run them once when the change is done.

## When the change is done

Run `checks.py <dir> --run --changed <base>` once. It scopes each check:

| Check | Scope |
| --- | --- |
| lint, format | the changed files with an extension the tool reads |
| test | `vitest related`, `jest --findRelatedTests`, or the test files named after a changed file (pytest, `node --test`) |
| typecheck, build | the packages that hold a changed file, and their dependents in a pnpm workspace |
| Go | the packages that hold a changed `.go` file |

The script falls back to a full run of a check when:

- a config file changed (package.json, a lockfile, tsconfig, `*.config.*`, `.*rc`, pyproject.toml, Cargo.toml, go.mod). A config at the root runs everything. A config in a package runs that package.
- the script cannot be scoped, such as one that chains commands with `&&`.
- more than 400 files changed.
- the project type has no scoping (Cargo, Makefile).

A check with no related files is skipped.

## When to run the full set

- The user asks for it.
- This is the last check before merge, and the change touches a module other packages import. The repo also has no CI that runs the full set (a private repo, or no check workflow).
- A test outside the module graph may depend on the change, such as an end-to-end test or a snapshot of generated output.

Say in the report or PR which checks ran scoped and which ran in full.

## What scoping misses

- Outside a pnpm workspace, typecheck does not cover the packages that depend on a changed one.
- pytest and `node --test` find tests by file name only. A test with another name that imports the changed file does not run.
- Go runs the changed packages, not the packages that import them.

When one of these matters for the change, run that check in full.

## Hook

`scripts/hook.py` is a PreToolUse hook on Bash that stops a full run of tests, lint, format or a workspace-wide typecheck. A run counts as full when it names no file and no single package: `pnpm test`, `vitest run`, `eslint .`, `pytest`, `go test ./...`, or `checks.py --run` without `--changed`. It is off by default. Turn it on with `SCOPED_CHECKS_HOOK=block` (or `warn`). To run a full check on purpose, prefix the command with `SCOPED_CHECKS=full`.

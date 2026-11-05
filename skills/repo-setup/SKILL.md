---
name: repo-setup
description: Set up a new or existing repository of this user that publishes a library to npm. pnpm workspaces, changesets, tsdown, vitest (Playwright for browser e2e), oxlint and oxfmt, an MIT license, a check workflow and a release workflow with npm trusted publishing (OIDC). Covers the folder layout (packages, examples, benchmarks, docs, website on Vercel), the manual 0.0.0-stage first publish, and GitHub environments for releases with more than one target. Use this skill whenever the user asks to set up, bootstrap, scaffold, initialize or modernize a repo, add CI or a release workflow, or bring an old repo up to their current setup, even if they do not say "repo-setup". Also use it to check an already set up repo for missing property-based, model-based or oracle tests and for implicit state machines.
---

# Repo setup

One setup for every npm library repo the user owns. talata and brumate are the reference repos: when a template here and those repos disagree, the newer repo wins, and this skill should be updated.

Use this skill only on repos the user owns (`gh repo view --json owner`). Repos of an organization, such as `solidjs/*`, keep their own conventions.

A repo that already matches the setup gets an audit with every line `ok`. Steps 4 and 5 still apply to it.

## The setup

- **Package manager**: pnpm, with `packageManager` set in the root `package.json`. A repo with more than one package is a pnpm workspace.
- **Releases**: changesets, with the changesets skill for each change.
- **Bundler**: tsdown for each published package.
- **Tests**: vitest. Playwright only when the library runs in a browser, as an `e2e/` workspace package. fast-check only in packages that need property, model or oracle tests (step 4).
- **Lint and format**: oxlint extending `@lxsmnsyc/oxlint-config`, and oxfmt.
- **License**: MIT.
- **Workflows**: `check.yml` (lint, format, types and tests on pull requests and on `main`) and `release.yml` (changesets, publishing to npm with trusted publishing).
  - Draft pull requests skip the check until they are marked ready, so review fixes do not use CI minutes.
  - A new push cancels the older run of the same pull request (`concurrency` with `cancel-in-progress` on pull requests only). Runs on `main` are never cancelled.
  - Changes only under `docs/**` skip both workflows. Roadmaps, debates, proposals and decisions are not build inputs and carry no changesets. The website's docs live in `website/` and stay covered.
- **Folders**:
  - `packages/` for the published packages
  - `examples/` for examples
  - `benchmarks/` for measurements
  - `docs/` for roadmaps, debates, proposals and decisions. Nothing in it is a build input.
  - `website/`, only when the project needs a website. It is the central place for user documentation, and that documentation lives in `website/`. Build it with brumate or Solid 2.0, and deploy it on Vercel.

## Templates

`templates/` holds the files to copy. Replace each `<...>` placeholder.

| Template | Goes to |
| --- | --- |
| `package.json` | root `package.json` (merge into an existing one) |
| `pnpm-workspace.yaml` | root, keep only the folders the repo has |
| `changeset-config.json` | `.changeset/config.json` |
| `oxlint.config.ts`, `oxfmt.config.ts` | root |
| `tsdown.config.ts`, `vitest.config.ts` | each package folder |
| `LICENSE` | root, with the current year |
| `gitignore` | `.gitignore` |
| `workflows/check.yml`, `workflows/release.yml` | `.github/workflows/` |
| `workflows/release-extra-target.yml` | jobs to add to `release.yml` for a second target |
| `vercel.json` | `website/vercel.json` |

The templates hold no tool versions. Install each tool at its latest version, for example `pnpm add -Dw @changesets/cli@latest oxlint@latest oxlint-tsgolint@latest oxfmt@latest @lxsmnsyc/oxlint-config@latest typescript@latest`, and `pnpm add -D tsdown@latest vitest@latest` in each package. Set `packageManager` from `npm view pnpm version`. For the GitHub Actions versions (`actions/checkout`, `pnpm/action-setup`, `actions/setup-node`, `changesets/action`), copy the majors from the newest reference repo's workflows. A major on the npm `next` tag is not the latest: Solid 2.0, for example, is a release candidate, so pin its exact version.

## Steps

### 1. Audit

```bash
python3 <skill>/scripts/audit.py <repo>          # add --offline to skip the npm lookups
```

It lists each part of the setup as `ok`, `missing`, `migrate` (something else is there) or `info`. It also says which published packages are not on npm yet. For a new repo, every line is `missing`. Show the list to the user before editing.

### 2. Branch

A new repo starts on `main`. An existing repo gets one setup branch (`chore/repo-setup`) and one setup pull request through the pr-author skill.

### 3. Apply

Work through the audit list. For each `migrate` line, replace the old tool and remove its config and dependencies:

- biome, eslint or prettier: oxlint and oxfmt. Run `pnpm lint:fix` and `pnpm format` once, in a commit of their own, so the reformat is easy to skip in a review.
- tsup, rollup or unbuild: tsdown. Keep the package's `exports` map, and compare the file list of `npm pack --dry-run` before and after.
- jest, mocha or ava: vitest. Port the config, then run the tests.
- npm, yarn or bun: pnpm. Delete the other lockfile and run `pnpm install`.
- an npm token in the release workflow: the template's trusted publishing. Remove the `NPM_TOKEN` secret after the first release from CI.
- `benchmark/`: rename it to `benchmarks/`.

Then run every check locally: `pnpm install`, `pnpm build`, `pnpm lint`, `pnpm format:check`, `pnpm typecheck`, `pnpm test`. The check workflow runs the same scripts, so a script that is missing locally fails in CI.

### 4. Test depth

Decide for each package, and for each module with real logic, whether it needs generated tests. Read `references/testing.md`.

- **Property tests** for functions with a rule that holds for every input. Examples: round-trips (parse and print), laws (sort, merge, normalize), no throws on valid input.
- **Model tests** for objects whose behavior depends on the order of calls: caches, stores, queues, reactive graphs, state machines.
- **Oracle tests** where a trusted reference gives the right answer: an older version, a native API, a simpler implementation.

Most modules need none, and then the step adds nothing. When one does, install fast-check in that package only and write the tests in its vitest suite. Show the user the decision per module, with the reason, before writing tests. The audit's `fast-check` line says which packages have it already.

### 5. Implicit state machines

Scan for state spread over several flags or status strings with no list of allowed transitions. Read `references/state-machines.md`.

```bash
python3 <skill>/scripts/scan_states.py <repo>
```

Read each candidate and drop the false ones. Then check whether the state is stored:

- **Not stored** (memory only): replace it with a discriminated union and a transition function.
- **Stored, but no database holds data for it yet**: fix it and the schema together. When the scan lists database tooling, ask the user whether a deployed or shared database holds data before you decide this.
- **Stored with existing data**: do not change it. Propose the new states and a migration of the old values, and wait for the user.
- **Exported from a published package**: keep the old fields as values read from the new state, or ask for a `major` changeset.

Each fix is its own pull request through pr-author, after the setup pull request, with a model test (step 4) that checks the new transitions.

### 6. Release targets and environments

Count the release targets. npm is one. A VS Code extension, a browser extension, or anything published by hand or to another registry is another.

- **One target**: no GitHub environments. Use `release.yml` as it is.
- **More than one**: each publish job gets its own environment. Add `environment: npm` to the npm publish job, and add a job per extra target from `release-extra-target.yml`, adapting its steps to that target. Tell the user which environments to create under Settings, Environments, and which secrets each one needs. Packages that are not published to npm go into `ignore` in `.changeset/config.json`, or are marked `"private": true`.

### 7. First publish of a new package

npm trusted publishing can only be set up for a package that already exists on npm. For each package the audit reports as not on npm, the skill does not publish. It gives the user these three reminders in order, and waits for the user to finish each one.

**1. Publish the placeholder.** From the package folder, with `version` set to `0.0.0-stage`:

```bash
pnpm build
npm publish --access public --tag stage --otp=<code from your authenticator>
npm view <pkg> dist-tags
```

The last command shows whether npm also pointed `latest` at the placeholder. Report what it shows.

**2. Set up trusted publishing on npmjs.com.** Open the package page, then Settings, then Trusted Publisher, and pick GitHub Actions:

- Organization or user: the repo owner
- Repository: the repo name
- Workflow filename: `release.yml`, the file name only
- Environment: empty, unless step 6 added environments. Then use the npm publish job's environment name.

Or from the command line, with npm 11.15.0 or later and 2FA on the account:

```bash
npm trust github <pkg> --file release.yml --repo <owner>/<repo> --allow-publish
npm trust list <pkg>
```

Add `--env <name>` when step 6 added environments. `npm trust` ignores workspaces, so name each package. A package holds one trust configuration: to change it, find its ID with `npm trust list` and remove it with `npm trust revoke <pkg> --id <id>` first.

After the first release from CI works, set Publishing access to "Require two-factor authentication and disallow tokens".

**3. Set up GitHub Actions.**

- The publish job already has `permissions: id-token: write`. No `NPM_TOKEN` secret is needed.
- Under Settings, Actions, General, turn on "Allow GitHub Actions to create and approve pull requests". Without it, changesets cannot open the version pull request.
- Create the environments from step 6, if any, with the same names as in the workflow.

Then set the package's `version` to `0.1.0`. Do not add a changeset for the first release: changesets publishes any version that is not on npm yet.

### 8. Website

Only when the project needs one. Create `website/` with brumate or Solid 2.0, as a workspace package that reads its pages from `docs/`. Copy `templates/vercel.json` to `website/vercel.json`, and set `outputDirectory` to what the framework builds. The template deploys only `main`. Tell the user to import the repo on Vercel with `website` as the root directory. Add `website` to `ignore` in `.changeset/config.json`.

### 9. Push

Before the first push, check the visibility with `gh repo view --json visibility`, or with pr-author's `ci_guard.py`. On a private repo, the new workflows start billed Actions runs, so do not push until the user says so. On a public repo, push the branch and open the setup pull request through pr-author. A new repo pushes `main`.

After the first release from CI, check the provenance with `npm view <pkg>@<version> dist.attestations`.

## Rules

- Only repos the user owns.
- Never publish to npm for the user. Give the command and wait.
- Never push to a private repo without asking.
- Never change how stored state is represented while a database or saved data may hold it, unless the user approves the migration.
- Never add a tool version from memory. Read it from npm or from the newest reference repo.
- An existing repo keeps its own choices, such as an extra workflow, a Node version in `engines` or extra oxlint rules. Ask when one conflicts with the setup.

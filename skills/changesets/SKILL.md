---
name: changesets
description: Write the changeset for a change in a repo that releases with changesets (a `.changeset/` folder exists). The bump level follows one question, whether the thing existed before: patch for changed behavior, minor for something new, major only with the maintainer's approval. Use this skill whenever finishing a change, opening a pull request or reviewing one in such a repo, even when nobody asks for a changeset, and when the user asks about bump levels or changelog entries.
---

# Changesets

In a repo that releases through [changesets](https://github.com/changesets/changesets), a changeset is part of finishing the work, not a step somebody has to ask for. Check for a `.changeset/` folder; without one, this skill does not apply.

## What gets one

A changeset describes what changed **against the release branch** (usually `main`), not against the last commit.

A branch often adds something and then corrects it a few commits later. Nobody reading `CHANGELOG.md` ever saw the broken version, so the correction gets **no changeset of its own**. Amend the feature's changeset instead if it now says something untrue.

The test is one question: did the behavior being fixed ever reach a release? A fix for something users have today, or anything the release branch does not have at all, gets a changeset.

Changes users never see get none: tests, internal tooling, CI, docs that do not ship with the package. When unsure, ask whether the entry would mean anything to someone reading the changelog.

## The bump level

The question is not how big the change looks. It is **whether the thing existed before**.

- **`patch`**: something that already existed now behaves differently. A bug fix, a retuned number, a rewritten internal path, a relaid screen, a performance win. All of these are `patch`, however different the result looks.
- **`minor`**: something exists that did not exist before. A new export, option, command, screen, event or field callers can set. If a user could not reach it yesterday and can today, it is `minor`.
- **`major`**: ask first. Never write one on your own judgment. Say what you think warrants it (a removed export, a changed signature, a changed default that breaks callers) and let the maintainer decide.

One change often does both: adding a new option is `minor`, retuning an existing default is `patch`. When one changeset covers both, take the higher level.

Packages before 1.0 often treat `minor` as breaking. Follow the repo's `.changeset/config.json` and its history; when the two rules conflict, ask.

## The file

A markdown file in `.changeset/`, named in kebab-case as a short sentence about the change, not a ticket or a component: `empty-carts-total-zero.md`, `tax-rounds-half-up.md`.

```markdown
---
'<package-name>': patch
---

One line saying what is true now.
```

Take the package name from the `name` field of the package's `package.json`. In a monorepo, list every package whose published behavior changed, each with its own level, and nothing else.

## The prose

- **One line for one change.** A changeset is a changelog entry: it says what is true now and stops. Leave out the reasoning, the trade-offs and what it replaced.
- **Several changes**: a list, one line each.

  ```markdown
  ---
  'cart': patch
  ---

  - Subtotals include the first item in the cart.
  - Discounts round half up instead of losing a cent on some totals.
  ```

- Write for someone reading `CHANGELOG.md`, not the diff. Name the behavior, not the file or the function.
- Follow the plain-writing rules if that skill is installed: no em-dashes, plain sentences, no build-up. Wrap like the files already there.
- When a change alters data or output that existing users already have (a saved format, generated content, a migration), say so on its own line.

## Before concluding one is missing

The release step folds every changeset into `CHANGELOG.md` and empties `.changeset/`, so a folder holding only `README.md` and `config.json` does not mean work went unrecorded. Check `CHANGELOG.md` before writing a second entry for something already released.

## Held for a later release

Every changeset on the release branch ships with the next release. A pull request can be held for a later release, by a roadmap fence or by the maintainer. Keep its changeset in the pull request and hold the merge. Do not remove the changeset to slip the code into the current release, because the change would then ship with no changelog entry.

## In reviews

When reviewing a pull request in such a repo, check that it has a changeset when it should, that the level follows the rules above, and that a `major` was approved. A missing or wrong changeset is a should-fix finding, not a blocking one.

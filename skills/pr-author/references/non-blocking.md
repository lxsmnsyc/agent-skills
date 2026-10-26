# Non-blocking pull requests

A pull request blocks others when another PR cannot merge before it, when it cannot merge before another, or when merging it breaks something until a later PR lands. These patterns avoid all three.

## One concern per PR

A fix, a feature, a refactor and a formatting change each get their own PR. Mixed PRs are slower to review, harder to revert, and make an urgent fix wait for an unrelated feature.

When you notice something unrelated while working, write it down and do it in its own branch, or leave it for later. Do not let it into the current diff.

## Small

A PR a reviewer reads in one sitting gets reviewed quickly. As a guide, under about 400 changed lines of non-generated code. A large change usually splits along one of these lines:

- Preparation first: a pure refactor or file split with no behavior change, then the change itself.
- Per area: the same change in several modules, one PR each.
- Expand, migrate, contract (below).

## Mergeable alone

- **Feature flags.** Code for an unfinished feature can merge when it is off by default or unreachable. Remove the flag in a final PR.
- **Expand, migrate, contract.** To change an API: add the new form next to the old one (expand), move callers over in separate PRs (migrate), then remove the old form (contract). Every step keeps the main branch working.
- **Stubs for missing parts.** When code needs something another PR is building, build against an interface with a stub, and swap in the real thing when it lands. The parallel-roadmap skill calls this a `behavior` dependency.
- **Database changes.** Add columns and tables first, write to both old and new, backfill, switch reads, then drop the old. Never rename or drop in the same PR that starts using the new form.

## Shared files

Conflicts come from files many PRs touch: route registries, config, barrel exports, changelogs, lockfiles.

- Append to lists instead of inserting in the middle.
- Do not reformat or reorder a shared file in a feature PR.
- Prefer one file per feature with discovery over a central list. If a central list causes repeated conflicts, propose splitting it in its own PR.
- Lockfiles: add a dependency in a PR of its own when several PRs need it, or merge those PRs one at a time and regenerate the lockfile.
- Numbered files (migrations, decision records): take the next number at the last moment before merge, or use the number your roadmap node reserved.

## Stacked PRs

Stack only when a PR truly needs another one's code. Then:

- Open the dependent PR with the other branch as its base, or against the main branch with "Depends on #N" at the top of the description.
- Keep the stack short. Two is fine, four is a sign the work should be split differently.
- After the bottom PR merges, rebase the next one onto the main branch.

## Keeping up with the base

Rebase onto the base before asking for review, and again when it conflicts. Rerun the checks after every rebase. Push with `--force-with-lease`, never plain `--force`, so you do not overwrite someone else's push.

# Is the version maintained?

`versions.py` reads what the repo shows. This page covers the cases it cannot settle.

## Where maintainers say it

In order of weight:

1. A support table in `SECURITY.md` or `SUPPORT.md`. `versions.py` reads these. A table that lists only security fixes still says which lines get any fix at all.
2. A "Supported versions", "Release policy" or "LTS" section in the README or the docs site. Search for those words, then read the dates.
3. npm metadata. `npm view <pkg>@<major> deprecated` prints a message when a line is deprecated. A dist-tag such as `v1-lts` or `legacy` that points into a line means someone still publishes it.
4. Activity. Commits on a maintenance branch, or releases from it, in the last year. This is the weakest sign, and `versions.py` marks it `likely`.

When none of these exist, the current line (the default branch) is the only one you can count as maintained.

## Writing it down

Name the source in the Affects table, so a maintainer can correct you:

- `yes, SECURITY.md`
- `yes, current line`
- `unclear, no support policy; release/1.x had a release in 2026-08`
- `no, npm deprecated: "1.x is no longer supported"`

## The runtime

A bug can need an old runtime, such as Node 16 or an old browser. Check whether the repo still supports that runtime: `engines` in `package.json`, the CI matrix in `.github/workflows/`, and the runtime's own schedule (Node release lines reach end of life about 30 months after release). A bug that shows only on a runtime the repo dropped is the same as a bug in an unmaintained line: open no issue, and tell the user.

## The user's version is old

When the user runs an unmaintained line and the current line also shows the bug, open the issue against the current line and list the user's version as a row. When only the user's line shows it, the fix is an upgrade. Tell the user which version to move to and what changed on the way, from the changelog.

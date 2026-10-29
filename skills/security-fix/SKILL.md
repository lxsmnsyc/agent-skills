---
name: security-fix
description: Fix a security vulnerability without leaking it before the release. Work happens on a local-only branch that is never pushed, then merges straight into the branch the release workflow publishes from. The fix becomes public at the same moment CI publishes the release, so the package keeps npm provenance. Use this skill whenever the user asks to fix a security issue, vulnerability, advisory, CVE or GHSA, or when other work finds one, even if they do not say "security-fix".
---

# Security fix

The fix must not be public before the release ships, and the release must still go through CI so it keeps its provenance attestation. A manual `npm publish` drops provenance, and package managers with trust policies (pnpm `trustPolicy: no-downgrade`) then refuse to install the version.

## Rules

- Never push the fix branch to any remote.
- Never open a pull request, issue or public comment about the vulnerability. Comments on the draft advisory are private to its collaborators, so they are the place for the details.
- Never publish manually. CI publishes once the release branch is pushed.
- Keep commit messages and changelog lines plain (for example, "fix: harden input validation in X"). The details go in the advisory, not in git.

## Found during other work

A subagent that finds a vulnerability, such as a roadmap worker or a pr-author or pr-review run, does not fix it in its own branch. It does not push anything about it either. It stops and reports the finding to the orchestrator, which tells the user. The fix then starts at step 1 of this skill.

## Working with others

When the reporter or a co-maintainer works on the fix too, use the advisory's temporary private fork in place of the local-only branch. A draft GitHub Security Advisory has a "Start a temporary private fork" button. GitHub Actions do not run in that fork, so the local checks of step 7 are still the only verification. Merging the fork's pull request publishes the fix. Merge only when it holds the version bump of step 8 and step 9 passed. The rest of the steps still apply.

## Steps

1. Find the release branch: the branch whose push triggers the publishing workflow. Read the `on.push.branches` trigger of the release workflow in `.github/workflows/` (for example `main`, `next` or `release/1.x`). If several branches qualify, or the affected version line is released from a maintenance branch, ask the user which one to use. The steps below call it `<release-branch>`.
2. Draft the GitHub Security Advisory if none exists yet (`gh api repos/{owner}/{repo}/security-advisories` or the Security tab), and request a CVE on the draft. A draft stays private. The CVE can take a few days, so ask for it before the release, not after.
3. Review the advisory description. The description is published with the advisory, so it must not teach anyone how to exploit the vulnerability. A description from the reporter often does.
   - Post the original description as a comment on the advisory first, so the details stay with the collaborators. Quote it in full and say it is the reporter's original text.
   - Rewrite the description with the plain-writing skill, under these headings:
     - **Summary**: one or two sentences on the vulnerability class (the CWE) and the affected package.
     - **Impact**: who is affected and what an attacker can do, in general terms.
     - **Affected versions** and **Patches**: the vulnerable range and the patched version once it exists.
     - **Workarounds**: what users can do before they upgrade, or "None".
     - **References**: the CVE and links that are already public.
   - Remove proof-of-concept code, payloads, exact requests, step-by-step reproduction, the vulnerable file and line, internal hosts and paths, and any secret or token.
   - Update the draft with `gh api -X PATCH repos/{owner}/{repo}/security-advisories/{ghsa_id} -F description=@<file>`. Write `<file>` to a temporary folder outside the repo.
   - Post the comment with `gh api repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments -F body=@<file>`. Fix a comment with `gh api -X PATCH repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments/{comment_id} -F body=@<file>`.
4. Update the local `<release-branch>` from the remote (`git fetch origin && git switch <release-branch> && git merge --ff-only origin/<release-branch>`).
5. Create a local-only branch from `<release-branch>`, for example `security/<short-name>`. Do not set an upstream for it. Then guard it against pushes:
   - When `git config core.hooksPath` prints nothing, add a pre-push hook to `.git/hooks/pre-push` that refuses `refs/heads/security/*`. It blocks `git push`, `git push --all` and `git push --mirror` of the branch, and still lets `<release-branch>` push after the merge. If a `pre-push` hook already exists, add the check at its top instead of replacing it.

     ```sh
     #!/bin/sh
     while read local_ref local_sha remote_ref remote_sha; do
       case "$local_ref" in refs/heads/security/*) echo "pre-push: refusing to push $local_ref" >&2; exit 1;; esac
     done
     ```

     Make it executable with `chmod +x`.
   - When `core.hooksPath` is set (husky and similar tools), git ignores `.git/hooks`, and the hooks folder is usually tracked. Do not write there. Tell the user the branch has no push guard.
6. Confirm the vulnerability on the branch. Write a test that reproduces it on the code of `<release-branch>` and check that the test fails. This test becomes the regression test of step 7.
   - When it reproduces, leave a comment on the advisory. Say the vulnerability is confirmed, name the version and commit, and say a fix is in progress. Post it the same way as the comment of step 3.
   - When it does not reproduce, do not start a fix. Tell the user, and ask the reporter for the missing details in an advisory comment.
   - Reject the advisory when it still does not reproduce consistently after the reporter answers, or when it does not merit an advisory. A normal bug with no security impact does not merit one. Neither does documented behavior, or an attack that needs access the attacker already has.
   - To reject, ask the user first. Then leave a comment that says why the advisory is rejected, and close it with `gh api -X PATCH repos/{owner}/{repo}/security-advisories/{ghsa_id} -f state=closed`. Delete the local branch and the pre-push check of step 5. A normal bug can then go through a public issue or pull request, without the reporter's exploit details.
7. Apply the fix and keep the regression test of step 6 on that branch. Run the project's checks locally (build, typecheck, tests). CI does not see the code before the merge, so this is the only verification.
8. Bump the version on the branch so pushing `<release-branch>` publishes right away instead of opening a version PR. In a repo that uses changesets:
   - Check that `.changeset/` on `<release-branch>` has no other pending changesets. If it does, ask the user whether to release those first or include them.
   - Check `.changeset/pre.json` for prerelease mode, which changes the version the bump produces.
   - Run `pnpm changeset` (patch) and then `pnpm changeset version`, so the bumped `package.json` and the `CHANGELOG.md` entry are committed and no `.changeset/*.md` file remains.
9. Check that the release workflow can publish with provenance. A publish that fails after the push leaves the fix public with no release. In the release workflow:
   - the publishing job has `permissions: id-token: write`
   - it publishes with `--provenance`, `NPM_CONFIG_PROVENANCE=true`, or the package has `"publishConfig": { "provenance": true }`
   - it authenticates with an npm token secret or npm trusted publishing

   If any is missing, stop and tell the user. Do not fix the workflow in the same push.
10. Merge the branch into the local `<release-branch>` (fast-forward when possible).
11. Confirm with the user, then push `<release-branch>` (`git push origin <release-branch>`). This is the moment the fix becomes public, and it triggers the release workflow. Before pushing, check the repo visibility with `gh repo view --json visibility`. Do not push when the repo is private, because Actions minutes are billed. Ask the user instead.
12. Watch the release run and confirm the new version is on the registry with provenance (`npm view <pkg>@<version> dist.attestations`). The registry can lag a few minutes after a publish.
13. Publish the advisory with the patched version in it, or remind the user to publish it.
14. Remove the pre-push check added in step 5 and delete the local branch (`git branch -D security/<short-name>`).
15. In a repo with several integration branches (gitflow), merge `<release-branch>` back into the branches listed under `back_merge` by `python3 <skills>/pr-review/scripts/branch_policy.py`, for example `next` then `dev`. The fix is public now, so these can go through normal pull requests. Other supported version lines, such as a maintenance branch, need their own run of this skill. Tell the user which ones.

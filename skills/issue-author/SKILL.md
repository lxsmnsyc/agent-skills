---
name: issue-author
description: Write and open GitHub issues that a maintainer can act on, such as bug reports, feature requests and diagnosis handoffs, in the user's repo or someone else's. Searches open and closed issues and pull requests for duplicates first, follows the repo's own issue templates and labels, reproduces a bug on the latest release and on every release line the repo still maintains, and lists which lines it affects. Opens no issue for a bug that shows only in unmaintained versions, and none for a security problem, which goes to a private report or the security-fix skill instead. Use this skill whenever the user asks to open, file, write, draft or report an issue or a bug, when root-cause returns a fix-large verdict, or when pr-author finds a bug too large for a fix PR, even if they do not say "issue".
---

# Issue author

An issue asks for a maintainer's time. Open one only when the problem still exists, in a version someone still fixes, nobody has reported it yet, and the issue holds enough to reproduce it without a follow-up question.

## Scripts

```bash
python3 <skill>/scripts/versions.py [--cwd <repo>] [--offline]       # release lines: maintained, likely or unmaintained, and why
python3 <skill>/scripts/affects.py --ref main --ref v1.9.4 [--copy <test>] [--setup 'npm ci'] [--symptom '<regex>'] -- <command>
python3 <skills>/plain-writing/scripts/check_prose.py <draft>         # prose check of the draft
```

`affects.py` runs one reproduction on each ref in its own worktree and calls each one `affected`, `not-affected`, `other-failure` or `error`.

## Rules

- **A security problem never becomes an issue.** Before you write anything, ask: could someone use this to harm the project's users? That covers code execution, injection, auth or permission bypass, data exposure, path traversal, crafted input that crashes or hangs a server, and leaked credentials. If yes or unsure, stop. Write no issue, comment, pull request or public draft, and do not mention it in other issues.
  - In the user's own repo, hand it to the security-fix skill.
  - In someone else's repo, find the private channel: the contact in `SECURITY.md`, or GitHub private vulnerability reporting (`gh api repos/<owner>/<repo>/private-vulnerability-reporting` returns `"enabled": true`, then the Security tab's "Report a vulnerability"). Write the report in `.git/issue-author/<slug>/report.md` and give it to the user to send. Do not send it yourself. With no private channel, tell the user and stop.
- **Keep drafts local.** Write every draft in `.git/issue-author/<slug>/`. Git never commits that folder.
- **Redact** tokens, keys, internal hostnames, user names and personal data in logs and reproductions. Write `<REDACTED>`.
- **Opening an issue is visible to others.** When the user asked for the issue, open it: the request already answered that. When another skill routes the work here (root-cause `fix-large`, pr-author's large fix), show the draft and ask first. Say that "no" keeps the draft in `.git/issue-author/<slug>/issue.md`. The same holds for a comment on an existing issue.
- Write by the plain-writing rules if that skill is installed, and run its checker on the draft.

## Steps

### 1. Find the repo that owns it

A stack trace that ends in `node_modules/<pkg>` belongs to that package, unless your code calls it wrongly. Find its repo with `npm view <pkg> repository.url bugs.url`. Report upstream, with the version you run.

Read the repo's own rules: `.github/ISSUE_TEMPLATE/` (Markdown templates and `.yml` issue forms), its `config.yml`, and `CONTRIBUTING.md`. For a repo that is not checked out, use `gh api repos/<owner>/<repo>/contents/.github/ISSUE_TEMPLATE`. The repo's template wins over `templates/issue.md`: put this skill's content under the template's headings. `gh issue create --body-file` skips an issue form, so copy each field's label as a heading in the body. When `config.yml` sends questions to Discussions or a forum through `contact_links`, a question goes there, not to an issue.

Labels: list them with `gh label list -R <owner>/<repo>` and use only existing ones. Do not create labels in someone else's repo. Without triage rights, a label you pass is dropped, so leave labels to the template.

When a roadmap runs in the user's repo, a gap that belongs to the plan goes to the roadmap inbox (parallel-roadmap, "Change"). Open an issue when the user wants it tracked in public.

### 2. Search for duplicates

Search open and closed issues and pull requests, with the symptom in a few words and the exact error message in quotes:

```bash
gh search issues --repo <owner>/<repo> --include-prs '"<exact error>"'
gh search issues --repo <owner>/<repo> --include-prs <symptom words>
```

Also read the changelog or release notes after the version that shows the bug.

- **An open issue reports it**: open no new one. When you have something it lacks (another affected line, a smaller reproduction, the cause), draft a comment with only that. Never post a "+1".
- **Closed as fixed**: find the release with the fix. When the user runs an older version, the answer is to upgrade. When the fixed version still shows it, open a new issue that starts with "Regression of #<n>".
- **Closed as not planned**: do not reopen or repost it. Tell the user and quote the maintainer's reason.
- **An open pull request fixes it**: link it to the user and stop.

### 3. Check the bug in maintained versions

Skip this step for a feature request.

1. Get a checkout. In someone else's repo, clone it into the draft folder: `gh repo clone <owner>/<repo> .git/issue-author/<slug>/repo -- --filter=blob:none`.
2. Run `versions.py` in it. Read `references/maintained.md` when it reports no support policy, or when the bug needs an old runtime.
3. Write the smallest reproduction you can: a test file or a short script. With none, the bug is not ready for an issue. Build one with the root-cause skill, or ask the user for the missing details.
4. Run `affects.py` on the default branch, the newest tag of each `maintained` and `likely` line, and the version the user runs. Pass `--copy` for the reproduction and `--setup` for the install.
5. Decide from the results:

| Result | What to do |
| --- | --- |
| Affected on a `maintained` line | Open it. List every line you ran under Affects. |
| Affected only on `likely` lines | Open it. Say under Affects that no support policy covers the line, and name the evidence from `versions.py`. |
| Affected only on `unmaintained` lines, not on the current line | Open no issue. Tell the user which version no longer shows it and which commit fixed it if `git log` or `git bisect` finds it. A backport request is the user's call, and it goes as a question to the maintainers, not as a bug. |
| Not affected anywhere, including the user's version | Open no issue. The reproduction misses something. Ask for the environment or use root-cause. |
| `other-failure` or `error` on a line | Fix the setup and run that line again. If it still cannot run, say under Affects which line was not tested and why. |

The same check applies to the user's own repo: a bug only in a line they no longer maintain needs no issue unless they say they still support it.

### 4. Write it

Fill `templates/issue.md` in `.git/issue-author/<slug>/issue.md`.

- **Title**: the symptom and its condition, in the repo's title style. `subtotal() skips the first item when the cart has two or more items`, not `Cart bug` and not a guessed cause.
- **Bug**: what happens (the exact error, quoted), what you expected, the reproduction as steps a maintainer can paste, the Affects table, and the environment (OS, runtime, package manager, the package version).
- **Feature**: the problem first. Who has it, what they do today, and what that costs them. Then the smallest change that would solve it. Do not design the API for a repo you do not maintain, unless its template asks for a proposal.
- **Diagnosis handoff** from root-cause: the cause at file and line as a permalink to a commit, the confirmed hypothesis, the regression test, the fix options with their cost, and why the fix is too large for one pull request.
- Write a cause only when it is confirmed. A guess goes under Notes and says it is a guess.

### 5. Open it

```bash
gh issue create -R <owner>/<repo> --title '<title>' --body-file .git/issue-author/<slug>/issue.md [--label <existing label>]
```

Report the link, what the duplicate search found, and the Affects result.

## What the user sees

```
Opened acme/cart#212: subtotal() skips the first item when the cart has two or more items
Duplicates: none open; #180 (closed, fixed in 2.1.0) is a different off-by-one
Affects: 2.x affected (main a1b2c3d, v2.3.1), 1.x affected (v1.9.4, SECURITY.md supports 1.x), 0.x not tested (unmaintained)
Reproduction: test/subtotal.repro.test.js, in the issue body
```

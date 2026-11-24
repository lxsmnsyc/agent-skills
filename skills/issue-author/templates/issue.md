<!--
Fill the part that matches the issue and delete the other parts.
When the repo has its own issue template, use its headings instead and move this content under them.
Leave out a section with nothing in it.
-->

<!-- Bug -->

## What happens

<The symptom in one or two sentences. Quote the exact error or wrong output.>

```
<error or output, redacted>
```

## Expected

<What should happen instead, and where the docs or types say so, if they do.>

## Reproduce

<Steps a maintainer can paste. Prefer one test file or script over prose.>

```<lang>
<minimal reproduction>
```

```bash
<command that shows it>
```

## Affects

| Line | Ref tested | Maintained | Result |
| --- | --- | --- | --- |
| <2.x> | <main a1b2c3d, v2.3.1> | <yes, current line> | <affected> |
| <1.x> | <v1.9.4> | <yes, SECURITY.md> | <affected> |
| <0.x> | <not tested> | <no> | <n/a> |

Environment: <OS>, <runtime and version>, <package manager and version>, <package>@<version>

## Cause

<Only when confirmed: file and line as a permalink to a commit, and how it was confirmed. Otherwise leave this out.>

## Notes

<Related issues or pull requests (#n), workarounds, a guess about the cause marked as a guess.>

<!-- Feature -->

## Problem

<Who has it, what they do today, and what that costs them, in numbers when you have them.>

## Proposal

<The smallest change that would solve it. Alternatives you considered, and why they fall short.>

## Notes

<Related issues, prior discussion, how other libraries solve it.>

<!-- Diagnosis handoff from root-cause -->

## What happens

<Symptom, quoted.>

## Cause

<File and line as a permalink to a commit. The hypothesis that was confirmed, and the loop that confirmed it.>

## Regression test

<Path or inline test. It fails on <ref> and should pass after the fix.>

## Fix options

| Option | Reach | Cost | Undo |
| --- | --- | --- | --- |
| <option> | <who runs the changed code> | <size, speed or memory> | <reverts alone, or changes data or API> |

<Why this does not fit one small pull request.>

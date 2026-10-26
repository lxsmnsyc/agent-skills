# Evaluation

How to judge whether a change works, and whether it is worth what it costs.

## Contents

- Correctness
- Simplicity
- Cost
- Risk
- Writing it down

## Correctness

- **Proof over reading.** A reproduction that fails on the base and passes on the head is worth more than any amount of reading the diff. Use `repro.py` for every fix.
- **When the problem does not reproduce.** The report is usually still true; the PR just tested the wrong input. Match the symptom exactly: "a cent too low" points to rounding or floating point, not to a missing item. Then search for inputs that show it. Loop over a range of values and compare against an exact computation, try boundaries (0, 1, halves, the largest values), and try the inputs named in the report. Report the smallest input that fails, on both base and head. Do not name a cause whose effect does not match the reported symptom.
- **Cause, not symptom.** A fix that special-cases the reported input often leaves the same bug one input away. Find the cause in the code, then check that the fix is at the cause. Search for other callers of the changed function and for similar code that has the same flaw.
- **Tests that would have caught it.** The PR should add a test that fails without the fix. If it adds none, say so, and give the reproduction you wrote as a starting point.
- **Edge cases.** Empty input, one item, very large input, concurrent calls, errors from dependencies, and whatever the problem statement hints at.
- **Behavior outside the claim.** Run the full test suite on the head, not only the new test. Changes in snapshot files or golden output need a reason.

## Simplicity

Ask whether a smaller change would do the same job. Signs that it would:

- New abstractions (classes, options, layers, generic helpers) with a single user.
- Code that handles cases that cannot happen.
- Duplicated logic that already exists elsewhere in the repo.
- Configuration added for something that has one sensible value.
- A large diff for a small behavior change, for example a rename mixed in.

When you suggest a simpler version, show it, at least as a sketch. "Could be simpler" without an alternative is a nit at best.

## Cost

Give numbers. A cost without a number is an opinion.

| Cost | How to measure |
| --- | --- |
| Build size | Build both worktrees, then `size_diff.py base head --glob '<output glob>'`. Report the gzip change of the files users download. |
| Runtime | Run the repo's benchmarks on both sides when the change touches code on a hot path (render loops, request handlers, tight loops, startup). Report the before and after and the command. Run each side at least twice; one run is noise. |
| Dependencies | For each new package: what it adds to the install and the bundle, its license, its last release, and whether the repo already has something that does the job. |
| API surface | New public exports, options, config keys, CLI flags, events. Each one is a promise to keep. Breaking changes need a changeset or release note and a migration path. |
| Data and migrations | New migrations, changed formats, saved state. Can it roll back? Does old data still load? |
| Maintenance | New files, new concepts a reader must learn, new external services. |

Compare the cost against the value. A 2kB increase for a fix to a common crash is cheap. A 2kB increase for an option nobody asked for is not.

## Risk

- **Blast radius**: how much breaks if this is wrong? Core paths used by every user rate higher than an isolated feature.
- **Coverage**: are the changed lines exercised by tests? A risky change in untested code needs a test before it merges.
- **Rollback**: can the change be reverted alone, or does it come with a migration or a format change?
- **Compatibility**: does it change behavior that users, plugins or other packages rely on?

High risk does not block a change by itself. It raises the bar for proof and tests.

## Writing it down

Every finding names the file and line, states the problem, gives the evidence (a command and its output, a number, a quote from the diff), and says what would resolve it. A finding without evidence is a question, so write it as a question.

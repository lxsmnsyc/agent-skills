# Premise

A review can check every line of a diff and still miss that the change should not exist in this form. The problem may not be real. It may be solved at the wrong layer. A feature already in the repo may cover it, or a smaller change may do the same job. Line-level findings on such a change are wasted: the author polishes code that should be replaced.

This file covers the first question of every review: is this the right change to make?

## Contents

- Write your own design first
- Questions to ask
- Comparing your design with the PR's
- Sorting premise findings
- When the premise is agreed elsewhere

## Write your own design first

In step 2b, before you open the diff, add a `## Premise` section at the top of `expectations.md`. Write it from the claim and the base worktree only:

```
## Premise
- Goal: <the outcome the change is for, in one sentence, in the user's terms, not the code's>
- Problem is real: <yes, shown by X | unproven | no, because Y>
- Cause or need: <where the problem comes from in the base code, with path>
- Options:
  1. Do nothing: <what it costs to leave it>
  2. Use what exists: <a function, option, config or dependency already in the repo that covers it, or "none found">
  3. <the smallest change that reaches the goal>
  4. <a change at a different layer, such as the caller, the data model or an upstream package>
- My pick: <option>, because <reason>
```

Search the base before you write "none found" in option 2. Grep for the domain words in the claim. Read the module the claim names, its neighbors, and the docs for that area. Most premise findings come from this search.

You write this before the diff for the same reason as the expectations: after reading the author's solution, it is hard to imagine another one.

## Questions to ask

| Question | Signs of a problem |
| --- | --- |
| Is the problem real? | No issue, no report, no reproduction. "Might be slow" with no measurement. A fix whose bug does not reproduce (`not-reproduced`). |
| Is the goal worth it? | The cost (size, API surface, maintenance) is larger than the benefit. Few users need it. It pulls the project away from its README or `GOAL.md`. |
| Does it treat the cause? | A cache over a slow call that runs N times in a loop. A retry around a race. A null check where the null should never be produced. A timeout raised to hide a hang. |
| Is it at the right layer? | A workaround in this repo for a bug in a dependency, which should get an upstream fix or a pinned version. A UI check for a rule the server must enforce. One caller fixed when the function is wrong for all of them. |
| Does it duplicate what exists? | A new helper next to one that does the same thing. A new option that an existing option already covers. A hand-written version of something a dependency already in `package.json` provides. |
| Is there a smaller version? | A new module where one line in an existing one would do. A config system for one value. A feature that could ship as a docs recipe. |
| Does it decide something the maintainer should? | A new public API, a new dependency, a change of default, a new direction for the project. |

## Comparing your design with the PR's

After you read the diff, compare the PR's approach with your pick before you look at any line:

- **Same approach, or the PR's is better**: say so in one line under "What I checked", and continue with the line-level review.
- **Different, and yours is better by evidence**: smaller, at the cause, reuses what exists, or cheaper by a number you can give. That is a premise finding. Show your option as a sketch, with paths and the code it would reuse.
- **Different, and you cannot tell which is better**: ask the author why they chose theirs over yours. That is a question, not a finding.

Your design can be wrong. You wrote it from the base without the author's context. When the diff, the PR body or the code shows a reason your option fails, record that and drop it. Do not argue a design you cannot back with evidence.

## Sorting premise findings

- **Blocking**: any of these.
  - The problem is not shown to exist.
  - The change treats a symptom, and you can show the cause that stays.
  - A feature already in the repo does the same job.
- **Should fix**: a smaller or simpler design reaches the same goal, and you can sketch it.
- **Needs a decision**: the goal or the cost is a choice only the maintainer can make. Put it to them as a question, with the options and their costs.

Premise findings go first in the review, above all other findings. When a premise finding is blocking, keep the rest of the review short. List only the line-level problems that would still apply after the redesign, and leave out nits. Polishing code that will be replaced wastes the author's time.

A review that has only line-level findings and no word on the premise is incomplete. When the premise holds, say why in one line ("Approach: matches my pick, cache at the source, see expectations").

## When the premise is agreed elsewhere

A roadmap node, an accepted issue or an ADR means someone has already agreed on the goal. Do not reopen it in the review. You can still question the approach, because a brief rarely fixes how to build something. When the brief itself looks wrong (it asks for a workaround, or something the repo already has), say so as a question to the maintainer. Do not make it a finding against the author, who did what the brief asked.

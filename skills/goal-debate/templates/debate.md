---
goal: <one sentence>
date: <YYYY-MM-DD>
rounds: <n of max>
status: proposed        # approved once the user signs off
roadmap: <path to the roadmap, or none>
supersedes: <earlier debate.md, or none>
decision: <link to the decision record entry, or none>
---

# Debate: <goal>

## Hypothesis

Research debates only. Fixed before any run. Change it only through a new debate.

- statement: <what is claimed to be true>
- metric: <what is measured, on what data>
- baseline: <current value, with its source>
- threshold: <value that counts as success, and how many runs or seeds>
- kill: <result or spend at which the idea is dropped>

## Settled structure

<What will be built, in the order it ships. One line per upheld proposal or adopted alternative, with its id.>

## Budget

- device: <limit, e.g. "at most 2 parallel worktrees, peak 3.5 GB for the caption job"> (<claim ids>)
- time: <limit, e.g. "backlog done within a week of overnight runs"> (<claim ids>)
- tokens: <limit, e.g. "about 1.5M for the roadmap, sonnet workers for S and M nodes"> (<claim ids>)
- <extra axis>: <limit> (<claim ids>)

## Rejected

- <alternative or proposal>: <why, in one line> (<claim id that beat it>)

## Scope changes

Roadmap debates only.

- <drop | park | merge | outline> <node ids>: <why> (<claim id>)

## Proofs

- <T id> for <claim id>: <question>. <done | abandoned>, <result> (cap <minutes> min, <tokens> tokens)

## Prior art

- <citation>: <what it found, including negative results> (<fact id>)

## Open risks

- <risk> (<claim id>): <spike | measurement | accepted, because ...>

## Answers from the user

- <question>: <answer>

## Overruled

- <claim id>: <the user's ruling and reason, or "none">

## Cost of this debate

- <rounds>, about <tokens> tokens

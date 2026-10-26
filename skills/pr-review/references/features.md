# Features

How to review a pull request that adds a feature.

## When the feature is on the roadmap

The roadmap node is the agreement on what to build. Review the PR against it:

1. Read the node's `brief.md` and the outcomes of its dependencies. If the repo uses the parallel-roadmap skill, `plan.py <root> context <id>` lists these files.
2. Check each acceptance criterion. Run the brief's `verify` command in the head worktree if it has one.
3. Check the diff stays inside the node's owned paths. Changes outside them are the usual cause of merge conflicts with other nodes running at the same time; each one needs a reason.
4. Check the contracts it uses or provides still match the code.
5. Then evaluate simplicity, cost and the required checks as for any change.

If the PR does less than the brief, say which criteria are missing. If it does more, the extra part is an unplanned feature (next section).

## When the feature is not on the roadmap

No one has agreed that this feature belongs in the project yet. Approving it would skip that decision, so the review becomes a proposal for the maintainer instead.

Judge its value:

- **Who needs it?** A linked issue, user reports, a dependent feature. "It would be nice" is weak evidence.
- **Does it fit the project's goals?** Read the roadmap's `GOAL.md` and the README. A feature that pulls the project in a new direction needs the maintainer's call more than a review.
- **What does it cost?** Size, maintenance, API surface, as in `evaluation.md`. Features are hard to remove once released.
- **Is there a smaller version?** Often a hook, an option on an existing feature, or a recipe in the docs gives most of the value.

Then write a comment that proposes it, in the same shape as a roadmap addition:

```
This adds <feature>, which is not on the roadmap yet, so it needs the maintainer's decision before approval.

Proposed roadmap entry:
- Title: <short title>
- Priority: <must | should | could | later>, because <evidence>
- Size: <S | M | L>, <files and lines>
- Owns: <paths>
- Depends on: <nodes or contracts, if any>

Questions for the maintainer:
- <the decisions only the maintainer can make>

What I checked so far: <checks and their results, proof if any>
```

When the maintainer accepts it (a roadmap node is added, or they say so in the thread), review the PR again against that node and continue with the normal approval hand-off. When they decline, say so plainly and suggest what part, if any, could land separately.

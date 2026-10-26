# Review format

Templates for what the review posts. Keep each comment short and exact. Every finding has evidence and a way to resolve it.

## Not approvable yet

Posted as one comment review (`gh pr review <n> --comment --body-file review.md`). Inline comments on specific lines are fine for findings tied to one line; put the summary in the review body.

```
Not ready for approval yet. <One sentence on the main reason.>

## Blocking
- `<path>:<line>`: <problem>. Evidence: <command and result, number, or quote>. To resolve: <what would fix it>.

## Should fix
- `<path>:<line>`: <problem>. To resolve: <fix>.

## Nits (optional)
- `<path>:<line>`: <suggestion>.

## Found on `<base>`, not caused by this PR
- `<path>:<line>`: <problem>. Suggest a separate fix PR against `<base>`.

## What I checked
- Proof: `<command>` fails on `<base>` (<result>), passes on this branch (<result>).
- Checks (local): lint <pass|fail>, typecheck <pass|fail>, build <pass|fail>, tests <pass|fail>.
- Cost: <size change, benchmark change, new dependencies>.
```

Leave out sections that are empty. When the reproduction could not be made, say so under Blocking and ask for the steps.

## Ready for maintainer approval

When the maintainer is someone other than the user in the session, post this as a comment review so they get notified. Mention the maintainer's real login.

```
Ready for maintainer approval, @<maintainer>.

- Proof: `<command>` fails on `<base>`, passes on this branch.
- Checks (local): lint pass, typecheck pass, build pass, tests pass.
- Cost: <numbers>.
- Roadmap: <node id, or "not a feature">.
```

When the maintainer is the user in the session, do not post this. Give them the same summary in the chat and the command `gh pr review <n> --approve`.

## Proposed feature

See `features.md` for the template used when a feature is not on the roadmap.

## Tone

- Write about the code, not the author.
- State facts and evidence. Do not soften blocking findings into suggestions, and do not inflate nits into problems.
- One comment per problem. Do not repeat a finding across files; list the places in one comment.

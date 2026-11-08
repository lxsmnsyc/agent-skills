# Pull request description

Use this layout. Leave out sections that do not apply. Keep it short, exact and free of narration. If the plain-writing skill is installed, follow its rules.

```
<One or two sentences: what changes and why.>

Depends on #<n>                      <- only for stacked PRs, as the first line

## Changes
- <one sentence per change>

## Proof
- Fails on `<base>`: `<command>` (<result>)
- Passes on this branch: `<command>` (<result>)

## Checks
- Local: lint <pass>, typecheck <pass>, build <pass>, tests <pass>

## Roadmap
- <node id and path to its brief, or "none">

## Cost
- <bundle size change, new dependencies, migrations; numbers where measured>

## Risk
- <what could break, and how it is covered>

## Not done
- <known gaps, nits left from review, follow-up PRs>
```

## Titles

Use the repo's convention, usually `type(scope): summary` in the imperative, under 72 characters. Match the type to the change: `fix` only when there is a bug that the Proof section shows on the base.

## Proof for fixes and optimizations

For an optimization, the Proof section gives the measured cost on the base and on the branch. Give the noise too, for example the median and MAD over alternating runs. A gain inside the noise is not proof, and such a change gets no pull request.

The Proof section is what lets the reviewer approve quickly. Name the exact command, and the result on each side (exit code, or expected and actual values). The reviewer will run the same command.

---
title: Upgrade from <old major> to <new major>
type: migration
---

<What the new version changes for users, and how long the upgrade takes for a typical project.>

## Before you start

- <Upgrade to the latest <old major>.x first and fix its deprecation warnings.>
- <A codemod, if there is one: `<command>`.>

## Breaking changes

### <Change, named by what the reader used>

<What changed and why, in one or two sentences.>

Before:

```ts
```

After:

```ts
```

## Deprecations

- `<old>` is deprecated. Use `<new>`. Removed in `<version>`.

## Upgrade steps

1. <Update the package: exact command.>
2. <Run the codemod, then fix what it reports.>
3. <Run the tests.>

## Related

- [Changelog](<link>)

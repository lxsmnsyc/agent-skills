---
title: How the <subsystem> works
type: internals
covers: [<path/to/subsystem>]
---

<What the subsystem does, in one or two sentences. Written for contributors and advanced users.>

This page describes the current implementation. It is not public API and may change in any release. For how to use <the feature>, see [<concept page>](<link>).

## Overview

<One diagram of the whole mechanism: inputs, stages, outputs. One short paragraph that walks through it.>

## <Stage 1, named by what it does>

<What it takes, what it produces, and where it lives: `<path/to/file>`, `<functionName>`.>

```ts
// The intermediate result for a small input, when it helps.
```

## <Stage 2>

## Data flow

<What moves between stages and in what form. What runs at build time, on the server and in the client.>

## Design decisions

- **<Decision>.** <Why, and the alternative that lost.> [<decision record>](<link>)

## Where to start in the code

- Entry: `<path>`, `<function>`.
- Tests to read first: `<path>`.
- Debugging: `<flag or command that prints intermediate output>`.

## Related

- [<Concept page for the same behavior>](<link>)
- [<Neighboring internals page>](<link>)

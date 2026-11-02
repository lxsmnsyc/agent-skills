# Principles for JS and TS

What is specific to `.js` and `.ts` code, in every major engine (V8, SpiderMonkey and Safari's JSC). Apply `principles.md` first. This file names how those principles look here and adds the rules that come from the engines, the DOM and the bundle. Cite ids the same way.

## The general principles here

- **W1, W2**: `includes`, `indexOf`, `find` or `some` inside a loop is the linear search. Use a `Set` or `Map` built once.
- **W4**: `new Intl.NumberFormat`, `new Intl.DateTimeFormat`, `new Intl.Collator` and `new RegExp(source)` are costly to build. Keep one instance. `toLocaleString` and `localeCompare` look up locale data on every call. For repeated calls, use a stored `Intl` object's `format` or `compare`.
- **A1**: `JSON.parse(JSON.stringify(x))` and `structuredClone` copy everything.
- **A2**: `acc = {...acc, [k]: v}` or `arr = [...arr, x]` inside a loop or `reduce` copies on every step. Mutate a local object or array, then return it.
- **L1, L2, L3**: `Float64Array`, `Int32Array` and the other typed arrays are the flat numeric arrays. An array of objects is an array of references to objects spread over the heap, so typed-array columns gain more over objects here than structures of arrays gain in C.
- **L4**: indices into typed arrays help large node graphs and data sent to Workers. For ordinary app data, object references are fine.
- **A4**: `fs.createReadStream`, `readline` and `Response.body` stream. A `WeakMap` ties an entry's lifetime to an object key (A5).
- **I1**: `for (...) await fetch(...)` waits for each in turn. Use `Promise.all`, with a concurrency limit when there are many.
- **I3**: `readFileSync`, `pbkdf2Sync` and other sync calls in a request handler block the event loop.

## Runtime

- **J1. One loop over a chain.** On a hot path, one `for` or `for...of` loop replaces `.filter().map().reduce()`, which allocates an array per step and calls a closure per item.
- **J2. No bit packing past 31 bits.** Bitwise operators work on 32-bit signed integers, and engines keep small integers unboxed only up to about 31 bits. Larger values become heap numbers. Pack spare bits only inside typed-array storage, and measure it.

## Shapes and types

- **E1. Same shape, same order.** Create objects of one kind with all their fields at once, in the same order (one literal or one constructor). Adding fields later gives the engine new shapes and slows every access site.
- **E2. No `delete` on hot objects.** It moves the object to a slow dictionary mode. Set the field to `undefined`, or use a `Map` when keys come and go.
- **E3. `Map` for dynamic keys.** A plain object used as a dictionary with many changing keys is slower than a `Map`, and inherits keys like `constructor` from its prototype.
- **E4. One type per field and per array.** Do not mix numbers and strings in one field or one array. Keep arrays dense: build them with literals or `push`, never leave holes, never write far past the end.
- **E5. Monomorphic hot functions.** A function on a hot path should see the same argument shapes and types every call. Split it when two different kinds of input pass through it.

## DOM and UI

- **D1. Read layout, then write.** Interleaving reads (`offsetHeight`, `getBoundingClientRect`) with style writes forces a layout per read. Do all reads, then all writes, and put visual writes in `requestAnimationFrame`.
- **D2. Render only what is visible or changed.** Long lists render the visible window. Lists keep stable keys so items are moved, not rebuilt.
- **D3. Derive instead of syncing.** A value computed from state is derived (a memo, a computed signal, a plain expression), not copied into more state by an effect. Copying renders twice and can drift. A memo is a cache that the framework invalidates, so it does not fall under C2.
- **D4. Insert in bulk.** Many new nodes go in through one `DocumentFragment`, `append(...nodes)` or `replaceChildren`. Set text with `textContent`, not `innerHTML`.
- **D5. Rate-limit frequent events.** Throttle or debounce `scroll`, `resize`, `input` and `pointermove` handlers. Mark scroll and touch listeners `{ passive: true }`.
- **D6. Animate with `transform` and `opacity`.** They skip layout and paint. Animating `top`, `left`, `width` or `height` lays out every frame.

## Size

- **S1. Native APIs over dependencies** when every target has them: `fetch`, `URL`, `URLSearchParams`, `structuredClone`, `Intl`, `crypto.randomUUID`, `AbortController`, `Array.prototype.at`. Check the targets first for newer ones (`Object.groupBy`, `Array.prototype.toSorted`).
- **S2. Import only what is used.** Named imports from the package's ESM entry, per-function imports for libraries that offer them (`lodash-es/debounce`, not `lodash`). Avoid barrel files that pull in modules with side effects.
- **S3. Mark libraries side-effect free.** `"sideEffects": false` (or the list of files that have side effects) in `package.json`, so bundlers can drop unused modules.
- **S4. Compile to the real targets.** Set `target` in `tsconfig.json` and the bundler to what users run (ES2022 or later for current browsers and Node 18+). Older targets add helpers and rewrite `async`, classes, `?.` and `#private` fields into longer code.
- **S5. No runtime cost for types.** Prefer string-literal unions or an `as const` object over `enum`, which emits an object and does not tree-shake. Use `import type` for imports that are only types.
- **S6. Strip development code.** Guard warnings and checks with `process.env.NODE_ENV !== "production"` or `import.meta.env.DEV`, so the minifier removes them from production builds.
- **S7. Split what is rare.** Routes, dialogs, editors and charts most users never open load through dynamic `import()`.
- **S8. One copy of each dependency.** Check the lockfile for duplicate versions of the same package (`pnpm why <pkg>`), and dedupe them.

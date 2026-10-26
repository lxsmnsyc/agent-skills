---
name: ts-style
description: Style rules for this user's TypeScript code, and for `.js` files too. Write for-of loops instead of callback-taking Array methods (map, filter, forEach, reduce, some, every, find, flatMap and the like). Use this skill whenever writing, editing or reviewing TypeScript, `.ts`, `.tsx`, `.js` or `.jsx` code, unless the repo's own style rules say otherwise.
---

# TypeScript style

Rules that apply to every repo of this user with `.ts`, `.tsx`, `.js` or `.jsx` code. A repo's own conventions (a CLAUDE.md, a lint config, the existing code) win when they disagree.

## Prefer for-of over Array methods

Iterate with `for...of` instead of an Array method that takes a callback. A callback is a closure, which allocates and captures state, and the methods are generally slower than a plain loop. That matters in render loops, game ticks, parsers, compilers and anything else that runs often, and the habit costs nothing elsewhere.

### What becomes a loop

`map`, `filter`, `forEach`, `reduce`, `reduceRight`, `some`, `every`, `find`, `findIndex`, `findLast`, `findLastIndex`, `flatMap`, and `Array.from(items, mapper)`. The same goes for `forEach` on a `Map` or a `Set`.

- A chain becomes one loop: `filter` then `map` is one pass with a `continue`.
- `some`, `every` and `find` keep their short circuit with `return` or `break`.
- A callback that reads the index iterates `entries()`, or uses a counted `for`.
- `Promise.all(items.map(async ...))` becomes a loop that pushes the promises, then `Promise.all` over them.
- `new Map(items.map(...))` becomes an empty `Map` filled in the loop.

```ts
// Before
const names = party.filter((unit) => unit.alive).map((unit) => unit.name);
const fainted = party.some((unit) => unit.hp === 0);

// After
const names: string[] = [];
let fainted = false;

for (const unit of party) {
  if (unit.hp === 0) {
    fainted = true;
  }
  if (unit.alive) {
    names.push(unit.name);
  }
}
```

### What stays

- Methods with no per-item callback: `sort`, `join`, `slice`, `includes`, `indexOf`, `concat`, `push`, `at`.
- A `sort` comparator, which no loop replaces.
- A framework's list rendering idiom: `<For each={...}>` in Solid, `items.map(...)` inside React JSX.
- Anything that only shares a name with an Array method: a promise's `.then(...)`, a string's `.includes(...)`.

### Traps

- **Reactivity.** In Solid and other signal-based code, a loop hoisted out of a JSX expression, a memo or an effect stops being tracked. Keep the loop inside the same tracked scope, as the body of the accessor or memo it came from.
- **Types.** Give the accumulator its type (`const names: string[] = []`), so callers still see what the method inferred.
- **Fresh results.** Where the method returned a fresh array the caller may keep, the loop builds a fresh array too, never a shared one.

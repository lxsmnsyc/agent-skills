---
name: ts-style
description: Style rules for this user's TypeScript code, and for `.js` files too. Write for-of loops instead of callback-taking Array methods (map, filter, forEach, reduce, some, every, find, flatMap and the like), write named functions as function declarations with action names (never `<noun>Of`), comment the steps inside a function rather than the function itself, and run the repo's linter and formatter after editing. Use this skill whenever writing, editing or reviewing TypeScript, `.ts`, `.tsx`, `.js` or `.jsx` code, unless the repo's own style rules say otherwise.
---

# TypeScript style

Rules that apply to every repo of this user with `.ts`, `.tsx`, `.js` or `.jsx` code. A repo's own conventions (a CLAUDE.md, a lint config, the existing code) win when they disagree.

## Prefer for-of over Array methods

Iterate with `for...of` instead of an Array method that takes a callback. This is the user's style: their code has far more for-of loops than callback methods. A chain of methods walks the array once per method, and a loop does the work in one pass.

Do not claim the loop is faster. A single `map` over a small array is often faster than a loop with `push`. When speed matters, measure it with the perf-pass skill.

Test files are exempt. `expect(units.map((unit) => unit.id)).toEqual(...)` is fine in a test.

### What becomes a loop

`map`, `filter`, `forEach`, `reduce`, `reduceRight`, `some`, `every`, `find`, `findIndex`, `findLast`, `findLastIndex`, `flatMap`, and `Array.from(items, mapper)`. The same goes for `forEach` on a `Map` or a `Set`.

- A chain becomes one loop: `filter` then `map` is one pass with a `continue`.
- `some`, `every` and `find` keep their short circuit with `return` or `break`.
- A callback that reads the index iterates `entries()`, or uses a counted `for`.
- `Promise.all(items.map(async ...))` becomes a loop that pushes the promises, then `Promise.all` over them.
- `new Map(items.map(...))` becomes an empty `Map` filled in the loop.
- When the linter's `prefer-find` flags `filter(...)[0]`, write a loop with `break`, not `find`.

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

## Function declarations

Write a named function as a `function` declaration, not as a `const` holding an arrow function.

```ts
// Before
export const heal = (unit: Unit, amount: number): void => { ... };

// After
export function heal(unit: Unit, amount: number): void { ... }
```

Inline callbacks, `sort` comparators, JSX event handlers and functions passed straight to another call stay arrows.

## Comments

Comment the steps inside a function, not the function. Split a body of more than a few lines into sections, one blank line apart. Open each section with a comment that says what the step does, and why when that is not obvious. A reader should be able to follow the function by reading only its section comments.

```ts
function applyDamage(battle: Battle, hit: Hit): void {
  // Shields absorb the hit first, and only the rest reaches the hp.
  const absorbed = Math.min(hit.target.shield, hit.amount);
  hit.target.shield -= absorbed;
  const rest = hit.amount - absorbed;

  // A unit at 0 hp faints at once, before the next hit in the same turn.
  hit.target.hp = Math.max(0, hit.target.hp - rest);
  if (hit.target.hp === 0) {
    faint(battle, hit.target);
  }

  // The log keeps the absorbed part, so the replay can draw the shield breaking.
  battle.log.push({ kind: 'damage', target: hit.target.id, absorbed, rest });
}
```

- A function of one step needs no section comment.
- A doc block goes on exported functions and types only. It says what the thing is for, not what its name already says.
- The wording follows the plain-writing skill: short, full sentences, no history.

## Naming

Do not name functions `<noun>Of` (`keyOf`, `fileOf`, `ownerOf`). Name the action. Use `getKey(unit)` for a plain read, or a verb that says the work, such as `findFile`, `readFile` or `createKey`.

## Lint and format

Most repos of this user extend `@lxsmnsyc/oxlint-config` and format with oxfmt. That config enforces about 150 rules, such as braces on every `if`, `prefer-const` and explicit return types. This skill does not repeat them. After editing, run the repo's lint script (often `pnpm lint`, which runs `oxlint --type-aware`) and its formatter, and fix what they report.

## Before finishing

Search the lines your change added for callback Array methods, for example with `git diff -U0 | grep -E '^\+.*\.(map|filter|forEach|reduce|some|every|find|findIndex|flatMap)\('`. Turn each hit outside tests and the "What stays" list into a loop. Search the same lines for `function \w+Of(` and rename each hit.

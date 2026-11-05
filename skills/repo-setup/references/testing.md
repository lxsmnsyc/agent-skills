# Test depth: properties, models and oracles

Example tests check the inputs someone thought of. Generated tests check inputs nobody thought of, and they pay off only where a module has a rule that holds for every input. Decide per module, from what the module does. Most modules need none of the three.

## Which kind fits

| The module | Test | What the test checks |
| --- | --- | --- |
| Pairs of inverse functions: parse and print, encode and decode, serialize and deserialize | property | `decode(encode(x))` equals `x` for any generated `x` |
| Pure functions with a law: sort, normalize, merge, diff, format | property | the law: output is sorted and a permutation of the input, `normalize(normalize(x))` equals `normalize(x)`, `merge` is associative, `apply(a, diff(a, b))` equals `b` |
| Code that must not throw on valid input: parsers, validators, compilers | property | any generated valid input returns without throwing |
| Objects whose behavior depends on the order of calls: caches, stores, queues, pools, reactive graphs, undo stacks, state machines | model | after any generated sequence of calls, the object agrees with a small model (a `Map`, an array, a transition table) |
| Code with a trusted reference: an older version, a native API (`JSON.parse`, `structuredClone`, `Intl`), a slow but simple version, another library | oracle | the module and the reference give the same output for any generated input |

Skip generated tests for thin wrappers, I/O glue, UI layout, config, and code whose behavior is a call to another library. Example tests are enough there.

An oracle is the right test for a rewrite, such as a perf-pass candidate or a fix that changes an algorithm. Keep the old implementation as the reference until the new one ships.

## Setup

Use fast-check. Install it only in the packages that need it:

```bash
pnpm add -D fast-check@latest @fast-check/vitest@latest
```

`@fast-check/vitest` adds `test.prop`. The tests sit in the package's normal vitest suite, so `pnpm test` and the check workflow run them with no other change.

```ts
import { fc, test } from '@fast-check/vitest';
import { expect } from 'vitest';
import { parse, stringify } from '../src';

test.prop([fc.jsonValue()])('stringify round-trips through parse', (value) => {
  expect(parse(stringify(value))).toEqual(value);
});
```

A model test lists one command class per public operation. Each command checks the real object against the model, then updates the model:

```ts
import fc from 'fast-check';
import { test } from 'vitest';
import { LRU } from '../src';

class SetCommand implements fc.Command<Map<string, number>, LRU<string, number>> {
  constructor(readonly key: string, readonly value: number) {}
  check() {
    return true;
  }
  run(model: Map<string, number>, real: LRU<string, number>) {
    real.set(this.key, this.value);
    model.delete(this.key);
    model.set(this.key, this.value);
    if (model.size > real.capacity) {
      model.delete(model.keys().next().value!);
    }
  }
  toString() {
    return `set(${this.key}, ${this.value})`;
  }
}

test('LRU agrees with a Map model', () => {
  const key = fc.constantFrom('a', 'b', 'c', 'd');
  const commands = [fc.tuple(key, fc.integer()).map(([k, v]) => new SetCommand(k, v))];
  fc.assert(
    fc.property(fc.commands(commands), (cmds) => {
      fc.modelRun(() => ({ model: new Map(), real: new LRU(3) }), cmds);
    }),
  );
});
```

Use `fc.asyncModelRun` for async objects. Add a `GetCommand` and the other operations the same way.

## Rules

- Keep the default number of runs (100) so the check workflow stays fast. A longer run goes behind an environment variable, for example `numRuns: process.env.FC_RUNS ? Number(process.env.FC_RUNS) : undefined`.
- A failure prints a seed and a shrunk counterexample. Fix the bug, then add the counterexample as a plain example test, so it is checked on every run whatever the seed.
- Generators make valid inputs only. When a module rejects some inputs, test the rejection with its own property.
- Report the decision per module to the user, with the kind and the reason, including the modules you skipped.

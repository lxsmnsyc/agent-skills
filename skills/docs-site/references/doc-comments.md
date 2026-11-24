# Doc comments for generated reference

Generated reference is only as good as the comments it reads. Write doc comments on every export so the generator produces the reference entry from SKILL.md without hand-written pages.

## Mapping to the reference entry

For TypeScript, with TypeDoc or a similar tool reading TSDoc:

| Reference entry part | Source |
|---|---|
| Signature | The type signature itself. Never repeat types in the comment. |
| One-line description | The first sentence of the comment. |
| Parameters | `@param name` with what the value does, its default and any rule it must follow. |
| Returns | `@returns` with what the value holds. |
| Throws | `@throws {ErrorName}` with when it happens. |
| Example | `@example` with a fenced code block that runs as written. |
| Notes | Remarks after the first paragraph, or `@remarks`. Only facts a caller could get wrong. |
| Since | `@since 1.4.0` |
| Deprecated | `@deprecated Use {@link newName} instead. Removed in 3.0.0.` |
| See also | `@see {@link conceptOrGuide}` or a link to the docs page. |

````ts
/**
 * Creates a store that saves its state after every `set`.
 *
 * Values that `JSON.stringify` cannot encode are dropped when saved.
 *
 * @param initial The state used when nothing is saved under `key`.
 * @param options.key The storage key.
 * @param options.storage Where to save. Defaults to `localStorage`.
 * @returns A store with `get`, `set` and `subscribe`.
 * @throws {TypeError} When `storage` is missing outside a browser.
 * @example
 * ```ts
 * const cart = createPersistedStore([], { key: 'cart' });
 * cart.set(['apple']);
 * ```
 * @since 1.4.0
 * @see https://example.dev/concepts/persistence
 */
export function createPersistedStore<T>(initial: T, options: PersistOptions): Store<T> {}
````

## Rules

- **Every public export** has a doc comment. Internal exports are marked `@internal` and left out of the reference.
- **First sentence stands alone.** Generators show it in lists and search results.
- **Say what, not how.** The comment says what the caller gets and what they could get wrong. plain-writing's doc block rules apply.
- **Examples run.** Doc comment examples are extracted and type-checked or run in CI, like page examples.
- **Links by name.** Use `{@link name}` for other exports, so the generator checks them and renames update them.
- **Warnings as errors.** Turn on the generator's checks for missing comments and broken links (TypeDoc: `validation.notDocumented`, `validation.invalidLink`, and `treatWarningsAsErrors` in the docs build).

`docs_check.py --exports` also reports exports declared in the entry file with no doc comment above them.

## Other languages and surfaces

- **HTTP APIs**: the OpenAPI schema is the source. Each operation gets a `summary` (the one-line description), a `description`, parameter and response descriptions, error responses and an `example`.
- **CLIs**: the help text is the source. Each command and flag has a one-line description, and the reference page is generated from `--help` output or the parser's definitions.
- **Config files**: a JSON Schema with `description`, `default` and `examples` for each key generates the configuration reference and gives editors completion.
- **Rust, Go, Python**: rustdoc, godoc and docstrings follow the same mapping.

set -eu
git init -q -b main
git config user.name "Repo Owner"; git config user.email owner@example.com
mkdir -p src website/docs/reference website/docs/guides
printf '{"name":"tiny-store","version":"1.3.0","type":"module"}\n' > package.json
cat > src/store.js <<'J'
// persist: { key: string, storage?: Storage } saves the state under `key`
// after each set() and loads it in createStore. storage defaults to
// localStorage. Values that JSON.stringify cannot encode are dropped.
export function createStore(initial, options = {}) {
  const { persist } = options;
  const storage = persist ? persist.storage ?? globalThis.localStorage : null;
  let state = initial;
  if (persist) {
    const saved = storage.getItem(persist.key);
    if (saved !== null) state = JSON.parse(saved);
  }
  const listeners = new Set();
  return {
    get: () => state,
    set(next) {
      state = next;
      if (persist) storage.setItem(persist.key, JSON.stringify(state));
      for (const listener of listeners) listener(state);
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}
J
cat > website/docs/index.md <<'M'
---
title: tiny-store
type: index
---

A store with get, set and subscribe.

- [Getting started](getting-started.md)
- [Share state between components](guides/share-state.md)
- [API reference](reference/api.md)
M
cat > website/docs/getting-started.md <<'M'
---
title: Getting started
type: tutorial
---

Create a store and read it in two minutes.

## Before you start

- Node 20 or a browser.

## Create a store

```js
import { createStore } from "tiny-store";
const counter = createStore(0);
counter.set(1);
```

## Next steps

- [API reference](reference/api.md)
M
cat > website/docs/guides/share-state.md <<'M'
---
title: Share state between components
type: guide
---

Use one store from several components.

## Steps

1. Create the store in its own module and export it.
2. Call `subscribe` in each component.

## Related

- [API reference](../reference/api.md)
M
cat > website/docs/reference/api.md <<'M'
---
title: API
type: reference
---

Every export of tiny-store.

## `createStore`

```ts
createStore<T>(initial: T): Store<T>
```

Creates a store holding `initial`.

**Returns** `Store<T>`: an object with `get`, `set` and `subscribe`.
M
printf "setup.sh\n" > .gitignore
git add -A && git commit -qm "tiny-store docs"

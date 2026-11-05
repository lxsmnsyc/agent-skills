# Implicit state machines

An implicit state machine is one state spread over several values, with no list of the transitions it allows. Two shapes are common:

- **Flags.** `isLoading`, `isError` and `data` each hold part of one state. Nothing stops `isLoading && isError`, so every reader has to guess what that combination means.
- **Status strings.** `this.status = 'running'` is set from many methods, each with its own guard (`if (this.status !== 'done')`). The allowed transitions exist only as those guards.

Not every hit is a machine. Flags that change on their own (`isOpen` and `isDisabled`, or Vite's `isSsrBuild` and `isServe`) are separate state. A status that a `switch` reads in one place, such as a tokenizer, already lists its transitions.

## Find them

```bash
python3 <skill>/scripts/scan_states.py <repo>          # --json for the raw list
```

The scan lists candidates with `file:line` and a `stored` hint, and it lists the database tooling the repo uses. Read each candidate and keep the ones where some combination of values is impossible or where transitions are checked in more than one place.

## Check whether the state is stored

A state is stored when its value leaves the process. That covers a database column or document field, a migration or ORM schema, `localStorage` or IndexedDB, and a file. It also covers a message on the wire and an exported type of a published package. The scan's `stored: yes` means a schema or migration names it, and `stored: maybe` means its file writes to storage. Confirm by reading.

- **Not stored**: fix it.
- **Stored, and no database holds data for it yet**: fix it, and change the schema in the same pull request. When the repo has database tooling, ask the user first whether a deployed or shared database holds data for the project. A local database the user can reset counts as none.
- **Stored, with existing data**: do not change it in place. Propose the new representation and a migration that maps every old combination of values to a new state. Query the data for combinations the code calls impossible, because old bugs leave them behind. Ship the change as expand, migrate, contract (pr-author's `references/non-blocking.md`), and wait for the user to approve it.
- **An exported type or field of a published package**: changing it breaks callers. Keep the old fields as values read from the new state, or ask the maintainer for a `major` changeset (changesets skill).

## Fix

Replace the scattered values with one discriminated union and one function that moves between states.

```ts
type Load<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'done'; data: T }
  | { status: 'failed'; error: unknown };

type LoadEvent<T> =
  | { type: 'start' }
  | { type: 'resolve'; data: T }
  | { type: 'reject'; error: unknown };

function transition<T>(state: Load<T>, event: LoadEvent<T>): Load<T> {
  switch (state.status) {
    case 'idle':
    case 'done':
    case 'failed':
      return event.type === 'start' ? { status: 'loading' } : state;
    case 'loading':
      if (event.type === 'resolve') {
        return { status: 'done', data: event.data };
      }
      if (event.type === 'reject') {
        return { status: 'failed', error: event.error };
      }
      return state;
  }
}
```

- Data lives only on the states where it is valid, so `data` cannot be read while loading.
- Each event the current state does not accept is either ignored on purpose or throws. Pick one per machine and keep it.
- Keep the public API where you can: `isLoading` becomes a getter that reads `state.status === 'loading'`.
- Write no state machine library into a repo that has none. A union and a function are enough.
- Test the fix with a model test (`references/testing.md`). The model is a table of the allowed transitions, written in the test apart from the code, and the commands are the events.

Each fix is its own pull request through pr-author, not part of the setup pull request.

# Principles

Practices known to be faster or smaller in any language. A change that only applies one of them needs no side-by-side proof. Cite the id in the option ("W2: one grouping pass"), and the final measurement in step 7 covers it. Each principle holds under the conditions it states. Outside them, it is a candidate to measure.

A principle settles the direction of a change, not its size. Do not claim a number for it until the final run shows one.

Language files add what is specific to a runtime, with their own ids:

- `.js`, `.ts`, `.jsx`, `.tsx`: `principles-js-ts.md`

## Work

- **W1. Look up by key, not by search.** A linear search inside a loop is O(n·m). Build a hash set, a hash map or an index once, and look up in O(1).
- **W2. Group once.** One pass that fills a map of groups replaces a filter per key.
- **W3. Compute only what the output reads.** Rank or filter on the cheap field first, then compute the expensive fields only for the rows that are returned (the top `limit`, the visible rows).
- **W4. Hoist invariant work out of loops.** Values, lookups, compiled patterns and formatters that do not change between iterations are built once, before the loop.
- **W5. Keep comparators cheap.** A sort calls its comparator about n·log n times. Precompute sort keys, and compare numbers or stored keys, not derived values.
- **W6. Exit early.** Stop a loop once the answer is known, and check the cheapest condition first.
- **W7. No exceptions for control flow.** Throwing captures a stack trace and unwinds frames. On a hot path, return a value that says it failed instead.

## Data layout

- **L1. Arrays for dense integer keys.** When the keys are integers you assign from 0 to n, index an array instead of a hash map: no hashing, contiguous memory. Keys that are strings, sparse, or come from outside stay in a map.
- **L2. Contiguous storage for bulk numbers.** Coordinates, pixels, samples and matrices go in flat numeric arrays, not in collections of boxed values or of separate objects.
- **L3. Structure of arrays for field-wise loops.** When a hot loop reads a few fields across many items, store each field as its own array. Keep an array of structures when code reads most fields of one item together, picks items at random, or adds and removes items often.
- **L4. Indices into an arena for owned graphs.** Many small nodes owned by one structure (trees, graphs, ASTs, entities) live in one array and refer to each other by index. Indices are smaller than pointers, survive moves and serialization, and keep nodes close in memory. Track reuse of freed slots with a generation number, so a stale index cannot read a new node.

## Data and allocation

- **A1. Do not clone to read.** Read the data in place. Copy only what you mutate, and only when others can see it.
- **A2. No copy per step.** Building a result by copying the whole accumulator on every step (immutable append, string rebuilt from scratch) is O(n²). Append to one buffer, then hand it out.
- **A3. Reuse buffers on hot paths.** Allocate scratch buffers once and clear them between uses, instead of allocating per call or per item.
- **A4. Stream what is large.** Read big files and responses in chunks instead of loading them whole.
- **A5. Bound what is kept.** A cache or a list that only grows is a leak. Give it a size limit, or tie each entry's lifetime to its owner.

## I/O and concurrency

- **I1. Do not wait on independent work in sequence.** Start independent requests together, with a concurrency limit when there are many.
- **I2. Batch round trips.** One query for many keys instead of one per key (no N+1), bulk inserts, one request for a list.
- **I3. Do not block the serving thread.** Long synchronous work in a request handler or an event loop stalls every other request. Move it off that thread or make it asynchronous. Startup code and one-shot scripts may stay synchronous.

## Caching

- **C1. Redesign before caching.** A cache in front of slow code hides the cost instead of removing it. First look for a structure that does not need the cache (W1 to W3, L1 to L4). Building an expensive object once and reusing it (W4) is not a cache in this sense.
- **C2. A new cache needs a measured reason.** Add one only when the work cannot be designed away (network, disk, compiling, parsing input that repeats) and a side-by-side run shows the gain. State its invalidation rule and its size limit (A5).
- **C3. Remove a cache by measurement.** An existing cache goes when the redesign is measured to match its speed without it. A cache whose only job is to hide a slow structure is a sign to redesign, not a cache to keep.

## When a principle is not enough

Measure side by side (step 6) when a change:

- trades one cost for another: caches (C2), workers and concurrency (overhead, ordering), laziness (moves the cost to first use), code splitting (adds a request)
- packs extra data into the spare bits of an index or a pointer. It is a known pattern for tagged handles and generation numbers in systems languages, but it narrows the index range and costs a mask on every use.
- relies on runtime or compiler behavior not listed here or in a language file
- replaces a dependency with own code that does not behave the same
- runs on small, fixed inputs, where constant factors decide and the asymptotic win may not show

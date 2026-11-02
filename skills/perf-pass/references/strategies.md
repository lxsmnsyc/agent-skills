# Strategies

Kinds of fix to draw candidate options from. Option A is always a structural rewrite (first row); pick the others from different rows, so the options differ.

## Runtime

| Kind | Examples | Usually costs |
| --- | --- | --- |
| Structure | Rewrite from the contract: one pass instead of several, group once instead of filtering per key, compute only the output callers read, drop intermediate copies and layers | A rewrite to review; usually less code |
| Algorithm | A map instead of a linear search; sort once instead of per query; an index; a better data structure | Little; sometimes memory |
| Less work | Skip work whose result is unused; early exit; avoid recomputing unchanged inputs; narrower updates in UI | Small; needs a clear invalidation rule |
| Less allocation | Reuse buffers and objects; loops instead of callback chains; avoid temporary arrays, strings and closures in hot paths | Some readability |
| Batching | One query for many keys; one DOM write per frame; group events; bulk inserts | A queue and a flush point |
| Caching | Only after a redesign is ruled out (principles C1 to C3): cache network, disk, compile or parse results for input that repeats | Memory, invalidation bugs |
| Laziness | Compute on first use; load modules on demand; defer work until idle | A first-use cost moved elsewhere |
| Concurrency | Workers for CPU-heavy work; parallel I/O | Complexity, ordering bugs |
| Platform | Typed arrays, native APIs, a faster runtime flag, a compiled path | Portability |
| Dependency | Replace a slow dependency, or drop it for a few lines of code | Maintenance of the replacement |

## Size (web apps and published libraries)

| Kind | Examples | Usually costs |
| --- | --- | --- |
| Drop or swap dependencies | A smaller library, native APIs (`Intl`, `fetch`, `URL`, `structuredClone`), a few lines of own code | Maintenance |
| Code splitting | Dynamic `import()` for routes, dialogs, editors, charts; load on interaction or idle | A request and a delay on first use |
| Tree shaking | Named imports instead of namespaces; `sideEffects: false`; ESM builds of dependencies; avoid barrel files that pull everything in | Little |
| Dead code | Remove unused exports, feature flags that are always on, development-only code in production builds | Little |
| Targets and polyfills | Raise the build target to what users run; drop polyfills for features every target has | Older browsers lose support |
| Assets | Compress images (AVIF, WebP), subset fonts, inline small SVGs, lazy-load below the fold | Build steps |
| Build settings | Minifier options, property mangling for private fields, dropping `console` calls, brotli on the server | Debuggability |
| Data | Ship generated data compactly, fetch large tables on demand instead of bundling them | A request |

## Picking among them

- Start from the profile. The kind of fix follows the kind of cost: many small allocations point to allocation and loops, one slow call points to an algorithm or a cache, a large chunk points to splitting or a dependency.
- Prefer kinds that remove work over kinds that hide it. A simpler structure beats a faster version of the same steps, and an algorithm change beats a cache in front of the slow algorithm.
- Structural fixes usually shrink size too. Reach for size-only fixes (splitting, build settings) when the size goal is still missed after the structure is simple.
- Mind the other axis: caching and concurrency cost memory; splitting costs a request; a faster dependency may be bigger.

# Measuring

Tools for the baseline, the profile and the comparison, by stack. Use what the repo already has before adding anything.

## Runtime

| Stack | Benchmark | Profile |
| --- | --- | --- |
| Node and browsers (`.ts`, `.js`) | `vitest bench`, `tinybench`, `mitata`, or a script timed by `bench.py` | `node --cpu-prof` (open the `.cpuprofile` in Chrome DevTools), `node --heap-prof`, `--trace-gc`; Chrome DevTools Performance panel for pages |
| Browser rendering | A page that runs the scenario and logs a number; Playwright to drive it; `performance.now()` marks | DevTools Performance (frame time, long tasks, layout), the Memory panel for leaks |
| Rust | `cargo bench` with criterion | `cargo flamegraph`, `perf`, `samply` |
| Go | `go test -bench . -benchmem` | `go test -cpuprofile`, `pprof` |
| Python | `pytest-benchmark`, `timeit`, `hyperfine` for scripts | `py-spy`, `cProfile` with `snakeviz` |
| Any command | `hyperfine`, or `bench.py` to compare checkouts | the stack's own profiler |

Reading a number from a benchmark's output: pass `--metric 'ops/sec: ([\d.]+)' --higher-is-better` to `bench.py`.

## Size

| Build tool | Size report | What is in it |
| --- | --- | --- |
| Vite or Rollup | `vite build`, then `size_diff.py` on `dist/` | `rollup-plugin-visualizer` (treemap), `vite-bundle-visualizer` |
| esbuild | `--metafile=meta.json` | `esbuild --analyze`, or the esbuild bundle analyzer page |
| webpack | `--json > stats.json` | `webpack-bundle-analyzer` |
| Any built output | `size_diff.py base head --glob 'dist/**/*.js'` | `source-map-explorer` on the source maps |
| Published package | `npm pack --dry-run` | `size-limit` with its `--why` flag |

Report gzip or brotli sizes for files the browser downloads; raw sizes mislead because minified code compresses very differently.

## Getting numbers that hold

- **Warm up.** The first runs include JIT compilation, cold caches and disk reads. `bench.py --warmup 2` drops them.
- **Repeat.** At least 10 runs for runtime. Report the median and the spread, never one run.
- **Interleave.** Compare checkouts in alternating order (`bench.py` does this), so slow drift in machine load does not favor one side.
- **Quiet machine.** Stop other heavy work, including other agents' builds and tests. Do not run two benchmarks at the same time.
- **Same input.** Fixed seeds, fixed data files, the same build mode (production, minified) on every side.
- **Production builds.** Development builds have extra checks and no minification; their numbers do not transfer.

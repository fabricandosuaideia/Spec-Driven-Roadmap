# Benchmark results

Appended by `scripts/run-benchmark.py score --record`. Never edit by hand:
a scoreboard someone can rewrite measures nothing.

`captured` is out of the seven planted ambiguities in
[`expected.md`](expected.md). A drop is a regression.

| date | version | run | captured | linter | missing |
|---|---|---|---|---|---|
| 2026-08-09 | 3.13.0 | pauta | 7/7 | 14 passed, 0 failed, 0 warnings, 0 skipped | — |
| 2026-08-09 | 3.10.0 | run-a | 6/7 | 12 passed, 1 failed, 1 warnings, 0 skipped | 4 votes after edit |
| 2026-08-09 | 3.18.0 | v3180-a | 6/7 | 80 passed, 0 failed, 1 warnings, 4 skipped | 7 retention / deletion |
| 2026-08-09 | 3.18.0 | v3180-a | 7/7 | 80 passed, 0 failed, 1 warnings, 4 skipped | — |

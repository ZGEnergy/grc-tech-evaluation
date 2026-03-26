---
test_id: D-1
tool: gridcal
dimension: accessibility
network: TINY
protocol_version: "v11"
skill_version: v2
test_hash: "c3eaae4c"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.485
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T12:00:00Z"
---

# D-1: Install-to-First-Solve

## Result: INFORMATIONAL

## Finding

GridCal (veragridengine v5.6.28) installs cleanly via `uv sync` and achieves first
DC power flow solve in 1.485 seconds wall-clock (measured via `time.perf_counter()`).
Three minor friction points were encountered, none blocking.

## Evidence

### Measured Timing Breakdown

Timing measured in devcontainer (Ubuntu 24.04, Python 3.12) using `time.perf_counter()`:

| Phase | Wall-clock (s) |
|-------|---------------|
| Import (`import VeraGridEngine`) | 1.291 |
| Load network (`open_file('case39.m')`) | 0.104 |
| Solve (DC power flow) | 0.089 |
| **Total (import + load + solve)** | **1.485** |

Warm-run timings (import cached): 0.118s (run 2), 0.019s (run 3).

### Dependency Installation

```
$ uv sync
Resolved 65 packages in 0.51ms
Checked 62 packages in 0.56ms
```

All packages install from pre-built wheels. No compilation step required. The
dependency tree includes numpy, scipy, PuLP, OR-Tools, chardet, and several I/O
format libraries. Total: 62 audited packages.

### Friction Points Encountered

1. **Rebrand confusion (medium):** The PyPI package is `veragridengine`, the import
   is `VeraGridEngine`, and much documentation still references `GridCal`/`GridCalEngine`.
   A user searching for "GridCal" on PyPI finds the old (deprecated) package. The README
   explains the rename but this adds a discovery step. [tool-specific]

2. **urllib3 warning on every import (low):** `RequestsDependencyWarning: urllib3 (2.6.3)
   or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!`
   emitted on every import. Cosmetic only; does not affect functionality. [tool-specific]

3. **Asymmetric API naming (low):** The top-level `vge` namespace exposes `power_flow()`
   but OPF requires `linear_opf()` or `simple_opf()` — names that are not symmetric
   with the PF API. The `OptimalPowerFlowOptions` constructor uses `solver=` while
   `PowerFlowOptions` uses `solver_type=`. Discovered via `dir(vge)` introspection,
   not documentation. [tool-specific]

### Positive Notes

- `uv sync` installs cleanly with no build-from-source steps
- `vge.open_file()` reads MATPOWER `.m` files natively with no additional configuration
- First-solve latency (1.485s including import) is competitive for a Python tool
- The core API pattern (`open_file()` / `power_flow()`) is clean and intuitive

## Implications

Install-to-first-solve is straightforward for a Python-literate user. The main friction
is the rebrand naming inconsistency (package vs import vs documentation) and the
asymmetric API naming for PF vs OPF. Neither is blocking. The 1.485s total time is
dominated by import overhead (1.291s / 87%), with the actual solve taking only 0.089s.

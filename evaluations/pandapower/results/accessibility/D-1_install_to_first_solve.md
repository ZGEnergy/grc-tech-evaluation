---
test_id: D-1
tool: pandapower
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: c3eaae4c
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: 5.35
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# D-1: Install to First Solve

## Result: INFORMATIONAL

## Finding

pandapower installs and reaches first solve in approximately 5.3 seconds total wall-clock
time (measured via `time.perf_counter()`). Cold install via `uv sync` takes under 300ms
with cached wheels. The tool requires no system dependencies, no compiler toolchain, and
no Julia runtime for basic functionality.

## Evidence

### Environment

- Container: devcontainer (Ubuntu 24.04, Python 3.12)
- Package manager: uv
- pandapower version: 3.4.0
- Timing method: `time.perf_counter()` (measured, not estimated)

### Measured Timing (warm cache)

| Phase | Wall-clock (s) |
|-------|---------------|
| `uv sync` (warm cache) | 0.04 |
| Import pandapower | 1.87 |
| Load case9 network | 0.58 |
| AC power flow solve | 2.81 |
| **Total (install + first solve)** | **5.29** |

### Measured Timing (cold install — .venv deleted and recreated)

| Phase | Wall-clock (s) |
|-------|---------------|
| `uv sync` (cold, cached wheels) | 0.27 |
| Import pandapower | 3.31 |
| Load case9 network | 0.34 |
| AC power flow solve | 1.43 |
| **Total (cold install + first solve)** | **5.35** |

### Install Details

```
Resolved 41 packages in 0.46ms
Installed 39 packages in 242ms
```

Dependencies: numpy, scipy, pandas, networkx, numba, lightsim2grid, ortools, pandapower
(39 packages total). No compilation required — all binary wheels.

### Friction Points

1. **No friction on install.** `uv sync` with the provided `pyproject.toml` works cleanly.
   No system dependencies, no compiler toolchain, no Julia runtime needed for basic
   functionality.
2. **Import time is moderate (~1.9-3.3s).** pandapower eagerly imports numpy, scipy, pandas,
   and numba. First import after cold install is slower (~3.3s) due to numba initialization;
   subsequent imports stabilize around ~1.9s.
3. **Warning on MATPOWER case loading.** Loading case39 produces a warning about branches
   treated as transformers due to non-unity tap ratios. Informational but could confuse new
   users who do not understand the distinction between lines and transformers in pandapower's
   data model.
4. **No Julia dependency for basic ops.** The PandaModels.jl bridge (for advanced OPF
   formulations) is optional. Core AC/DC power flow and basic OPF work with the pure-Python
   PYPOWER backend.

## Implications

Very low barrier to entry. Sub-6-second install-to-first-solve is among the fastest for
Python power system tools. No system dependencies and no compilation step means the tool
works in any Python 3.12 environment. The cold vs warm timing difference is negligible
(5.35s vs 5.29s), confirming that install overhead is minimal.

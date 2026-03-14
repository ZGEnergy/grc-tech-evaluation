---
test_id: A-1
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v10
skill_version: v1
test_hash: 05bc255c
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.185
timing_source: measured
peak_memory_mb: 0.48
convergence_residual: null
convergence_iterations: null
loc: 145
solver: null
timestamp: 2026-03-13T23:09:44Z
---

# A-1: Solve DCPF on TINY

## Result: PASS

## Approach

Loaded IEEE 39-bus network via the shared MATPOWER loader (`load_pypsa` from
`evaluations/shared/matpower_loader.py`), which applies transformer susceptance
and generator cost patches. Ran `n.lpf()` (PyPSA's linear power flow) which
solves the DC power flow using the B-matrix factorization.

Verified that outputs are accessible as structured pandas DataFrames (not raw
solver vectors): voltage angles via `n.buses_t.v_ang`, nodal injections via
`n.buses_t.p`, and line flows via `n.lines_t.p0`. Transformer flows are also
available via `n.transformers_t.p0`.

## Output

| Metric | Value |
|--------|-------|
| Buses | 39 |
| Lines | 35 |
| Transformers | 11 |
| Generators | 10 |
| Nonzero angles (non-slack) | 38 / 38 |
| Nonzero line flows | 35 / 35 |
| Max voltage angle | 13.46 deg |
| Max line flow | 608.8 MW |
| Total generation capacity | 7,367 MW |

**Voltage angles (first 5 buses, degrees):**

| Bus | Angle (deg) |
|-----|-------------|
| 1 | -12.30 |
| 2 | -8.10 |
| 3 | -10.99 |
| 4 | -11.65 |
| 5 | -10.35 |

**Line flows (first 5 lines, MW):**

| Line | P0 (MW) |
|------|---------|
| L0 | -178.4 |
| L1 | 80.8 |
| L2 | 333.4 |
| L3 | -261.8 |
| L4 | 54.1 |

All outputs are pandas DataFrames with named indices, directly usable for
downstream analysis.

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.185s (including network loading)
- **Solve-only:** 0.177s
- **Timing source:** measured
- **Peak memory:** 0.48 MB (solve only, via tracemalloc)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a1_dcpf.py`

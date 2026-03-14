---
test_id: A-2
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v10
skill_version: v1
test_hash: fca7353e
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.259
timing_source: measured
peak_memory_mb: 0.60
convergence_residual: 3.317e-09
convergence_iterations: 4
loc: 256
solver: null
timestamp: 2026-03-13T23:09:44Z
---

# A-2: Solve ACPF (Newton-Raphson) on TINY

## Result: PASS

## Approach

Loaded IEEE 39-bus network via `matpowercaseframes` + `import_from_pypower_ppc`,
but **without** the shared loader's Patch 1 (transformer `b = 1/x`). This is
critical: PyPSA's transformer `b` field in the AC context represents shunt
susceptance (pi-model parameter), not the series susceptance used in the DC
B-matrix. Applying the DCPF patch causes ACPF to diverge completely (error
grows to 10^42 after 100 iterations).

Ran `n.pf(x_tol=1e-6)` which invokes PyPSA's internal Newton-Raphson solver.
No external solver (Ipopt) is needed for ACPF -- PyPSA uses its own NR
implementation. The solver converged from a flat start in 4 iterations with
a final residual of 3.32e-9, well below the 1e-6 tolerance.

### Convergence verification (per convergence-protocol.md)

1. **Convergence residual:** 3.317e-9 -- below tolerance of 1e-6
2. **Iteration count:** 4 -- nonzero, indicating actual NR iterations
3. **Voltage profile:** 38/39 buses (97.4%) differ from flat-start 1.0 pu by
   more than 0.001 pu. The one bus at exactly 1.0 is within the tolerance
   band. The full profile ranges from 0.982 to 1.064 pu.

All three diagnostics are accessible via the `pf_result` dict returned by
`n.pf()`: keys `converged`, `n_iter`, and `error` (each a DataFrame indexed
by snapshot x subnetwork).

## Output

| Metric | Value |
|--------|-------|
| Converged | Yes (flat start) |
| NR iterations | 4 |
| Convergence residual | 3.317e-09 |
| Tolerance | 1e-06 |
| Non-flat voltage buses | 38 / 39 (97.4%) |
| V_mag range | 0.982 -- 1.064 pu |
| V_mag mean | 1.026 pu |
| Total losses | 31.06 MW (0.50% of load) |
| Total load | 6,254.23 MW |

**Voltage magnitudes (first 5 buses):**

| Bus | V_mag (pu) |
|-----|------------|
| 1 | 1.0394 |
| 2 | 1.0485 |
| 3 | 1.0307 |
| 4 | 1.0045 |
| 5 | 1.0060 |

**Voltage angles (first 5 buses, degrees):**

| Bus | Angle (deg) |
|-----|-------------|
| 1 | -13.54 |
| 2 | -9.79 |
| 3 | -12.28 |
| 4 | -12.63 |
| 5 | -11.19 |

**Line P flows (first 5 lines, MW):**

| Line | P0 (MW) | Q0 (MVAr) |
|------|---------|-----------|
| L0 | -173.7 | -40.3 |
| L1 | 76.1 | -3.9 |
| L2 | 319.9 | 88.6 |
| L3 | -244.6 | 83.0 |
| L4 | 37.3 | 113.1 |

All outputs are structured pandas DataFrames: `n.buses_t.v_mag_pu`,
`n.buses_t.v_ang`, `n.lines_t.p0`, `n.lines_t.q0`, `n.lines_t.p1`.

## Workarounds

None required. The shared loader's DCPF transformer patch must not be applied
for ACPF, but using the raw `import_from_pypower_ppc` path is not a workaround
-- it is the correct loading approach for AC analysis.

## Timing

- **Wall-clock:** 1.259s (including network loading)
- **Solve-only:** 0.271s
- **Timing source:** measured
- **Peak memory:** 0.60 MB (solve only, via tracemalloc)
- **Solver iterations:** 4 (Newton-Raphson)
- **Convergence residual:** 3.317e-09
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a2_acpf.py`

Key implementation note: the test uses a custom `load_network_for_acpf()`
function that loads via `matpowercaseframes` + `import_from_pypower_ppc`
without applying the shared loader's Patch 1 (transformer `b = 1/x`), because
that patch is specific to DCPF B-matrix construction and breaks the AC Y-matrix.

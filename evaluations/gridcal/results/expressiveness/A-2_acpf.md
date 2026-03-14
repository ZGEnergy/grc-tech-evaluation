---
test_id: A-2
tool: gridcal
dimension: expressiveness
network: TINY
status: pass
workaround_class: null
blocked_by: null
protocol_version: "v10"
skill_version: v1
test_hash: "fca7353e"
wall_clock_seconds: 2.24
timing_source: measured
peak_memory_mb: null
convergence_residual: 3.32e-11
convergence_iterations: 4
loc: 198
solver: "NR (native)"
timestamp: "2026-03-13T00:00:00Z"
---

# A-2: Solve AC power flow (Newton-Raphson) on TINY

## Result: PASS

## Approach

Loaded the IEEE 39-bus network via `load_gridcal()`. Configured AC power flow using
`PowerFlowOptions(solver_type=SolverType.NR, tolerance=1e-6, max_iter=100)` and executed
via `vge.power_flow(grid, options=opts)`.

**Solver deviation from protocol:** The eval-config specifies Ipopt as the AC solver.
GridCal does NOT integrate Ipopt for AC power flow -- it uses its own native Newton-Raphson
implementation. This is documented as a finding (see Observations below). The native NR
solver is the correct and only option for ACPF in GridCal.

Flat start converged on the first attempt -- no DC warm start fallback was needed.

Results are accessed via:
- `results.voltage` -- complex bus voltages
- `results.Sf`, `results.St` -- branch complex power flows (from and to ends)
- `results.losses` -- branch losses
- `results.converged` -- boolean
- `results.iterations` -- NR iteration count
- `results.error` -- final convergence residual
- `results.get_bus_df()`, `results.get_branch_df()` -- DataFrame export

## Output

| Metric | Value |
|--------|-------|
| Converged | True |
| NR Iterations | 4 |
| Convergence Residual | 3.32e-11 |
| Buses with Vm != 1.0 | 39/39 (100%) |
| Vm range | 0.982 -- 1.064 pu |
| Vm mean | 1.026 pu |
| Max angle (deg) | 14.54 |
| Total losses (MW) | 43.64 |

Sample voltage magnitudes (pu):

| Bus | Vm | Va (deg) |
|-----|-----|---------|
| 1 | 1.039 | -13.54 |
| 20 | 0.991 | -6.82 |
| 31 (slack) | 0.982 | 0.00 |
| 36 | 1.064 | 4.47 |

All 39 buses have voltage magnitudes differing from the 1.0 pu flat-start value (100%),
far exceeding the >95% threshold. The solution is physically meaningful with losses of
43.64 MW (0.70% of total load).

## Workarounds

None required.

## Timing

- **Wall-clock:** 2.24 s
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** 4 (NR)
- **Convergence residual:** 3.32e-11
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a2_acpf.py`

Key code showing the API:

```python
pf_opts = vge.PowerFlowOptions(
    solver_type=SolverType.NR,
    tolerance=1e-6,
    max_iter=100,
)
pf_results = vge.power_flow(grid, options=pf_opts)

# Convergence diagnostics directly accessible
iterations = pf_results.iterations   # 4
error = pf_results.error             # 3.32e-11
converged = pf_results.converged     # True
```

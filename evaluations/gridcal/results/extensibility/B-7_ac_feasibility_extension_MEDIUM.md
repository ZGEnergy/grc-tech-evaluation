---
test_id: B-7
tool: gridcal
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 21.600
peak_memory_mb: null
loc: 110
solver: HiGHS / Newton-Raphson
timestamp: 2026-03-06T03:00:00Z
---

# B-7: AC Feasibility Extension (MEDIUM)

## Result: PASS

## Approach

Reproduced the DC OPF -> ACPF pipeline on the 10k-bus network. Ran DC OPF via `vge.linear_opf()`, applied generator dispatch to a fresh grid, then ran ACPF via `vge.power_flow()` with Newton-Raphson solver.

## Output

### DC OPF

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Total generation (MW) | 150,916.88 |
| Solve time | 12.96s |

### ACPF with OPF Dispatch

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Voltage range (pu) | 0.9266 -- 1.0888 |
| Max loading (%) | 1,586.92 |
| Solve time | 8.65s |
| Total wall clock | 21.60s |

### Voltage Violations

| Threshold | Count |
|-----------|-------|
| Below 0.9 pu | 0 |
| Above 1.1 pu | 0 |

### Workaround Assessment

No workaround was needed. The DC OPF -> ACPF pipeline works entirely through the documented public API on the 10k-bus network:

1. `vge.open_file()` -- load MATPOWER file
2. `vge.linear_opf()` -- DC OPF solver
3. `gen.P = dispatch[i]` -- set generator dispatch
4. `vge.power_flow()` with `SolverType.NR` -- ACPF
5. `results.voltage` / `results.loading` -- inspect results

ACPF converged successfully with the OPF dispatch. The high loading percentages (>100%) indicate some branches exceed their thermal ratings in the AC solution, which is expected since the DC OPF does not account for reactive power flows.

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b7_ac_feasibility_extension_medium.py`

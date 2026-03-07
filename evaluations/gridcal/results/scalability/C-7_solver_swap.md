---
test_id: C-7
tool: gridcal
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 14.06
peak_memory_mb: 127.15
loc: 45
solver: "HiGHS, SCIP"
timestamp: 2026-03-06T04:00:00Z
---

# C-7: Solver Swap (Grade: MEDIUM)

## Result: PASS

## Network

ACTIVSg10k -- 10,000 buses, 12,706 branches, 2,485 generators.

## Approach

Ran DC OPF with both available solvers (HiGHS and SCIP) via `opts.mip_solver = MIPSolvers.HIGHS|SCIP`. CBC and GLPK are not available in this environment.

## Output

| Metric | HiGHS | SCIP |
|--------|-------|------|
| Converged | Yes | Yes |
| Solve time (s) | 14.06 | 11.87 |
| Peak memory (MB) | 127.15 | 114.52 |
| Total generation (MW) | 150,916.88 | 150,916.88 |
| Active generators | 1,937 | 1,937 |
| LMP range | 20.064 -- 20.064 | 20.064 -- 20.064 |
| Max loading (%) | 84.72 | 84.72 |
| Binding branches | 0 | 0 |

### Comparison

| Metric | Value |
|--------|-------|
| Generation difference | 0.0 MW |
| SCIP / HiGHS speedup | 0.84x (SCIP slightly faster) |
| Results identical | Yes |
| Solvers available | 2 (HiGHS, SCIP) |
| Solvers not available | 2 (CBC, GLPK) |

## Notes

Both solvers produce identical dispatch and LMPs. Solver swap is a one-line change (`opts.mip_solver = MIPSolvers.SCIP`). Only 2 of 4 potential solvers are available in the current environment, but the swap mechanism works correctly.

## Workarounds

None required. Solver swap is native API.

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c7_solver_swap.py`

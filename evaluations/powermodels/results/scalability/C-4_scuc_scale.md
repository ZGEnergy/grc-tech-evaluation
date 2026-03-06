---
test_id: C-4
tool: powermodels
dimension: scalability
network: SMALL
status: qualified_pass
wall_clock_seconds: 624.43
peak_memory_mb: 72.41
timestamp: 2026-03-05
---

# C-4: SCUC 24hr at SMALL (2000 buses)

## Result: QUALIFIED PASS

The model was successfully constructed but neither solver found a feasible solution within the 300s time limit.

## Timing

| Solver | Wall-clock | Status | MIP Gap | Objective |

|--------|-----------|--------|---------|-----------|

| HiGHS  | 180.3s    | OTHER_ERROR | N/A | N/A |

| SCIP   | 408.0s    | TIME_LIMIT | 1e20 (no feasible) | null |

- Problem size: 166,416 variables (31,104 binary), 495,792 constraints
- Active generators: 432 (of 544 total; 112 offline in base data)
- Periods: 24
- Peak memory: 72.4 MB (SCIP)
- CPU cores: 1 (single-threaded)

## Model Construction
The custom SCUC model was successfully built by:
1. `PowerModels.replicate(data, 24)` for multi-period structure
2. `instantiate_model(mn_data, DCPPowerModel, build_mn_opf)` for base DC OPF
3. Adding binary commitment variables `u[t,g]`, startup `v[t,g]`, shutdown `w[t,g]`
4. Linking constraints: `pmin*u <= pg <= pmax*u`
5. Startup/shutdown logic: `u[t] - u[t-1] = v[t] - w[t]`
6. Minimum up time (3h), minimum down time (2h)
7. Ramp rate constraints (hourly, derived from ramp_10)
8. Startup costs added to objective

## Solver Notes
- **HiGHS**: Cannot solve MIQP (mixed-integer quadratic programming). PowerModels' DC OPF uses quadratic cost curves, and adding binary variables creates an MIQP. HiGHS only supports MILP + QP separately, not MIQP.
- **SCIP**: Supports MIQP but did not find a feasible solution in 300s on this 2000-bus problem. Zero nodes explored suggests the LP relaxation at the root node was itself very slow.

## Analysis
The 2000-bus x 24-period SCUC creates a massive optimization problem (166k variables, 496k constraints). Key findings:

1. **PowerModels has no built-in SCUC** -- requires ~100 LOC of custom JuMP code
2. **HiGHS cannot solve MIQP** -- a fundamental limitation for UC problems with quadratic costs
3. **SCIP is too slow** for industrial-scale UC at 2000 buses
4. A practical workaround would be to linearize costs (enabling HiGHS MILP), but this was not tested
5. Commercial solvers (Gurobi, CPLEX) would likely handle this scale, but are not available in this evaluation

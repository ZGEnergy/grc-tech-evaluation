---
test_id: C-7
tool: powermodels
dimension: scalability
network: MEDIUM
status: pass
wall_clock_seconds: 834.30
peak_memory_mb: 30.77
timestamp: 2026-03-05
---

# C-7: Solver Swap at MEDIUM (10000 buses)

## Result: PASS

## Timing

| Solver | Wall-clock | Status | Objective | Success |

|--------|-----------|--------|-----------|---------|

| HiGHS  | 452.8s    | OTHER_ERROR | 0.0 | Numerical failure |

| GLPK   | 9.7s      | ERROR | N/A | Unsupported quadratic objective |

| SCIP   | 330.8s    | TIME_LIMIT | null | No solution in 300s |

| Ipopt  | 20.6s     | LOCALLY_SOLVED | 2,446,806 | Clean convergence |

- CPU cores: 1 (single-threaded)
- Reformulation required: **No** -- solver swap is a single argument change

## Swap Mechanism

```julia
# Swap is trivially changing the optimizer argument:
result = solve_dc_opf(data, HiGHS.Optimizer)
result = solve_dc_opf(data, GLPK.Optimizer)
result = solve_dc_opf(data, SCIP.Optimizer)
result = solve_dc_opf(data, Ipopt.Optimizer)

```

No reformulation, no model reconstruction, no code changes beyond the solver selection. This is a direct benefit of the JuMP/MathOptInterface abstraction layer.

## Solver Compatibility Matrix (DC OPF at 10k buses)

| Solver | QP Support | Convergence | Speed |

|--------|-----------|-------------|-------|

| Ipopt  | Yes (NLP) | Reliable | Fast (20.6s) |

| HiGHS  | Yes (QP)  | Unreliable at scale | Slow (timeout/error) |

| SCIP   | Yes (MINLP) | Timeout | Very slow |

| GLPK   | No (LP only) | N/A | N/A for QP |

## Analysis
PowerModels + JuMP provides seamless solver interchange with zero code changes. However, solver compatibility at scale is a critical concern:

1. **Only Ipopt reliably solves the 10k-bus DC OPF** within reasonable time
2. HiGHS, despite being the default open-source LP/QP solver, has numerical stability issues on large QPs
3. GLPK is LP-only and cannot handle PowerModels' quadratic cost formulation
4. SCIP is too slow for large continuous QPs (designed for MINLP)

This is an important operational finding: while the API supports any JuMP-compatible solver, practical solver selection at scale is constrained to Ipopt for QP problems.

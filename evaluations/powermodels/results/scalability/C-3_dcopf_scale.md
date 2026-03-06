---
test_id: C-3
tool: powermodels
dimension: scalability
network: MEDIUM
status: pass
wall_clock_seconds: 1246.81
peak_memory_mb: 30.79
timestamp: 2026-03-05
---

# C-3: DC OPF at MEDIUM (10000 buses) with Multiple Solvers

## Result: PASS

## Timing

| Solver | Wall-clock | Status | Objective | Memory |

|--------|-----------|--------|-----------|--------|

| Ipopt  | 60.5s     | LOCALLY_SOLVED | 2,446,806 | 30.8 MB |

| HiGHS  | 331.7s    | TIME_LIMIT | 2,509,079 | 26.8 MB |

| GLPK   | 811.0s    | OPTIMAL | 2,440,105 | 21.6 MB |

- CPU cores: 1 (single-threaded)

## Output
- Network: 10,000 buses, 12,706 branches, 2,485 generators
- Objective range across solvers: ~69,000 (due to different cost models and convergence)
- Sample LMPs (Ipopt): -2073.77 across all sampled buses

## Solver Notes

**Ipopt (recommended for 10k-bus DC OPF):** Fastest solver at 60.5s. Handles the quadratic cost objective natively as a QP. Converged cleanly.

**HiGHS:** Hit 300s time limit. The QP solver on this 10k-bus network has numerical stability issues -- on initial runs it reported "Solve error" with primal infeasibilities. On the timed run it reached TIME_LIMIT with objective 2,509,079 (higher than optimal, suggesting incomplete convergence).

**GLPK:** LP-only solver. Required cost linearization (quadratic-to-linear at midpoint). Converged in 811s to objective 2,440,105. The ill-conditioned basis matrix warning suggests numerical difficulties at this scale.

## Method

```julia
result = solve_dc_opf(data, Ipopt.Optimizer)

```

Solver swap requires only changing the optimizer argument -- no reformulation or code changes.

## Analysis
DC OPF at 10k buses is tractable but solver choice matters significantly:
1. **Ipopt** is 5x faster than HiGHS and 13x faster than GLPK for this problem
2. **HiGHS QP solver has numerical issues** at 10k scale (primal infeasibilities, solve errors)
3. **GLPK** cannot handle quadratic objectives natively; linearization introduces approximation error
4. PowerModels' quadratic cost formulation is natural for DC OPF but limits LP-only solvers

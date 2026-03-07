---
test_id: C-3
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 3.134
peak_memory_mb: 183.8
loc: 184
solver: Ipopt
timestamp: 2026-03-07T00:00:00Z
---

# C-3: DC OPF Scalability on MEDIUM (ACTIVSg 10000-bus)

## Result: PASS

## Solver Comparison

| Solver | Formulation | Termination | Solve Time | Objective ($/hr) | Note |
|--------|-------------|-------------|------------|------------------|------|
| **Ipopt** | QP (quadratic costs) | LOCALLY_SOLVED | 3.13s | 2,436,631.22 | Interior point, 25 iterations |
| **GLPK** | LP (linearized costs) | OPTIMAL | 50.91s | 2,401,337.08 | Simplex, ~41k iterations |
| **HiGHS** | QP (quadratic costs) | TIME_LIMIT | 300.0s | 2,436,631.2 (approx) | QP ASM solver, 113k iterations at timeout |

## Metrics (Ipopt -- primary)

| Metric | Value |
|--------|-------|
| Wall-clock | 3.134s (including model build) |
| Ipopt internal | 1.153s |
| Iterations | 25 |
| Peak memory | 183.8 MB |
| Memory delta | 108.9 MB |
| Variables | 23,632 |
| Equality constraints | 22,707 |
| Inequality constraints | 12,217 |

## Analysis

**Ipopt** is the clear winner for DC OPF at this scale. Its interior point method handles the QP formulation (quadratic generator costs) in 25 iterations / 1.15s. The barrier method's polynomial complexity scales well with network size.

**HiGHS** hit its 300s time limit. The QP active-set method (ASM) accumulated 113,501 iterations without converging. HiGHS' simplex-based QP solver is not competitive with interior point methods at 10,000-bus scale. Note: HiGHS' LP solver would likely be fast, but PowerModels generates a QP when cost functions are quadratic.

**GLPK** solved in 50.91s but required fully linearized costs (quadratic terms removed, `ncost=2`). The different objective (2,401,337 vs 2,436,631) reflects the linearized cost approximation. GLPK's simplex method is adequate for LP at this scale but cannot handle the native QP.

## Data Workaround

1,349 generators required cost array fixes (empty `cost=[]` or `ncost=0`). See A-3 MEDIUM result for details.

## Methodology

- JIT warm-up: solved case39 DC OPF before timing
- Each solver run on a fresh parse of the network data
- GLPK costs fully linearized to `ncost=2` (linear + constant terms only)
- Duals enabled via `setting = Dict("output" => Dict("duals" => true))`

## Test Script

Batch runner: `evaluations/powermodels/tests/test_medium_all.jl`
Supplemental (GLPK fix): `evaluations/powermodels/tests/test_medium_supplemental.jl`

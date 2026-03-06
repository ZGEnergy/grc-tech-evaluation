---
tag: solver-issues
dimension: scalability
tool: powermodels
timestamp: 2026-03-05
---

# Solver Issues Observed During Scalability Testing

## Critical: HiGHS QP Solver Fails on 10k-Bus Networks

**Affected tests:** C-3, C-7, C-8, C-10 (all MEDIUM/10k-bus DC OPF)

HiGHS 1.13.1's QP solver consistently fails on the ACTIVSg10k DC OPF problem (34,924 rows, 24,643 cols, 24,643 Hessian nonzeros). The failure mode is:

1. Solver iterates for 300-450 seconds
2. Reaches what it believes is an optimal solution
3. Post-solve verification detects primal infeasibilities (13 rows, max residual 0.1008)
4. Returns `SOLVE_ERROR` or `OTHER_ERROR`

This is a **systematic numerical stability issue** in HiGHS's interior-point QP solver on ill-conditioned power system matrices, not a PowerModels bug.

**Impact:** HiGHS is unusable as a QP solver for DC OPF at 10k+ bus scale. Users must use Ipopt instead.

## Critical: HiGHS Cannot Solve MIQP

**Affected test:** C-4 (SCUC at 2000 buses)

HiGHS explicitly rejects mixed-integer quadratic programs: `"Cannot solve MIQP problems with HiGHS"`. PowerModels DC OPF uses quadratic cost curves, and adding binary UC commitment variables creates an MIQP that HiGHS cannot handle.

**Impact:** Unit commitment problems with quadratic costs require SCIP (slow) or commercial solvers (Gurobi/CPLEX). Linearizing costs enables HiGHS MILP but introduces approximation.

## High: GLPK Cannot Handle Quadratic Objectives

**Affected tests:** C-3, C-7

GLPK is LP-only and throws `UnsupportedAttribute{ObjectiveFunction{ScalarQuadraticFunction}}` on PowerModels' standard DC OPF. With linearized costs it works but is slow (811s vs Ipopt's 60s on 10k buses) and produces ill-conditioned basis warnings.

**Impact:** GLPK is not suitable for PowerModels DC OPF without cost linearization preprocessing.

## High: SCIP Too Slow for Continuous QP and Large MIP

**Affected tests:** C-4, C-7

SCIP hits the 300s time limit without converging on both:
- DC OPF at 10k buses (continuous QP) -- TIME_LIMIT, no solution
- SCUC at 2000 buses (MIQP with 31k binary vars) -- TIME_LIMIT, MIP gap = 1e20 (no feasible solution found)

**Impact:** SCIP is designed for MINLP/constraint programming, not large-scale LP/QP. It should not be the primary solver for any scalability benchmark.

## Medium: HiGHS QP Extremely Slow on Multi-Period Problems

**Affected test:** C-6

HiGHS takes >900 seconds for a single QP iteration on the 2000-bus x 24-period multi-network OPF (189k rows, 135k cols). After 2700s and 28k iterations, the objective has barely decreased (0.1% reduction). Each multi-period scenario would take >45 minutes.

**Impact:** Multi-period OPF at 2000+ buses requires Ipopt, not HiGHS.

## Summary: Recommended Solver Configuration

| Problem Type | Scale | Recommended Solver | Avoid |

|-------------|-------|-------------------|-------|

| DC PF | Any | Native (no solver) | -- |

| DC OPF (QP) | <1k buses | HiGHS or Ipopt | GLPK |

| DC OPF (QP) | >1k buses | **Ipopt only** | HiGHS, GLPK, SCIP |

| SCUC (MIQP) | Any | SCIP (slow) or commercial | HiGHS |

| Multi-period OPF | >500 buses | **Ipopt only** | HiGHS |

| SCOPF | >1k buses | Ipopt + iterative approach | Multi-network brute force |

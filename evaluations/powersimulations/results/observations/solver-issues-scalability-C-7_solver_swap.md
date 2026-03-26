---
tag: solver-issues
source_dimension: scalability
source_test: C-7
tool: powersimulations
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Solver Performance Variance on 10K-Bus DCOPF LP

## Finding

All four solvers solve the same 24,476-variable / 41,370-constraint DCOPF LP, with significant
performance variance:

| Solver | Time | Relative |
|--------|------|----------|
| HiGHS | 11.6 s | 1.0x (baseline) |
| SCIP | 26.4 s | 2.3x |
| Ipopt | 36.9 s | 3.2x |
| GLPK | 54.9 s | 4.7x |

HiGHS's simplex implementation is the fastest. SCIP (MIP solver) outperforms both Ipopt (NLP
interior-point) and GLPK (LP simplex) on this pure LP. GLPK is the slowest by nearly 5x.

All solvers produce consistent objective values to within 0.000002%.

## Context

[solver-specific] Performance differences are inherent to solver architectures, not to
PowerSimulations.jl. The tool's JuMP integration allows straightforward swapping.

## Implications

Low severity for tool evaluation. Performance ranking is useful context for solver selection
guidance.

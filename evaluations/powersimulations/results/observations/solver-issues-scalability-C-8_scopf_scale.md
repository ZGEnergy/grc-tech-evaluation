---
tag: solver-issues
source_dimension: scalability
source_test: C-8
tool: powersimulations
severity: high
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: HiGHS Crashes on MEDIUM SCOPF (535k Constraints)

## Finding

HiGHS returns OTHER_ERROR after 328s when solving the MEDIUM (10k-bus) SCOPF LP with 535,000
constraints (19,452 base-case flow limits + 474,178 N-1 contingency constraints + 41,370 base
DCOPF constraints). The same solver handles the unconstrained DCOPF (24,476 variables, ~42k
constraints) in 6.4s without issue.

## Context

The SCOPF LP has a constraint-to-variable ratio of ~22:1, which is unusually high for an LP.
The constraint matrix is very sparse (each N-1 constraint involves only 2 variables) but the
sheer count exceeds HiGHS's numerical stability envelope at 10K scale with single-threaded
solving. On SMALL (2000-bus), the same approach with 160,443 total constraints solves optimally
in 9.6s.

The unconstrained DCOPF on MEDIUM produces identical results to C-3 ($3,659,662.46), confirming
that the model construction is correct and the failure is specific to the constraint count.

## Implications

This is [solver-specific: HiGHS numerical limit on large sparse LPs]. Multi-threaded HiGHS or
a commercial solver (Gurobi, CPLEX) might handle the constraint count. However, the root cause
is also [tool-specific]: a built-in SCOPF with iterative constraint screening (Benders
decomposition, lazy constraint generation) would add only the 3-10 binding contingency
constraints instead of all 474k upfront, avoiding the solver scaling issue entirely.

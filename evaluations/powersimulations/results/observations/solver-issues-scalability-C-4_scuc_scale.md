---
tag: solver-issues
source_dimension: scalability
source_test: C-4
tool: powersimulations
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: HiGHS multi-threaded MILP provides minimal speedup on SCUC

## Finding

HiGHS with 32 threads solves the ACTIVSg 2000-bus SCUC (22,608 binary variables, 157,440 total
variables, 434,016 constraints) only 5.6% faster than single-threaded (439.6s vs 465.8s). Both
configurations reach the same 0.93% MIP gap and identical objective value ($27,224,128).

SCIP single-threaded fails to close the gap within 600 seconds, finding only a 4.1% worse
incumbent ($28,337,106).

## Context

The v11 protocol requires reporting both single-thread and max-thread timings for MILP tests.
The minimal HiGHS parallel speedup is consistent with known limitations of HiGHS's concurrent
tree search on MILP problems where the initial heuristic solution dominates solve time.

## Implications

This is a solver-specific finding, not a tool limitation. PowerSimulations.jl correctly passes
the thread count to HiGHS via JuMP's `optimizer_with_attributes`. The limited speedup means
that for SCUC-class problems at this scale, adding more threads is not an effective scaling
strategy with HiGHS. This finding applies equally to all tools using HiGHS for MILP.

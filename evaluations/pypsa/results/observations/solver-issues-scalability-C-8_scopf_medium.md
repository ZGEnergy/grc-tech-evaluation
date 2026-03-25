---
tag: solver-issues
source_dimension: scalability
source_test: C-8
tool: pypsa
severity: low
timestamp: 2026-03-24T21:00:00Z
---

# Observation: HiGHS simplex provides zero multi-thread speedup for SCOPF LP

## Finding

HiGHS dual simplex solver shows no multi-thread speedup for the SCOPF LP (1.3M rows,
15k cols). The 32-thread run was marginally slower (34.27s solver) than 1-thread
(29.48s solver), yielding a 0.92x "speedup." This is consistent with C-3 and is a
known property of simplex methods.

## Context

C-8 SCOPF on MEDIUM (10k buses, 50 contingencies) was solved with both 1 and 32
HiGHS threads. The LP has 1,313,689 rows and 2,416,227 nonzeros. Despite the large
problem size, simplex remains sequential. The HiGHS IPM solver supports parallelism
for LP but was not tested (PyPSA defaults to simplex). The dominant wall-clock cost
remains linopy model building (~285s of 315s total) [tool-specific], not the solver
itself (29.5s) [solver-specific].

## Implications

Multi-threading provides no scalability benefit for PyPSA SCOPF at this problem size.
Scalability improvements would need to target (1) linopy model construction overhead
[tool-specific] or (2) switching to HiGHS IPM solver for parallelism [solver-specific].
This is consistent with C-3's observation and reinforces the attribution: thread
speedup is solver-specific, model building overhead is tool-specific.

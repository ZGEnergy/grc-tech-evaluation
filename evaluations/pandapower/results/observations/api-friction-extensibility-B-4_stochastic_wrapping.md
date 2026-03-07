---
tag: api-friction
source_dimension: extensibility
source_test: B-4
tool: pandapower
severity: medium
timestamp: 2026-03-06T00:00:00Z
---

# Observation: No native scenario/timeseries API for OPF -- loop required

## Finding

pandapower has no native multi-period DCOPF or scenario-indexed API. While `pandapower.timeseries.run_timeseries()` exists for sequential power flow, it does not support OPF. Stochastic multi-period DCOPF must be implemented as a manual loop: modify DataFrames, call `rundcopp()`, collect results. The loop overhead is minimal (no model reconstruction), but the user must manage all scenario bookkeeping manually.

## Context

B-4 required 20 scenarios x 12 hours = 240 DCOPF solves with correlated perturbations by resource type. The implementation was a nested for-loop with in-place DataFrame modification. This worked and completed in 5.09 s (21.2 ms per solve), but 32 of 240 solves (13.3%) failed to converge, possibly due to PYPOWER's interior point solver limitations at low-load operating points.

## Implications

The lack of a native scenario API is not a fundamental limitation for the Extensibility grade (the loop works), but the solver failure rate and inability to swap solvers (no HiGHS support) compounds into a meaningful friction point. This should be considered in the Scalability assessment, where larger scenario counts may amplify the convergence issue.

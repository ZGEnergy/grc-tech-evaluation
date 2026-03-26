---
tag: api-friction
source_dimension: scalability
source_test: C-4
tool: gridcal
severity: medium
timestamp: "2026-03-24T12:00:00Z"
---

# Observation: No solver thread configuration exposed in GridCal OPF API

## Finding

GridCal's `run_linear_opf_ts` function and its PuLP-based solver interface do not expose
multi-threading configuration. HiGHS and SCIP both support parallel MILP solving, but
GridCal's internal `lp_model.solve()` call passes no thread count to the underlying solver.
PuLP's `HiGHS_CMD` accepts a `threads` parameter, but GridCal does not forward it.

## Context

During C-4 (SCUC 24hr on SMALL), the v11 protocol requires reporting both 1-thread and
max-thread wall-clock times. Neither timing could be produced because GridCal's API provides
no mechanism to configure solver thread count. The `run_linear_opf_ts` signature has 25
parameters but none for thread control. The `OptimalPowerFlowOptions` class also has no
thread-related attribute.

## Implications

The Accessibility evaluation should note that users needing parallel MILP solving with
GridCal would need to either (1) bypass GridCal's OPF driver and build their own PuLP model,
or (2) modify GridCal's source code to pass thread options through. This is a meaningful
gap for production deployments where solve time matters. The multi-threading gap affects
all MILP-class tests (C-4 and potentially future SCUC scale tests).

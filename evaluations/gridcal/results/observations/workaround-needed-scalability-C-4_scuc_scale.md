---
tag: workaround-needed
source_dimension: scalability
source_test: C-4
tool: gridcal
severity: high
timestamp: "2026-03-24T12:00:00Z"
---

# Observation: Sequential snapshot workaround required for SCUC at SMALL scale

## Finding

True 24-hour multi-period SCUC is not achievable on the SMALL network (ACTIVSg 2000-bus)
with GridCal v5.6.28. A sequential snapshot workaround (each hour solved independently)
was used instead, which completes in ~150s per solver but loses inter-temporal UC coupling
(min up/down times, ramp rates across hours).

## Context

The native `OptimalPowerFlowTimeSeriesDriver` with `OpfDispatchMode.UnitCommitment` cannot
be used due to: (1) TapPhaseControl enum bug crashes on networks with transformers, and
(2) the monolithic 24h MILP formulation (~13k binary variables) is computationally intractable.

The workaround uses `run_linear_opf_ts(grid, time_indices=None, solver_type=...)` in
snapshot mode -- a documented public API -- classified as STABLE. Both HiGHS and SCIP
produce identical results (24/24 hours converged, 430 generators committed for all hours).

## Implications

The Extensibility dimension should note that while GridCal's API exposes UC parameters
(MinTimeUp, MinTimeDown, StartupCost, RampUp, RampDown), these are only effective for
small networks where the monolithic MILP is tractable. The workaround demonstrates
economic dispatch capability at scale but not unit commitment capability. This finding
differentiates GridCal from tools that can decompose the UC problem for scalability.

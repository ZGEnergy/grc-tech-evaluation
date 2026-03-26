---
tag: solver-issues
source_dimension: scalability
source_test: C-4
tool: gridcal
severity: high
timestamp: "2026-03-24T12:00:00Z"
---

# Observation: Monolithic 24h SCUC MILP intractable on SMALL network

## Finding

VeraGridEngine's time-series OPF driver formulates the 24-hour SCUC as a single monolithic
MILP with ~13,056 binary variables (544 generators x 24 hours). HiGHS ran for >25 minutes
on this problem without producing a result before being terminated. Additionally, the
TapPhaseControl enum bug (v5.6.28) prevents the time-series OPF driver from running on
networks with transformers. [mixed: tool formulates monolithic MILP; solver cannot solve at scale]

## Context

During C-4 (SCUC 24hr on SMALL), the native `OptimalPowerFlowTimeSeriesDriver` with
`OpfDispatchMode.UnitCommitment` was attempted first. The driver either crashes on the
TapPhaseControl enum or, if that is bypassed, cannot solve the monolithic MILP within
a reasonable time budget.

The sequential snapshot workaround (each hour solved independently in ~1.8s) completes all
24 hours in ~150s total with both HiGHS and SCIP, but loses inter-temporal UC coupling
(min up/down times, ramp rates).

Additionally, GridCal's PuLP-based solver interface does not expose multi-threading
configuration. HiGHS supports parallel MILP solving, but the `run_linear_opf_ts` function
has no thread parameter, and the internal `lp_model.solve()` call does not forward thread
settings to PuLP. [mixed: tool binding does not expose solver's multi-threading]

## Implications

This finding affects the scalability grade: GridCal can solve individual hourly OPF snapshots
efficiently on the SMALL network (~1.8s per snapshot), but cannot solve the coupled
multi-period SCUC problem. The Maturity evaluation should note the gap between the existence
of UC mode parameters (min up/down, ramps, startup costs) and their practical applicability
at scale. The Accessibility dimension should note the lack of multi-threading configuration
exposure.

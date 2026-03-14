---
tag: solver-issues
source_dimension: scalability
source_test: C-4
tool: gridcal
severity: high
timestamp: "2026-03-13T04:30:00Z"
---

# Observation: Monolithic 24h SCUC MILP intractable on SMALL network

## Finding

VeraGridEngine's time-series OPF driver formulates the 24-hour SCUC as a single monolithic
MILP with ~13,056 binary variables (544 generators x 24 hours). HiGHS ran for >25 minutes
on this problem without producing a result before being terminated. This compounding with the
TapPhaseControl enum bug (see B-4 observation) means true multi-period SCUC is not achievable
on the SMALL network in v5.6.28.

## Context

During C-4 (SCUC 24hr on SMALL), the native `OptimalPowerFlowTimeSeriesDriver` with
`OpfDispatchMode.UnitCommitment` was attempted first. The process consumed 3.4 GB RAM and
119% CPU for >25 minutes with no solver output. This is distinct from the TapPhaseControl
bug — the driver did not crash, it simply could not solve the problem within a reasonable
time budget.

The sequential snapshot workaround (each hour solved independently in ~1.7s) completes all
24 hours in ~142s total, but loses inter-temporal UC coupling (min up/down times, ramp rates).

## Implications

This finding affects the scalability grade: GridCal can solve individual hourly OPF snapshots
efficiently on the SMALL network (~1.7s per snapshot with HiGHS), but cannot solve the coupled
multi-period SCUC problem. The Maturity evaluation should note the gap between the existence
of UC mode parameters (min up/down, ramps, startup costs) and their practical applicability
at scale.

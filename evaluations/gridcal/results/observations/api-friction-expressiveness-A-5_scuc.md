---
tag: api-friction
source_dimension: expressiveness
source_test: A-5
tool: gridcal
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Time profile API and commitment variable opacity

## Finding

Two API friction points in GridCal's SCUC workflow:

1. **Time profile requires unix timestamps:** `MultiCircuit.set_time_profile()` accepts
   `IntVec` (numpy int64 array of unix timestamps), not pandas DatetimeIndex or datetime
   objects. Users must manually convert, adding ~2 lines of boilerplate.

2. **Binary commitment variables not directly accessible:** The
   `OptimalPowerFlowTimeSeriesResults` object does not expose the binary commitment
   variables from the MILP solution. Commitment status must be inferred from
   `generator_power > threshold`, which introduces ambiguity for generators dispatched
   near zero. The MIP gap is also not directly extractable from the results object.
   [tool-specific: no direct access to binary UC variables or MIP gap]

## Context

During A-5 (SCUC), the initial attempt used `pd.date_range()` directly for time profiles,
which failed. The binding verification (v11 mandatory) showed identical commitment schedules
with and without min up/down constraints, making the min up/down constraints non-binding
in the baseline solution.

## Implications

For accessibility assessment: The time profile API is lower-level than expected. Other tools
(PyPSA, pandapower) accept datetime objects directly. The commitment variable opacity means
users cannot verify UC formulation behavior without inference.

For extensibility assessment: The inability to access the underlying MIP model or binary
variables limits formulation transparency and debugging capability.

# Observation: API Friction -- B-7 AC Feasibility Extension

**Tag:** api-friction
**Test:** B-7 (AC Feasibility Extension)
**Dimension:** extensibility

## Observation

The unit mismatch between PSI's `read_variables()` output and PowerSystems.jl's
component values is the most significant API friction point discovered in the
evaluation. PSI returns dispatch values ~100x larger than component Pmax values,
with no documentation or conversion utility.

This creates a reliability risk for any workflow that transfers results between
PSI (optimization) and PowerFlows (power flow), which is a common production
pattern (DCOPF dispatch -> ACPF validation).

The root cause appears to be PSI's internal use of the time series multiplier system
and device-base vs. system-base per-unit conventions. The 100x factor matches the
system base MVA (100 MVA), but this is empirically determined -- not documented.

## Impact

High. This is a silent correctness issue -- the user gets plausible-looking numbers
that are simply in the wrong scale. Without careful comparison against known limits,
the error could propagate through downstream analysis undetected.

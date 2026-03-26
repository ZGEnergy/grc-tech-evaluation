---
tag: workaround-needed
source_dimension: scalability
source_test: C-4
tool: powersimulations
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: PSI initialization bypass required at SMALL scale SCUC

## Finding

The `initialize_model=false` + `JuMP.optimize!()` workaround first documented in A-5 (TINY
SCUC) is also required at SMALL scale (ACTIVSg 2000-bus). PSI's initialization model fails
with both HiGHS and SCIP, confirming this is a systematic limitation of the initialization
procedure rather than a scale-specific issue.

## Context

PSI's `solve!()` method runs an initialization model before the main solve. This initialization
fails on SCUC problems, requiring the user to bypass it via `initialize_model=false` and call
`JuMP.optimize!()` directly on the underlying JuMP model. This also breaks PSI's result
tracking, requiring direct access to internal containers via `PSI.get_optimization_container`
and `PSI.get_variables`.

Additionally, `HydroDispatch` generators (25 of 544 in ACTIVSg 2000) cannot be included in the
UC template because PSI v0.30.2 does not export hydro formulations compatible with
`ThermalStandardUnitCommitment`.

## Implications

This workaround is classified as fragile because it depends on internal PSI APIs that are not
part of the public interface. The workaround pattern is reproducible and consistent across
network scales (TINY and SMALL), but could break on version upgrade. This is a tool-specific
limitation that affects the scalability grade.

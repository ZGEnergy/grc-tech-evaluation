---
tag: formulation-difference
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: powermodels
severity: high
timestamp: "2026-03-24T12:00:00Z"
---

# Observation: DCPPowerModel Simplified B-Matrix Causes 97.6% Bus Angle Failure on FNM

## Finding

PowerModels' `solve_dc_pf` (which hardcodes `DCPPowerModel`) uses a simplified B-matrix
that ignores transformer tap ratios. On the 27,862-bus FNM network with 12,501
transformer-connected buses, this produces systematic angle deviations of 5.1 degrees
mean (62.2 degrees max) compared to MATPOWER's full B-matrix reference, causing 97.6% of
buses to fail the 1.0-degree tolerance.

## Context

G-FNM-3 tested DCPF verification by comparing PowerModels' solve_dc_pf output against
the MATPOWER DCPF reference solution. The deviation pattern is global and systematic, not
localized to specific buses or regions. The simplified B-matrix formula `b = -1/x` produces
different power distribution than the full formula that accounts for `tap` and `shift`
parameters in the admittance matrix.

PowerModels does offer `DCMPPowerModel` (full B-matrix) but it is not accessible through
the convenience function `solve_dc_pf`, which hardcodes `DCPPowerModel`. Users must call
`solve_pf(data, DCMPPowerModel, optimizer)` to get the full formulation.

## Implications

This finding affects scalability (Suite C) and expressiveness (Suite A) evaluations: any
DCPF-based analysis in PowerModels on networks with significant transformer tap ratios
will produce systematically different results from MATPOWER. The `DCMPPowerModel` option
exists but requires the user to know about the formulation difference and use the
lower-level `solve_pf` API instead of `solve_dc_pf`.

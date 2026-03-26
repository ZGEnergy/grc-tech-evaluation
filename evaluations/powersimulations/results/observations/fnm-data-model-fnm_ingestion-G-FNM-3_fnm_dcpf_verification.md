---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: powersimulations
severity: medium
timestamp: "2026-03-24T18:30:00Z"
---

# Observation: PowerFlows.jl DC path returns per-unit flows and radian angles despite MW/degree log claim

## Finding

PowerFlows.jl v0.9.0 DCPowerFlow returns bus angles in radians and branch flows in
per-unit (system base), while the `@info` log message claims "Powers are exported in
MW/MVAr." The AC path correctly exports in MW. This documentation inconsistency requires
manual unit conversion (`rad2deg` for angles, `* baseMVA` for flows) for any downstream
analysis using the DC path.

## Context

Discovered during G-FNM-3 DCPF verification on the 27,862-bus FNM main island. Without
the correction, branch flows would be 100x too small (per-unit vs MW) and angles would
be in radians instead of degrees. The initial comparison showed nonsensical deviations
until the unit mismatch was identified empirically by comparing magnitudes against the
MATPOWER reference.

## Implications

This affects any user running DC power flow via PowerFlows.jl who trusts the log output
format claim. The Accessibility audit should note this as a documentation gap with
potential for silent unit errors. The inconsistency between AC and DC output paths adds
friction for users switching between power flow types.

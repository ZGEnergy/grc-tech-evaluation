---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-3
tool: powersimulations
severity: medium
timestamp: "2026-03-07T01:30:00Z"
---

# Observation: Single-period OPF requires time series workaround in PSI

## Finding

PowerSimulations.jl cannot solve a single-period DC OPF without first injecting synthetic
time series data into the PowerSystems.System. This requires creating `SingleTimeSeries`
objects for every generator and load, then transforming them to `Deterministic` forecasts.
The workaround is classified as **stable** (uses documented public API) but adds ~30 lines
of boilerplate.

## Context

The test script for A-3 is 297 LOC compared to 130 LOC for A-1 (DCPF via PowerFlows.jl)
and 178 LOC for A-2 (ACPF via PowerFlows.jl). The additional complexity comes entirely
from PSI's time series requirements. PSI is designed as a multi-period simulation
framework, so this requirement is by design -- but it means the tool is poorly suited
for ad-hoc single-period OPF studies without wrapping the boilerplate in a helper function.

## Implications

This workaround should be factored into the Extensibility assessment (B-4 stochastic
wrapping, B-5 interoperability) as context for the tool's design philosophy. PSI
trades single-period convenience for multi-period simulation capability.

---
tag: workaround-needed
source_dimension: extensibility
source_test: B-4
tool: gridcal
severity: medium
timestamp: 2026-03-06T02:00:00Z
---

# Observation: Stochastic wrapping works but requires snapshot OPF loop workaround

## Finding

GridCal accepts timeseries inputs programmatically via profile attributes (`P_prof`, `Pmax_prof`, etc.) and the scenario loop is clean Python code. However, the time-series OPF driver crashes on case39.m (TapPhaseControl bug), forcing a fallback to hour-by-hour snapshot OPF which loses inter-temporal constraints.

## Context

B-4 required 20 scenarios x 12 hours = 240 OPF solves. All converged successfully in 19.76s. Price and dispatch variation across scenarios was meaningful, demonstrating that the perturbation framework works. The workaround is classified as fragile because fixing the TapPhaseControl bug would allow proper multi-period OPF.

## Implications

The programmatic input API is good (no config files needed), but the inability to run multi-period OPF limits the value of the stochastic wrapper for applications requiring ramping or storage.

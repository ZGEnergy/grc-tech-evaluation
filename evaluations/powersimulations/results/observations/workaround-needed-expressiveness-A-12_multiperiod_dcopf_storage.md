---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-12
tool: powersimulations
severity: high
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: PSI v0.30.2 lacks storage device formulations

## Finding

PowerSimulations.jl v0.30.2 has no formulation for storage devices. `EnergyReservoirStorage`
exists as a data type in PowerSystems.jl but PSI cannot model it in a `DecisionModel`. Storage
had to be modeled entirely through manual JuMP variable/constraint injection.

## Context

A-12 tests 24-hour multi-period DCOPF with a 150 MW / 600 MWh BESS. The BESS was modeled by
adding JuMP variables (charge, discharge, SoC) and constraints (energy balance, cyclic SoC,
SoC bounds) directly to PSI's JuMP model, then injecting net BESS power into the nodal balance
constraints via `set_normalized_coefficient()`. This fragile workaround depends on PSI's
internal constraint naming conventions.

## Implications

This is a significant extensibility finding (B-suite). A production simulation framework that
cannot model storage natively requires users to build custom formulations at the JuMP level.
The workaround is version-specific -- PSI v0.31+ may add native storage support via
StorageSystemsSimulations.jl.

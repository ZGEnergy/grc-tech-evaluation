---
tag: formulation-difference
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: powersimulations
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: MATPOWER fallback precludes intermediate format field preservation

## Finding

PowerSystems.jl can only ingest the FNM via MATPOWER `.m` format, which merges
branches and transformers into a single table and discards PSS/E-specific fields
(switched shunt steps, transformer control modes, impedance correction tables, FACTS
devices, multi-section lines). This means any formulation differences observed in
downstream G-FNM-3/4 tests may be attributable to the MATPOWER intermediate format's
data loss rather than to the tool's formulation choices.

## Context

The intermediate CSV format preserves all 83 transformer columns from PSS/E v31,
separate branch and transformer tables, and all 17 record types. The MATPOWER fallback
collapses this to a single branch matrix with approximately 24 columns. PowerSystems.jl
re-separates branches into Line/Transformer2W/TapTransformer based on heuristics, but
the original PSS/E transformer control mode and winding detail are not available.

## Implications

When comparing G-FNM-3 (DCPF) and G-FNM-4 (ACPF) results against reference solutions,
any deviations at transformer-connected buses should be evaluated in the context of
MATPOWER format limitations, not solely attributed to PowerSimulations.jl's formulation
choices. The tool inherits PowerModels.jl's B-matrix formulation, which varies by
the chosen network model (DCPPowerModel uses simplified, DCMPPowerModel uses full).

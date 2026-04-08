---
tag: formulation-difference
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: powersimulations
severity: high
timestamp: "2026-03-24T18:30:00Z"
---

# Observation: Simplified B-matrix in PowerFlows.jl DCPF ignores transformer tap ratios

## Finding

PowerFlows.jl v0.9.0 DCPowerFlow uses a simplified B-matrix (`b = -1/x`) via
PowerNetworkMatrices.jl that ignores transformer tap ratios and phase shift angles. On
the ~28,000-bus FNM with ~2,340 off-nominal tap transformers, this produces systematic
angle deviations (mean 2.66 degrees, max 35.88 degrees) compared to MATPOWER's full
B-matrix reference. Branch flows are less affected (96.52% within 10% tolerance) because
flow errors depend on relative angle differences across each branch, which partially
cancel the global offset.

## Context

The FNM network has a high density of off-nominal tap transformers (2,340 of 2,358
transformers have tap != 1.0, ranging from 0.789 to 1.417). This amplifies the
formulation difference beyond what would be seen on networks with few transformers.
The simplified B-matrix approach is a deliberate design choice in PowerNetworkMatrices.jl,
not a bug. There is no configuration option to switch to a full B-matrix for DCPF.

## Implications

This formulation difference is inherent to the PowerFlows.jl/PowerNetworkMatrices.jl
architecture and affects all DCPF and PTDF-based analyses on networks with off-nominal
tap transformers. The Expressiveness and Scalability dimensions should note that DCPF
results from PowerSimulations.jl will systematically differ from MATPOWER on transformer-
heavy networks. This is classified as [tool-specific], not solver-specific, because it
stems from the B-matrix construction algorithm rather than the linear solver.

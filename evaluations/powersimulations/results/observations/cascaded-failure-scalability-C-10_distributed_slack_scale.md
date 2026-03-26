---
tag: cascaded-failure
source_dimension: scalability
source_test: C-10
tool: powersimulations
severity: high
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: C-10 Blocked by A-11 -- No Distributed Slack Formulation

## Finding

C-10 (distributed slack DC OPF at MEDIUM scale) is a cascaded failure from A-11 (distributed
slack DC OPF on TINY). PowerSimulations.jl and PowerModels.jl do not provide any distributed
slack formulation for DC OPF. All available DC formulations use a single reference bus:
- `DCPPowerModel`: single bus angle fixed to 0
- `PTDFPowerModel`: PTDF relative to single slack bus
- `CopperPlatePowerModel`: single-node aggregation

The `use_slacks` parameter on `PTDFPowerModel` controls constraint feasibility relaxation
(penalty slack variables), not distributed power balance. [tool-specific]

## Context

Without distributed slack at TINY scale, the capability cannot be tested at MEDIUM scale. A
manual JuMP-level reimplementation would be required, which goes beyond "workaround" into
custom formulation development.

## Implications

High severity. Distributed slack affects LMP accuracy in uncongested networks (all LMPs equal
marginal cost of the slack bus). This is a known limitation of the PSI/PowerModels formulation
library. The ACTIVSg10k network is uncongested in base-case DCOPF, so this limitation means
no LMP differentiation is possible at MEDIUM scale with PowerSimulations.jl.

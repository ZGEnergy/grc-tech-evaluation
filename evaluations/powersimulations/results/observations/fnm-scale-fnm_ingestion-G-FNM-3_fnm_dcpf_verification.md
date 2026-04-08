---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: powersimulations
severity: low
timestamp: "2026-03-24T18:30:00Z"
---

# Observation: PowerFlows.jl DCPF successfully handles ~28,000-bus network

## Finding

PowerFlows.jl DCPowerFlow solve completed in 10.70 seconds on the ~28,000-bus FNM main
island network with ~33,000 branches. Peak memory was 1,139.8 MB. The solve produced a
non-trivial solution (27,858 of ~28,000 buses with nonzero angles). Network loading via
PowerSystems.System took 38.11 seconds (includes JIT compilation overhead on cold start).

## Context

This was a MATPOWER fallback path (the `.m` file, not the intermediate CSV). The solve
completed within the 10-minute timeout budget. While the DCPF results deviate from the
MATPOWER reference due to the simplified B-matrix formulation, the tool demonstrated it
can load and solve large-scale networks without crashes or memory exhaustion.

## Implications

PowerFlows.jl is capable of handling LARGE-tier networks for DCPF. The scalability
dimension can reference this finding as evidence that the Sienna ecosystem handles
production-scale bus counts. Load time (38s) is dominated by MATPOWER parsing and JIT
compilation; subsequent solves in the same session would be faster.

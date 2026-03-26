---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-4
tool: powersimulations
severity: medium
timestamp: "2026-03-24T22:00:00Z"
---

# Observation: ACPF non-convergence on 28K-bus FNM network at all relaxation levels

## Finding

PowerFlows.jl's Newton-Raphson ACPF solver cannot converge on the 27,862-bus FNM
main island network with DCPF warm-start initialization and progressive branch rating
relaxation (0%, 10%, 20%). The solver ran 100 iterations at each level without
achieving convergence. Total ACPF wall-clock time across all three attempts was
approximately 81 seconds (33.8s + 18.5s + 28.8s). Peak memory was 1,727.5 MB.

## Context

This is consistent with the expected behavior for large-scale AC power flow in
open-source Newton-Raphson solvers without specialized multi-level initialization
heuristics. Contributing factors include the simplified B-matrix DCPF warm-start
(see formulation-difference observation from G-FNM-3), potential Q-limit interactions
from MATPOWER generator mapping, and the inherent difficulty of voltage-reactive power
convergence on networks with thousands of off-nominal-tap transformers. [tool-specific]

## Implications

For Phase 2 ACPF-based analyses on LARGE-tier networks, PowerSimulations.jl would
require either alternative solver methods (TrustRegion, LevenbergMarquardt, homotopy),
manual Q-limit relaxation, or a multi-step initialization strategy not currently
automated in PowerFlows.jl.

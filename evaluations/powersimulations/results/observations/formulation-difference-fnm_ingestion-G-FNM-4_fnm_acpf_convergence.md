---
tag: formulation-difference
source_dimension: fnm_ingestion
source_test: G-FNM-4
tool: powersimulations
severity: low
timestamp: "2026-03-24T22:00:00Z"
---

# Observation: Simplified B-matrix DCPF warm-start may degrade ACPF convergence

## Finding

The DCPF warm-start angles used for ACPF initialization in G-FNM-4 were computed
using PowerFlows.jl's simplified B-matrix (b = -1/x, ignoring transformer tap ratios).
As documented in the G-FNM-3 formulation-difference observation, this produces mean
angle deviations of approximately 2.7 degrees and maximum deviations of ~36 degrees
versus a full B-matrix reference on the ~28,000-bus FNM network with 2,340 off-nominal-
tap transformers.

## Context

The degraded warm-start quality is one of several contributing factors to ACPF
non-convergence (alongside network scale, Q-limit interactions, and the inherent
difficulty of large-network NR convergence). It is not possible to isolate the
warm-start quality contribution because PowerFlows.jl does not expose convergence
residuals that would enable comparison of convergence trajectories between different
initialization strategies.

## Implications

This is a secondary finding that reinforces the G-FNM-3 formulation-difference
observation. A full B-matrix DCPF warm-start might improve ACPF convergence prospects,
but the primary convergence barrier is likely the network scale and Q-limit handling
rather than the warm-start angle accuracy.

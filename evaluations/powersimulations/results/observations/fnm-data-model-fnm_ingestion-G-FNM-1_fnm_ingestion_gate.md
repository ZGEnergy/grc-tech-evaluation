---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: powersimulations
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: MATPOWER fallback component mapping loses PSS/E field fidelity

## Finding

When PowerSystems.jl loads via MATPOWER fallback (the only viable path since PSS/E
intermediate CSV and RAW parsing both fail), it provides reasonable component type
differentiation (Line vs Transformer2W vs TapTransformer) but all generators become
`ThermalStandard` and switched shunts become `FixedAdmittance`, losing discrete step
information and fuel type classification.

## Context

G-FNM-1 sub-check (a) failed because PowerSystems.jl has no parser for PSS/E-derived
intermediate CSV tables and its PSS/E RAW v31 parser fails on the Case Identification
header. The MATPOWER fallback loaded 27,862 buses (vs 30,307 in the full FNM) with
32,606 branches. The MATPOWER format merges branches and transformers into a single
table, though PowerSystems.jl re-separates them based on tap ratio heuristics.

## Implications

The data model obtained via MATPOWER fallback is sufficient for DCPF and DCOPF
verification (G-FNM-3, G-FNM-5) but may produce ACPF convergence differences due to
lost switched shunt discrete step information and the 2,445 missing isolated buses.
Field coverage audit (G-FNM-2) cannot be evaluated because the MATPOWER format does
not preserve the full PSS/E v31 field set.

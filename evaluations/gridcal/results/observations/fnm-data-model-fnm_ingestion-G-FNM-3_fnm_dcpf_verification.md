---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: gridcal
severity: medium
timestamp: 2026-03-13T00:00:00Z
---

# Observation: GridCal MATPOWER ingestion produces correct topology but large flow deviations on transformer-adjacent branches

## Finding

GridCal's MATPOWER loader correctly ingests 27,862 buses and 32,606 branches from
the cleaned FNM case file, and bus voltage angles match the reference MATPOWER DCPF
solution exactly (0.0 deg max deviation). However, 326 branches (1.0%) show extreme
flow deviations (up to 562,955%) concentrated on transformer-adjacent branches,
indicating the internal data model treats transformer tap ratios differently in the
DC B-matrix construction.

## Context

G-FNM-3 verified GridCal's DCPF solution against the MATPOWER reference on the
27,862-bus FNM main island. The MATPOWER fallback path was used because G-FNM-1
established that GridCal cannot ingest intermediate CSV tables. Bus angles match
perfectly, but branch flows on 326 branches (88.7% transformer-adjacent) diverge
by orders of magnitude. The flow magnitudes on affected branches reach hundreds of
thousands of MW, physically implausible for a transmission network with 165 GW total
load, suggesting the B-matrix susceptance entries for transformer branches use a
simplified formulation that omits tap ratio corrections.

## Implications

The data model correctly preserves bus topology, connectivity, and injection data
(as confirmed by perfect angle agreement). The transformer tap ratio handling in
the DCPF formulation is the specific limitation. This affects the Expressiveness
assessment for any DCPF-based analysis on networks with significant off-nominal
transformer taps. For the FNM ingestion dimension, this is classified as a
formulation difference (qualified_pass), not a data ingestion error.

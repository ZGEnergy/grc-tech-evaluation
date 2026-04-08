---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: gridcal
severity: medium
timestamp: 2026-03-24T00:00:00Z
---

# Observation: GridCal MATPOWER ingestion produces correct topology and injection data but simplified branch flow computation

## Finding

GridCal's MATPOWER loader correctly ingests ~28,000 buses and ~33,000 branches from
the cleaned FNM case file. Bus voltage angles match the reference MATPOWER DCPF
solution within machine precision (max deviation 7.713822e-09 deg). The v11 bus
injection power balance cross-reference confirms all ~28,000 bus load values match
the reference exactly (0 mismatches, max diff 0.000000e+00 MW). However, 326
branches (1.0%) show extreme flow deviations (up to 5.629550e+05%) concentrated
on transformer-adjacent branches, indicating the internal data model treats
transformer tap ratios differently in the DC B-matrix construction.

## Context

G-FNM-3 verified GridCal's DCPF solution against the MATPOWER reference on the
~28,000-bus FNM main island. The MATPOWER fallback path was used because G-FNM-1
established that GridCal cannot ingest intermediate CSV tables. Total generation
is ~156,000 MW and total load is ~165,000 MW, with the -9,981 MW imbalance absorbed
by the slack bus. The perfect load match confirms the injection vector is correctly
ingested; the formulation difference is isolated to the branch flow computation.

## Implications

The data model correctly preserves bus topology, connectivity, and injection data
(as confirmed by perfect angle agreement and zero load deviation). The transformer
tap ratio handling in the DCPF formulation is the specific limitation. This affects
the Expressiveness assessment for any DCPF-based analysis on networks with
significant off-nominal transformer taps. For the FNM ingestion dimension, this is
classified as a formulation difference (qualified_pass), not a data ingestion error.

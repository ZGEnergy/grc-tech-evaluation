---
tag: formulation-difference
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: pandapower
severity: medium
timestamp: 2026-03-14T04:00:00Z
---

# Observation: Localized DCPF deviations not classifiable as formulation difference

## Finding

pandapower's DCPF on the FNM main island produces 101 bus angle outliers (deviations
of 14-21 degrees) concentrated in a connected sub-region of the 138/69/34.5 kV
subtransmission network. The outlier buses have 0% transformer adjacency, ruling
out classification as a formulation difference. The deviations are classified as
data_ingestion_error per the formulation difference classification protocol.

## Context

G-FNM-3 compared pandapower's DCPF solution against the MATPOWER reference on
27,862 buses. Aggregate performance is strong (99.64% bus pass rate, 99.67% branch
pass rate), but the hard-fail condition is triggered by a maximum branch flow
deviation of 596.6% on a single branch (14102->48022). The affected buses form a
radial cluster with zero load and zero generation, where small impedance handling
differences cause large angle errors that cascade through the local topology.

## Implications

The failure is attributable to localized data handling differences in the PPC
import path, not to pandapower's B-matrix construction or DCPF solver. This
finding is relevant to the expressiveness and scalability dimensions: pandapower's
DCPF is fundamentally sound but its MATPOWER import path introduces small
discrepancies that are amplified in weakly-connected radial sub-networks.

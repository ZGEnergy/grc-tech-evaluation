---
tag: formulation-difference
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: pypsa
severity: high
timestamp: 2026-03-13T00:00:00Z
---

# Observation: PyPSA-MATPOWER DCPF deviation pattern suggests data ingestion issue, not formulation difference

## Finding

The DCPF deviations between PyPSA and MATPOWER on the 27,862-bus FNM are NOT consistent
with the expected formulation-difference pattern. Both tools use full B-matrix construction
(incorporating tap ratios), yet deviations are uniform across all voltage tiers and bus types.
A formulation sophistication difference (simplified vs full B-matrix) would concentrate
deviations at transformer-connected buses with non-unity taps.

The uniform deviation pattern (mean 3.63-4.18 deg across all voltage tiers) with a
systematic -1.3 degree signed bias suggests the `import_from_pypower_ppc` conversion path
introduces impedance parameter differences that affect the B-matrix globally.

## Context

The transformer flow deviations (mean 35.5%, max 87,054%) are significantly higher than
line deviations (mean 11.6%, max 52,032%), which does suggest transformer-related issues.
However, the bus angle deviations do not cluster near transformers -- they are spread
uniformly, indicating the impedance mapping affects the entire network's angle solution
through the coupled B-matrix system.

With 9,481 transformers (34% of all branches) and 2,358 having non-unity taps, even small
per-transformer impedance mapping errors propagate throughout the network.

## Implications

This finding should be considered when interpreting G-FNM-3 results across tools. If other
Python tools (pandapower, GridCal) also use `import_from_pypower_ppc` or similar PPC
conversion paths, they may exhibit similar deviation patterns. Tools with native MATPOWER
file readers (pandapower's `from_mpc`) may show better agreement with the reference.

---
tag: formulation-difference
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: pypsa
severity: low
timestamp: 2026-03-24T00:00:00Z
---

# Observation: No formulation difference -- PyPSA DCPF matches MATPOWER at machine precision after branch status fix

## Finding

PyPSA's DCPF solution (`n.lpf()`) produces deviations at float64 machine-precision level
from the MATPOWER reference on the 27,862-bus FNM main island when loaded via the shared
`matpower_loader.load_pypsa()`. Max bus angle deviation: 1.073352e-08 degrees. Max branch
flow deviation: 5.757744e-07 %. 100% of buses and 100% of branches pass all thresholds.
Both tools use the same B-matrix formulation.

## Context

The network contains 9,481 transformers, of which 2,358 have tap ratios != 1.0 (range
[0.7894, 1.4165]). Despite this significant transformer population with off-nominal taps,
no systematic formulation difference is observed. PyPSA's `calculate_B_H` and MATPOWER's
`makeBdc.m` produce equivalent B-matrix constructions when the branch status patch is
applied.

Bus injection power balance was verified on all 27,862 non-excluded buses using post-solve
generator dispatch values. Maximum bus mismatch: 1.317039e-07 MW. All buses balanced
within 1.000000e-03 MW tolerance.

## Implications

No formulation difference exists between PyPSA and MATPOWER for DCPF on this network.
The `import_from_pypower_ppc` branch status bug is documented in the shared
`matpower_loader` and workaround-classified as `stable`. The previous v10 result reported
"0.0" deviations due to display rounding; the v11 result uses scientific notation to
correctly show the float64 numerical noise floor.

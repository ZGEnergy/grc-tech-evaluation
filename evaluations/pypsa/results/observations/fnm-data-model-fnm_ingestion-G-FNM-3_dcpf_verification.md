---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: pypsa
severity: medium
timestamp: 2026-03-24T00:00:00Z
---

# Observation: import_from_pypower_ppc ignores MATPOWER branch status -- fixed by shared loader

## Finding

PyPSA's `import_from_pypower_ppc` imports the MATPOWER `BR_STATUS` column as a custom
`status` attribute on the Lines and Transformers DataFrames but does NOT map it to PyPSA's
`active` flag. All branches are treated as active regardless of their MATPOWER status.
On the ~28,000-bus FNM, this means 74 inactive branches (69 lines, 5 transformers)
participate in the DCPF B-matrix when they should be excluded.

## Context

This bug caused the original G-FNM-3 (v10) to fail with 91% bus angle failures and 87,054%
max branch flow deviation. After applying the shared `matpower_loader.load_pypsa()`
which includes a branch status patch (`active = False` for branches with `status == 0`),
G-FNM-3 passes with deviations at float64 machine-precision level (max bus angle
deviation: 1.073352e-08 deg, max branch flow deviation: 5.757744e-07 %).

The `import_from_pypower_ppc` warning -- "Note that when importing from PYPOWER, some
PYPOWER features not supported: areas, gencosts, component status" -- documents this
limitation but is easy to overlook. The shared loader addresses it deterministically.

## Implications

Any PyPSA evaluation using MATPOWER case files with inactive branches MUST use the
shared `matpower_loader.load_pypsa()` rather than raw `import_from_pypower_ppc`. This
affects Suite A/B/C tests as well, though the standard test cases (case39, ACTIVSg2k,
ACTIVSg10k) typically have all branches active, so the bug is only triggered on networks
with explicitly deactivated branches like the FNM.

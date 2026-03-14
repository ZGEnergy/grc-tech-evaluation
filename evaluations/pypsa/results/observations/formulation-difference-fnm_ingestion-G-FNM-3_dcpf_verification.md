---
tag: formulation-difference
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: pypsa
severity: low
timestamp: 2026-03-13T00:00:00Z
---

# Observation: No formulation difference — PyPSA DCPF matches MATPOWER exactly after branch status fix

## Finding

PyPSA's DCPF solution (`n.lpf()`) produces **zero deviation** from the MATPOWER reference
on the 27,862-bus FNM main island when loaded via the shared `matpower_loader.load_pypsa()`.
100% of buses and 100% of branches match exactly. Both tools use the same B-matrix
formulation: `b = 1/(x * tap)` (MATPOWER's `makeBdc.m` and PyPSA's `calculate_B_H` are
equivalent).

## Context

The original G-FNM-3 run (without the shared loader) showed 91% bus angle failures and
87,054% max branch flow deviation. Investigation identified the root cause as
`import_from_pypower_ppc` ignoring MATPOWER's `BR_STATUS` column — 74 inactive branches
were included in the DCPF, distorting the B-matrix globally. The shared loader adds a
branch-status patch that correctly deactivates these branches.

The `b = 1/x` transformer susceptance patch in the loader has no effect on DCPF results
because PyPSA's `calculate_B_H` recomputes susceptance from `x_pu_eff` internally,
bypassing the `b` attribute. The formulations are identical; the deviation was purely a
data import issue.

## Implications

No formulation difference exists between PyPSA and MATPOWER for DCPF on this network.
The `import_from_pypower_ppc` branch status bug is documented in the shared
`matpower_loader` and workaround-classified as `stable`. Tools that bypass this function
(e.g., pandapower's native `from_mpc`) would not be affected.

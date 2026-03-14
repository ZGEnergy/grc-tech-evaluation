---
tag: convergence-quality
source_dimension: expressiveness
source_test: A-11
tool: pypsa
severity: medium
timestamp: 2026-03-13T00:00:00Z
---

# Observation: Shared loader transformer susceptance patch breaks AC PF convergence

## Finding

The shared `matpower_loader.load_pypsa()` applies a transformer susceptance correction (`b = 1/x` instead of PyPSA's default `b = 1/(x*tap)`) that is correct for DC power flow but produces an incorrect AC admittance matrix. AC PF (`n.pf()`) diverges catastrophically when using the shared loader on case39 (error 2.4e42 after 100 iterations), but converges in 4 iterations (error 3.3e-09) with the raw `import_from_pypower_ppc` loader.

## Context

Test A-11 needed AC PF with distributed slack to demonstrate the capability. The shared loader's Patch 1 (transformer susceptance) overwrites each transformer's `b` attribute to `1/x`, which is the DC-PF convention (ignoring tap ratio). In AC PF, the admittance matrix requires the full `1/(x*tap)` susceptance including the tap ratio to construct the correct Y-bus. The 11 transformers in case39 have tap ratios ranging from 1.006 to 1.070, so the susceptance error is 0.6-7% per transformer -- enough to prevent convergence.

## Implications

This affects any test combining AC PF with the shared loader. Tests A-2 (ACPF), A-4 (AC feasibility), and any future AC OPF tests should either use the raw `import_from_pypower_ppc` loader or undo the transformer susceptance patch before running AC analysis. The patch should be documented as DC-PF-only in `LOADING_NOTES.md`.

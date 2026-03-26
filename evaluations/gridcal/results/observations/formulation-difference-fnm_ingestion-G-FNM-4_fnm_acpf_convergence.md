---
tag: formulation-difference
source_dimension: fnm_ingestion
source_test: G-FNM-4
tool: gridcal
severity: medium
timestamp: 2026-03-24T00:00:00Z
---

# Observation: MATPOWER fallback path loses ACPF-critical fields, potentially contributing to convergence failure

## Finding

GridCal's ACPF solver fails to converge on the 27,862-bus FNM main island loaded
via MATPOWER `.m` fallback. The MATPOWER format flattens transformer data and loses
ACPF-critical fields (tap control modes, winding impedance detail, switched shunt
discrete steps), which may contribute to the convergence failure. This represents a
formulation-level difference between the MATPOWER-ingested model and the original
PSS/e network model.

## Context

G-FNM-4 tested ACPF convergence with DCPF warm-start and progressive branch rate
relaxation (0%, 10%, 20%) using four solver algorithms (NR, NR+controls, LM, HELM).
All 12 combinations failed. The best result (Levenberg-Marquardt, 200 iterations)
achieved a residual of 1.583e+01, far from the 1e-6 tolerance. The MATPOWER
reference ACPF solution exists (buses_acpf.csv with 27,862 entries), confirming the
network is solvable with appropriate data fidelity.

Key ACPF-critical fields lost in MATPOWER fallback:
- Transformer tap control modes (CW, CZ, CM fields)
- Switched shunt discrete steps (BINIT, N1..N8, B1..B8)
- Generator Q-limit interpretation nuances
- Multi-winding transformer impedance detail

## Implications

The ACPF failure cannot be definitively attributed to either the solver or the data
path without testing GridCal's ACPF on the same network loaded via its native PSS/e
`.raw` parser (which GridCal supports for v29-35). Tools that converge ACPF on the
MATPOWER-format FNM may have more robust NR implementations or different default
Q-limit handling. This finding is relevant to cross-tool ACPF comparisons: tools
using the same MATPOWER input should be compared against each other, not against
tools using richer input formats. [mixed: data path fidelity + solver robustness]

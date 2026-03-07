---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-10
tool: pandapower
severity: high
timestamp: 2026-03-06T00:00:00Z
---

# Observation: pandapower has no lossy DC OPF or LMP decomposition

## Finding

pandapower's `rundcopp()` is inherently lossless. No parameter enables loss approximation in the DC OPF. LMP decomposition into energy, congestion, and loss components is not available in any OPF formulation (neither `rundcopp` nor `runopp`).

## Context

Test A-10 required lossy DC OPF with LMP decomposition and per-line congestion rent reconciliation. The lossless DC OPF produced uniform LMPs (13.517 across all buses), indicating no congestion on this network. AC OPF (`runopp`) was tested as a comparison: it converged with a 1.47% higher objective and non-uniform LMPs (std 0.187), confirming that losses do affect prices. However, AC OPF is not a DC formulation and still does not provide LMP decomposition. Only `lam_p` and `lam_q` columns are available -- no energy/congestion/loss breakdown.

## Implications

This is a significant gap for market simulation applications where LMP decomposition is essential for understanding price formation. For the accessibility evaluation, pandapower's documentation does not claim these capabilities, so the gap is at least transparent. For extensibility, adding lossy DC OPF would require modifying the PYPOWER solver formulation.

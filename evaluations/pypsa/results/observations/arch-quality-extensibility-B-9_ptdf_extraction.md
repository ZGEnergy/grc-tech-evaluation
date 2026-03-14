---
tag: arch-quality
source_dimension: extensibility
source_test: B-9
tool: pypsa
severity: low
timestamp: 2026-03-13T00:00:00Z
---

# Observation: Native PTDF API with machine-precision flow predictions

## Finding

PyPSA's `sub_network.calculate_PTDF()` provides a clean 3-step native API for PTDF matrix extraction. Flow predictions match DCPF results to machine precision (max error 1.91e-14 pu, 8 orders of magnitude below the 1e-6 tolerance). The PTDF matrix is a dense numpy array (branches x buses), directly usable for sensitivity analysis without format conversion.

## Context

The B-9 test computed the 46x39 PTDF matrix for case39 and validated against DCPF flows. The main non-obvious detail is that PTDF columns follow `sn.buses_o` order (slack-first), not `n.buses` alphabetical order. This is consistent with the SubNetwork's internal conventions but could trip users who assume alphabetical bus ordering.

## Implications

For maturity assessment: the PTDF API is well-implemented and numerically robust. The bus ordering convention is consistent but could benefit from clearer documentation. The dense matrix format may become a memory concern for large networks (e.g., 10k+ buses would produce a ~1.5 GB matrix).

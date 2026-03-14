---
tag: arch-quality
source_dimension: extensibility
source_test: B-6
tool: pypsa
severity: low
timestamp: 2026-03-13T00:00:00Z
---

# Observation: Well-separated architecture with 4 layers and 8 mixins

## Finding

PyPSA v1.1.2 has a clean 4-layer architecture (User API -> Mixin Dispatch ->
SubNetwork Computation -> Linear Algebra Backend) with good separation of concerns.
The OPF path has explicit model-build/solve separation via linopy. The PF path
combines build and solve in one call but exposes intermediate matrices (B, H, PTDF)
via public attributes.

## Context

B-6 traced the DCPF call chain from `n.lpf()` through `SubNetworkPowerFlowMixin.lpf()`
to `scipy.sparse.linalg.spsolve()`. The Network class is composed of 8 mixins with
a 12-class inheritance chain. Five documented injection points exist for extending behavior.

Two architectural weaknesses noted: (1) the mixin composition pattern is not documented,
making method discovery harder for new users; (2) the DCPF solver backend (scipy.sparse)
is hardcoded with no parameter to swap it.

## Implications

The architecture quality is a positive signal for maturity assessment. The clean
separation of data model (pandas DataFrames) from formulation (power_flow.py) and
solver (linopy/scipy) indicates mature software engineering. The undocumented mixin
architecture is a minor accessibility concern — users reading docs.pypsa.org would
not discover the internal layering without reading source code.

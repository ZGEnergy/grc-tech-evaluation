---
tag: doc-gaps
source_dimension: extensibility
source_test: B-6
tool: pypsa
severity: low
timestamp: 2026-03-13T00:00:00Z
---

# Observation: Mixin architecture and SubNetwork API underdocumented

## Finding

PyPSA's Network class is composed of 8 mixins (NetworkComponentsMixin,
NetworkPowerFlowMixin, NetworkGraphMixin, etc.), but this composition pattern is not
documented in the user guide. The SubNetwork-level methods (calculate_B_H, calculate_PTDF,
calculate_Y) are docstring-documented but not featured in the user-facing documentation.

## Context

During B-6 architecture tracing, the 12-class inheritance chain and 8 mixin classes were discovered
only through `inspect` and source code reading. The official docs at docs.pypsa.org
document top-level methods (lpf, pf, optimize) but do not explain the internal layering
or how to access SubNetwork-level computation (e.g., extracting the B-matrix directly).

## Implications

This is a minor accessibility finding. Advanced users who need to access intermediate
computational artifacts (B-matrix, PTDF, Y-bus) or understand method dispatch must read
source code. This does not affect standard usage patterns but increases the learning
curve for power-system researchers who need to build custom analyses on top of PyPSA's
internal matrices.

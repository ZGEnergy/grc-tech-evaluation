---
tag: doc-gaps
source_dimension: extensibility
source_test: B-9
tool: pypsa
severity: low
timestamp: 2026-03-13T00:00:00Z
---

# Observation: PTDF column ordering requires reading source code to discover

## Finding

The PTDF matrix columns follow `sub_network.buses_o` order (slack bus first, then pvpq buses), not the more intuitive `n.buses.index` alphabetical order. Using the wrong bus ordering produces incorrect flow predictions. This ordering convention is not prominently documented in the PyPSA user documentation; it must be discovered by reading the source code or through trial and error.

## Context

During B-9 (PTDF extraction), the injection vector had to be assembled in `sn.buses_o` order for `PTDF @ P_inj` to produce correct results. The v9 test script already documented this finding. The convention is internally consistent (SubNetwork uses this ordering throughout), but new users would likely assemble injections in `n.buses.index` order first and get wrong results.

## Implications

For accessibility assessment: this is a minor but reproducible documentation gap. Users attempting PTDF-based analysis will need to discover the bus ordering convention, which adds friction to the first use. A note in the `calculate_PTDF()` docstring or user guide would address this.

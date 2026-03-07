---
tag: doc-gaps
source_dimension: extensibility
source_test: B-9
tool: pypsa
severity: medium
timestamp: 2026-03-06T00:00:00Z
---

# Observation: PTDF column ordering undocumented

## Finding

The `SubNetwork.calculate_PTDF()` method produces a PTDF matrix whose column ordering
is `[slack_bus] + list(sn.pvpqs)`, which differs from `sn.buses_i()`. This ordering
is not documented in the API reference or examples. Using `buses_i()` ordering for the
injection vector produces completely wrong flow predictions (errors >1000 MW on a 39-bus
network).

## Context

During B-9 (PTDF Extraction), the initial implementation used `sn.buses_i()` to order
the injection vector. This produced a max flow prediction error of 1442 MW. Reading the
`calculate_PTDF` source revealed that the B matrix inverse is constructed with the slack
bus at index 0, followed by pvpqs buses. Reordering injections to match produced exact
agreement (max diff 1.88e-12).

## Implications

This is a meaningful documentation gap that would trip up users computing PTDF-based
analyses. The accessibility audit (D-4) should note that PTDF usage requires reading
source code to determine the correct bus ordering. The `calculate_PTDF` docstring says
only "Calculate the PTDF" with no mention of the column ordering convention.

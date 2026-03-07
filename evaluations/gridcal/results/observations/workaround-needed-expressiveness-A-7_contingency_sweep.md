---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-7
tool: gridcal
severity: low
timestamp: 2026-03-06T01:00:00Z
---

# Observation: N-M contingency requires manual loop (stable workaround)

## Finding

GridCal's `ContingencyAnalysisDriver` handles pre-defined N-1 contingency groups only. Arbitrary N-M sweeps with graph-distance scoping and pruning require a manual loop using `branch.active` toggle and `vge.power_flow()`.

## Context

A-7 required N-M (m=3) contingency sweep with graph-distance enumeration and pruning. The workaround uses public API (branch.active, build_graph() → NetworkX) and is classified as stable.

## Implications

The workaround is clean but documents that GridCal's built-in contingency analysis is N-1 only. Relevant to extensibility grading.

---
tag: api-friction
source_dimension: extensibility
source_test: B-2
tool: pypsa
severity: low
timestamp: 2026-03-06T00:00:00Z
---

# Observation: Graph access is zero-friction -- n.graph() returns standard NetworkX

## Finding

PyPSA's `n.graph()` returns a `networkx.MultiGraph` subclass (`OrderedGraph`),
enabling direct use of the entire NetworkX algorithm library (BFS, DFS, shortest
path, centrality, community detection, etc.) with no conversion or adaptation.
This is the lowest-friction graph access pattern observed.

## Context

Test B-2 required BFS to depth 3 from a chosen bus and subgraph extraction. The
entire operation required 4 lines of code beyond network loading, all using
standard NetworkX functions. No workaround, no custom code, no data extraction
needed.

## Implications

For Accessibility assessment: this is a positive finding. Users familiar with
NetworkX can immediately apply graph algorithms to PyPSA networks. The API is
discoverable and well-documented. This should be noted as a strength in the
Accessibility dimension.

---
tag: arch-quality
source_dimension: extensibility
source_test: B-3
tool: pandapower
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: pandapower's DataFrame-backed network model enables clean in-place contingency toggling

## Finding

pandapower's architecture -- where the network model is stored as pandas DataFrames with an `in_service` column per element type -- enables N-M contingency sweeps via simple column toggling without model reconstruction. Combined with the `create_nxgraph()` bridge to NetworkX, graph-distance pruning is clean and idiomatic.

## Context

B-3 performed 3,276 N-3 contingency cases by toggling `net.line.at[idx, 'in_service']` and re-running `rundcpp()`. pandapower rebuilds the internal PYPOWER bus-branch model from DataFrames on each solve, but the user-facing network object persists. This is architecturally clean: the user modifies DataFrames, and pandapower handles internal model updates transparently.

## Implications

This is a positive architecture observation. The DataFrame-backed design, combined with the topology module (`unsupplied_buses`, `create_nxgraph`), makes pandapower well-suited for contingency analysis workflows. The built-in `run_contingency()` only supports N-1, but the manual N-M pattern is straightforward. This should be noted in the Maturity assessment as evidence of good extensibility architecture.

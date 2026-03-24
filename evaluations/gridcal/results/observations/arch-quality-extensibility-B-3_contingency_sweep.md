---
tag: arch-quality
source_dimension: extensibility
source_test: B-3
tool: gridcal
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Clean branch toggling API for contingency analysis

## Finding

GridCal provides a simple `branch.active` boolean property that removes branches from the power flow solve without requiring model reconstruction. Combined with `build_graph()` for NetworkX export, this enables efficient N-M contingency sweeps (377 DCPF solves at ~4.9 ms each).

## Context

During B-3 contingency sweep testing, each contingency was solved by toggling `branch.active = False` on outaged branches, solving DCPF, then restoring. The internal `NumericalCircuit` is recompiled on each `power_flow()` call, but this recompilation is lightweight (sub-millisecond) and does not require user intervention.

## Implications

This pattern is simpler than tools requiring explicit contingency group objects or model cloning. The architecture enables ad-hoc contingency studies without learning a specialized contingency API. However, for very large-scale studies, the per-solve recompilation overhead may become significant compared to LODF-based analytical approaches (which GridCal also supports via `ContingencyAnalysisDriver`).

---
tag: arch-quality
source_dimension: extensibility
source_test: B-3
tool: matpower
severity: low
timestamp: 2026-03-13T00:00:00Z
---

# Observation: MATPOWER's flat data model enables low-friction contingency analysis

## Finding

MATPOWER's flat matrix data model (`mpc.branch`, `mpc.gen`) with named column constants (`F_BUS`, `T_BUS`, `BR_STATUS`) allows in-place branch status toggling for contingency analysis without model reconstruction. Combined with native `makePTDF()`/`makeLODF()` functions and `find_islands()`, the tool provides all building blocks for N-M contingency sweeps with minimal API friction.

## Context

B-3 implemented an escalating N-1/N-2/N-3 contingency sweep with LODF-based screening and graph-distance pruning. The entire sweep (155 contingencies) ran in 3.5 seconds on TINY. Branch outages were applied by setting `mpc.branch(idx, BR_STATUS) = 0` — a single field assignment. No model reconstruction or re-initialization was needed between contingencies.

## Implications

This is a positive architecture finding for the maturity dimension. The flat, transparent data model trades object-oriented elegance for directness and inspectability. For power systems analysis workflows that require iterative network modifications (contingency analysis, topology optimization), this pattern minimizes boilerplate compared to tools that encapsulate network state in opaque objects.

---
tag: workaround-needed
source_dimension: p2_readiness
source_test: P2-3
tool: pandapower
severity: medium
timestamp: 2026-03-06T00:00:00Z
---

# Observation: PYPOWER solver diverges when generators set out of service

## Finding

Setting `net.gen.at[idx, "in_service"] = False` causes the PYPOWER interior point OPF solver to diverge numerically on IEEE case39. The solver produces lambda/dual values on the order of 1e25, indicating complete numerical instability. The workaround is to set `max_p_mw=0` and `min_p_mw=0` instead, which achieves the same dispatch effect while keeping the generator in the solver's variable set.

## Context

Discovered during P2-3 commitment injection testing. Even decommitting a single generator via `in_service=False` caused OPF divergence. The DCPF (non-optimization) power flow converges fine with decommitted generators. The issue is specific to the OPF's interior point solver.

Additionally, not all generators can be decommitted via the `max_p_mw=0` approach -- the solver is sensitive to which specific generator is decommitted, suggesting fragility in the problem formulation or solver initialization when the feasible region geometry changes.

## Implications

This is relevant for the extensibility and scalability assessments. The PYPOWER interior point solver's fragility limits pandapower's ability to handle generator commitment changes robustly. For production use cases involving commitment schedules (e.g., SCUC -> SCED pipelines), this numerical instability could be a significant barrier. The PowerModels.jl bridge (using HiGHS or other solvers) would likely handle this case more robustly.

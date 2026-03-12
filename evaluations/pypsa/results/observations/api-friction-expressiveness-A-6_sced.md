---
tag: api-friction
source_dimension: expressiveness
source_test: A-6
tool: pypsa
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: No first-class API to fix UC commitment and re-solve ED as LP

## Finding

PyPSA has no `fix_commitment()` or equivalent convenience method to freeze a UC binary solution and re-dispatch as a pure LP. The two-stage SCED workflow requires manually translating `n.generators_t.status` into time-varying `p_min_pu`/`p_max_pu` bounds after setting `committable=False`.

## Context

Discovered during A-6 (SCED): to demonstrate cleanly separable UC+ED stages, the test ran Stage 1 as MILP (`committable=True`), extracted the 24×10 commitment schedule from `n.generators_t.status`, then constructed a fresh network for Stage 2 where each decommitted generator-hour had `p_max_pu=0` (forced off) and `committable=False` (no binary variables). The `n.optimize.fix_optimal_capacities()` method does not serve this purpose — it fixes generator nameplate capacity (p_nom), not the per-hour commitment schedule. There is also no `fix_optimal_dispatch()` for this use case.

## Implications

- **Accessibility (D-2):** The documentation does not describe how to perform a two-stage UC+ED workflow. Users implementing SCED must discover the `generators_t.p_min_pu` / `p_max_pu` workaround from source examples or GitHub discussions. This is a doc-gap risk.
- **Extensibility:** The absence of a `fix_commitment()` utility makes it slightly harder to build rolling-horizon UC+SCED pipelines that alternate between MILP and LP solves. The workaround is stable and low-effort (~10 lines), so grade impact is minor.
- The workaround itself is classified as **stable** (documented public API, natural PyPSA idiom), but the missing convenience method is a legitimate API friction point worth tracking.

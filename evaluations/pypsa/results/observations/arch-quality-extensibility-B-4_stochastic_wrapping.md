---
tag: arch-quality
source_dimension: extensibility
source_test: B-4
tool: pypsa
severity: low
timestamp: 2026-03-06T00:00:00Z
---

# Observation: Clean programmatic scenario loop via n.copy() + DataFrame assignment

## Finding

PyPSA's `n.copy()` + direct pandas DataFrame assignment pattern makes stochastic
scenario loops clean and efficient. 20 scenarios with 12-hour multi-period DCOPF
completed in ~10 seconds total (~0.39 s/scenario) with no per-scenario overhead
beyond the copy itself.

## Context

Test B-4 required running 20 scenarios with correlated load/renewable perturbations.
The pattern is: clone the base network, update time-varying DataFrames
(`loads_t.p_set`, `generators_t.p_max_pu`), solve, collect results. No configuration
files, no model reconstruction, no special scenario management API needed.

## Implications

This is a positive architectural finding. The DataFrame-centric data model makes
programmatic manipulation natural for Python users. The pattern should be noted in
the Accessibility assessment as evidence of low API friction for common workflows.
One caveat: `n.copy()` cannot be called on a solved network with an attached solver
model -- users must clear it first via `n.model.solver_model = None`.

---
tag: arch-quality
source_dimension: extensibility
source_test: B-1
tool: pypsa
severity: low
timestamp: 2026-03-06T00:00:00Z
---

# Observation: Clean custom constraint API via Linopy model split

## Finding

PyPSA provides a well-designed extension mechanism for custom constraints through the
`create_model()` / `solve_model()` split. Users access the Linopy model object at
`n.model`, use xarray-style coordinate selection (`m["Line-s"].sel(name="L0")`), and
add constraints with `m.add_constraints()`. Custom constraint duals are accessible via
`m.dual["constraint_name"]`. The entire workflow requires only 2-3 lines of user code.

## Context

During B-1 (Custom Constraints), a flow gate constraint was added to the DC OPF in 2
lines of code. The `assign_all_duals=True` parameter in `solve_model()` enables dual
extraction for both built-in and custom constraints. The Linopy model provides a clean,
composable interface for building linear expressions from optimization variables.

## Implications

This is a positive architectural finding. The Linopy-based model interface is well-designed
for extensibility. The `create_model()`/`solve_model()` split is a documented public API
pattern. This should be noted as a strength in the extensibility and maturity assessments.
The `extra_functionality` callback provides an alternative (single-call) path for the
same use case, though it runs after model creation and before solve within `n.optimize()`.

# Observation: No Custom Constraint API in GridCal OPF

**Test:** B-1 (Custom Constraints)
**Dimension:** extensibility
**Severity:** blocking

## Finding

GridCal's DC OPF formulation (via PuLP) does not expose any API for adding custom linear constraints. The LP model is constructed internally and not accessible to users.

## Impact

- Cannot add flow gate limits spanning multiple branches (interface limits)
- Cannot add generator group constraints (e.g., zonal reserve requirements)
- Cannot add arbitrary linear constraints to the OPF
- Cannot extract per-constraint dual values (only nodal LMPs available)

## Workaround Attempted

Branch `rate` modification can simulate single-branch flow limits, but this reuses the existing built-in constraint mechanism rather than adding new constraints. It cannot express multi-branch interfaces or non-branch constraints.

## API Evidence

- No methods containing "constraint" or "limit" on the grid object
- `BranchGroup` class exists but is not wired into the OPF formulation
- OPF results object has no reference to the underlying PuLP model
- Only `bus_shadow_prices` (nodal LMPs) available -- no per-branch or per-constraint duals

## Contrast

Tools like PowerModels.jl and PyPSA expose the optimization model directly, allowing users to add constraints via JuMP or Pyomo/linopy before solving.

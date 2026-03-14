---
tag: api-friction
source_dimension: extensibility
source_test: B-1
tool: pandapower
severity: high
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: Custom OPF constraint injection requires replicating internal functions

## Finding

Adding custom linear constraints to pandapower's DC OPF requires replicating the internal `_optimal_powerflow` function and monkey-patching `pandapower.run._optimal_powerflow`. The PYPOWER `userfcn` callback mechanism exists and works correctly, but pandapower does not expose it in its public API. Additionally, constraint duals are discarded during result extraction and must be captured by intercepting the PYPOWER result dict before pandapower processes it.

## Context

Test B-1 required adding a flow gate constraint (PTDF-based linear constraint on branch flow) to the DC OPF. The constraint was successfully injected via `add_userfcn('formulation', callback)` where the callback uses `om.add_constraints()`. However:

1. `add_userfcn` is only called internally when dclines are present; there is no public API to register user callbacks.
2. The `_optimal_powerflow` function is private (underscore-prefixed) and undocumented.
3. Constraint duals (`result['lin']['mu']`) are available in the PYPOWER result dict but discarded by pandapower's `_extract_results` before populating `net.res_*` DataFrames.

## Implications

This finding is relevant to Accessibility (documentation completeness) and Maturity (API design quality). The PYPOWER userfcn system is powerful and well-documented in PYPOWER's own codebase, but pandapower's abstraction layer hides it without providing an equivalent. Users who need custom constraints must understand pandapower's internal OPF pipeline architecture to inject callbacks.

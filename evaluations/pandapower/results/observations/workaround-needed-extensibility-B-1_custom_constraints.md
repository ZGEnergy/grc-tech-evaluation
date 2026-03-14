---
tag: workaround-needed
source_dimension: extensibility
source_test: B-1
tool: pandapower
severity: high
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: Custom OPF constraints require fragile workaround

## Finding

Injecting custom linear constraints into pandapower's DC OPF and extracting their dual values requires a fragile workaround: replicating the private `_optimal_powerflow` function, monkey-patching `pandapower.run._optimal_powerflow`, and capturing the PYPOWER result dict before pandapower discards the constraint duals. Classified as fragile because it depends on the internal structure of an undocumented private function.

## Context

The workaround was necessary because: (1) pandapower does not expose the PYPOWER `add_userfcn` mechanism in its public API, (2) the `_optimal_powerflow` function only calls `add_userfcn` when dclines are present, and (3) constraint duals from `result['lin']['mu']` are discarded during `_extract_results`. The constraint itself works correctly via PYPOWER's `om.add_constraints()` once the callback is properly injected.

## Implications

This finding directly affects the extensibility grade. The workaround is classified as fragile because it depends on undocumented internals that could change in any minor version update. However, the underlying PYPOWER mechanism is architecturally sound and has been stable for years.

---
tag: arch-quality
source_dimension: extensibility
source_test: B-6
tool: pandapower
severity: medium
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: pandapower has clean 6-layer architecture but OPF duals are discarded

## Finding

pandapower's DCPF solve path has 6 well-separated abstraction layers (public API, orchestration, data model conversion, problem formulation, solver, result extraction). However, the result extraction layer discards the PYPOWER OPF result dictionary containing constraint duals and multipliers, making dual extraction require internal API access.

## Context

During B-6 code architecture audit, tracing the solve path revealed that `_extract_results` in `pandapower.results` maps PYPOWER arrays back to pandas DataFrames but drops `result['lin']['mu']`, `result['var']`, and other solver output that contains shadow prices and constraint multipliers. This was independently confirmed in B-1 (custom constraints), where extracting flow gate duals required monkey-patching `_optimal_powerflow` to capture the PYPOWER result dict before it was discarded.

## Implications

This architectural gap affects the Accessibility dimension: users who need LMP decomposition, constraint shadow prices, or sensitivity analysis must access undocumented internals (`net._ppc["bus"][:, 13]` for bus LMPs, custom result capture for constraint duals). The gap also affects Maturity assessment -- a well-architected tool would expose solver output through its public result interface.

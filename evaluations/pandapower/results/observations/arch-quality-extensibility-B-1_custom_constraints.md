---
tag: arch-quality
source_dimension: extensibility
source_test: B-1
tool: pandapower
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: PYPOWER result dict with duals discarded during result extraction

## Finding

pandapower's OPF pipeline discards the full PYPOWER result dictionary (containing constraint multipliers/duals in `result['lin']['mu']`, `result['var']['mu']`) during the `_extract_results` step that maps PYPOWER results back to pandapower DataFrames. This architectural choice means shadow prices for custom constraints are permanently lost.

## Context

During B-1, the PYPOWER interior-point solver successfully computes constraint duals for user-injected flow gate constraints. The duals are present in the PYPOWER result dict (`result['lin']['mu']['flowgate']`) but are never transferred to any pandapower DataFrame or accessible attribute. Even the standard branch-flow constraint duals (LMPs) are only partially extracted via `net.res_bus.lam_p`.

## Implications

This is a positive finding for PYPOWER's architecture (the underlying solver and constraint system work well) but a negative finding for pandapower's architecture (the extraction layer discards valuable information). This pattern -- where internal capabilities exist but are hidden by the API layer -- should be noted in the Maturity assessment as an architectural quality observation.

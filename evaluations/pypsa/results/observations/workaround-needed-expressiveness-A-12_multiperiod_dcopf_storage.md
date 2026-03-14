---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-12
tool: pypsa
severity: medium
timestamp: 2026-03-13T00:00:00Z
---

# Observation: Branch shadow prices not assigned to network after n.optimize()

## Finding

In PyPSA v1.1.2, `n.lines_t.mu_upper` and `n.lines_t.mu_lower` are empty after `n.optimize()`, even though the solver computes and reports shadow prices. The solver log explicitly states: "The shadow-prices of the constraints Line-fix-s-upper, Line-fix-s-lower ... were not assigned to the network." Shadow prices must be extracted from the linopy model's internal constraint duals instead.

## Context

During A-12 (24-hour multi-period DCOPF with storage), branch shadow prices were needed to verify congestion reporting (pass condition 1). The documented API path (`n.lines_t.mu_upper`/`mu_lower`) returned empty DataFrames. The workaround accesses `n.model.constraints['Line-fix-s-upper'].dual`, which depends on undocumented internal constraint naming. This same issue was observed in A-3 (DCOPF) testing.

## Implications

This is a recurring PyPSA v1.1.2 bug affecting any test that requires branch-level shadow prices. It should be noted in the Accessibility audit (D-4) as a documentation gap -- the documented API exists but silently fails to populate results. The workaround is classified as fragile because the internal constraint name format could change in future versions.

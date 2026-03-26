---
tag: api-friction
source_dimension: expressiveness
source_test: A-3
tool: pypsa
severity: low
timestamp: 2026-03-24T12:02:00Z
---

# Observation: Branch shadow prices not assigned to network after optimize()

## Finding

After `n.optimize()` in PyPSA v1.1.2, the branch constraint shadow prices
(`n.lines_t.mu_upper`, `n.lines_t.mu_lower`) are not populated. The solver log
explicitly states: "The shadow-prices of the constraints Generator-fix-p-lower,
Generator-fix-p-upper, Line-fix-s-lower, Line-fix-s-upper, ... were not
assigned to the network."

Bus-level LMPs (`n.buses_t.marginal_price`) ARE populated correctly. The
branch shadow prices must be extracted from the linopy model object
(`n.model.constraints[name].dual`).

## Context

During A-3 (DCOPF on TINY), per-branch shadow prices were needed to verify
binding constraints. The `mu_upper`/`mu_lower` DataFrames were empty after
`optimize()`. The linopy constraint duals provided the same information via
`n.model.constraints["Line-fix-s-upper"].dual`.

## Implications

- Relevant to Accessibility: users expecting shadow prices in the standard
  result DataFrames will find them empty with no error message.
- The workaround is stable (uses linopy's documented public API) but is not
  shown in PyPSA's standard documentation or examples.
- This may be a known issue in PyPSA v1.1.2 or intentional behavior to avoid
  overwriting user data in the network DataFrames.

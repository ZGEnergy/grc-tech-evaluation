---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-3
tool: pypsa
severity: high
timestamp: 2026-03-11T00:00:00Z
---

# Observation: n.lines_t.mu_upper empty after optimize() — shadow prices require linopy model access

## Finding

After `n.optimize()` in PyPSA v1.1.2, the shadow price attributes `n.lines_t.mu_upper` and `n.lines_t.mu_lower` are empty DataFrames. Binding line/transformer constraints must be extracted from `n.model.constraints["Line-fix-s-upper"].dual` using linopy internal constraint names — undocumented internal naming convention.

## Context

Test A-3 (DCOPF) required verifying ≥2 binding line constraints with non-zero shadow prices. The documented API attribute `n.lines_t.mu_upper` (documented in PyPSA's component attribute tables) returns an empty DataFrame after `n.optimize()`. Shadow prices are accessible via the linopy model: `n.model.constraints["Line-fix-s-upper"].dual` and `n.model.constraints["Transformer-fix-s-lower"].dual`, where constraint names follow the pattern `{ComponentClass}-fix-s-{upper|lower}`. These names are internal to PyPSA's optimization module and are not in the user-facing API docs.

6 binding constraints were found (2 lines + 4 transformers), confirming the OPF is congested. The shadow prices themselves are correct — only the access path is the problem.

## Implications

This is a significant expressiveness gap for any workflow that needs LMP decomposition (A-10) or SCOPF analysis (A-4). Extensibility evaluators should note that custom shadow price extraction is required for congestion pricing applications. Accessibility evaluators should note that the documented `mu_upper` attribute is misleadingly empty — users will expect shadow prices to be populated automatically after optimization, matching other tools' behavior.

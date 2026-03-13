---
tag: api-friction
source_dimension: extensibility
source_test: B-1
tool: pypsa
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: ACTIVSg10k OPF infeasible with overwrite_zero_s_nom=1.0 — non-obvious parameter choice

## Finding

ACTIVSg10k has 2,462 transmission lines with zero thermal ratings in the source data. PyPSA's `import_from_pypower_ppc()` requires a value for `overwrite_zero_s_nom` to handle these lines. Using `overwrite_zero_s_nom=1.0` (1 MVA) — a common choice for networks where OPF is not intended — makes the ACTIVSg10k DC OPF infeasible because 1 MVA limits create binding constraints that cannot be satisfied by the dispatch.

The correct value for OPF is `overwrite_zero_s_nom=100000.0` (100 GVA, effectively unconstrained), allowing the optimizer to ignore unrated lines.

## Context

Discovered during B-1 MEDIUM development. Multiple test failures with `status='infeasible'` were traced to the parameter choice. The parameter is required whenever the source MATPOWER file has zero-rated lines, but the distinction between "zero = unconstrained" and "zero = must be 1 MVA for OPF" is not documented. Other B-tests (B-3, B-9) use `overwrite_zero_s_nom=1.0` safely because they do not run OPF.

PyPSA's `import_from_pypower_ppc` docstring does not document the semantic difference between using 1.0 vs. a large value, nor does it warn when zero_s_nom lines are likely to make OPF infeasible.

## Implications

Any developer loading a real-world MATPOWER network for OPF will silently get an infeasible result unless they know about this parameter and choose a value appropriate for the intended use (DCPF vs OPF). The error message from HiGHS ("infeasible") provides no guidance. The Accessibility audit (D-4, error quality) should test whether the infeasibility diagnostic provides actionable guidance. The parameter default (`overwrite_zero_s_nom=None`) is also problematic — `None` causes an error on networks with zero-rated lines, forcing the developer to know and set the parameter without documentation guidance on what value to use.

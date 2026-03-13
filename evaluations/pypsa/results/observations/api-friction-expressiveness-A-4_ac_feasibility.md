---
tag: api-friction
source_dimension: expressiveness
source_test: A-4
tool: pypsa
severity: low
timestamp: 2026-03-11T00:00:00Z
---

# Observation: pf() return structure undocumented — Dict with n_iter/error/converged keys

## Finding

`n.pf()` returns a `pypsa.definitions.structures.Dict` with top-level keys `n_iter`, `error`, `converged` (each a DataFrame), not a dict keyed by sub-network with `.converged` attributes. The documentation does not describe this return structure clearly, requiring source code inspection to use correctly.

## Context

Discovered during A-4 AC feasibility check. Initial implementation iterated `pf_result.items()` expecting sub-network objects with `.converged` attribute (as suggested by older documentation examples). The actual structure is flat: `pf_result["converged"].values.flatten()[0]` to get the boolean convergence status.

## Implications

The undocumented return structure of `n.pf()` will affect any consuming dimension that uses AC power flow results. Accessibility audit (D-4) should note that `n.pf()` return structure is not clearly documented and requires source code inspection to parse correctly. This is a documentation gap that could confuse new users.

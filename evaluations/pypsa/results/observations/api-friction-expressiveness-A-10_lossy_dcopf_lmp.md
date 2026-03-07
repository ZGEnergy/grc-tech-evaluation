---
tag: api-friction
source_dimension: expressiveness
source_test: A-10
tool: pypsa
severity: medium
timestamp: 2026-03-06T00:00:00Z
---

# Observation: LMP decomposition requires Linopy model internals

## Finding

PyPSA does not provide a built-in LMP decomposition method. Extracting energy,
congestion, and loss components from bus marginal prices requires accessing the
Linopy model's constraint duals via `n.model.constraints`, which is a public but
non-obvious API path.

## Context

During A-10 (lossy DCOPF with LMP decomposition), the `n.buses_t.marginal_price`
DataFrame provides total LMPs but no breakdown. The Linopy `Constraints` object
uses a `.labels` attribute (not `.keys()`) to enumerate constraint names, and duals
are accessed via `getattr(model.constraints, name).dual`. The
`transmission_losses` parameter API itself is clean (single parameter), but the
deprecation warning for integer arguments (`transmission_losses=2`) indicates an
API transition in progress.

## Implications

The lack of a built-in decomposition method adds friction for users performing
market-oriented analysis where LMP components are standard outputs. This should be
noted in the accessibility assessment. The Linopy model access pattern, while public,
requires understanding the optimization model structure rather than just the power
systems domain.

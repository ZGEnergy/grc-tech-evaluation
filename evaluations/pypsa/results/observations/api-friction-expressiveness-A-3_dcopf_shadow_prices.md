---
tag: api-friction
source_dimension: expressiveness
source_test: A-3
tool: pypsa
severity: low
timestamp: 2026-03-06T00:00:00Z
---

# Observation: Line shadow prices not assigned to network after optimize()

## Finding

After `n.optimize()`, PyPSA assigns bus-level LMPs to `n.buses_t.marginal_price` but
does not assign line flow constraint duals (`mu_upper`/`mu_lower`) to the network.
The solver log explicitly warns that these shadow prices were not assigned.

## Context

During test A-3 (DC OPF), `n.lines_t.mu_upper` and `n.lines_t.mu_lower` are empty
DataFrames after optimization. To access line congestion duals, users would need to
query the Linopy model object at `n.model` directly. Bus LMPs (the primary output
for locational pricing) are available without issue.

## Implications

This is relevant to Extensibility (B-series) -- users needing line shadow prices for
congestion analysis must access the underlying Linopy model, adding a step beyond
the standard results API. It is also relevant to Accessibility -- the behavior is
inconsistent (bus duals assigned, line duals not) and may confuse users expecting
symmetric treatment.

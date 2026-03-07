---
tag: api-friction
source_dimension: expressiveness
source_test: A-3
tool: pandapower
severity: low
timestamp: 2026-03-06T00:00:00Z
---

# Observation: OPF convergence check uses different attribute than PF

## Finding

Power flow convergence is checked via `net["converged"]` but OPF convergence uses `net["OPF_converged"]`. This inconsistency is a minor API friction point -- a user accustomed to the PF API would need to discover the separate OPF convergence flag.

## Context

During A-3 (DC OPF), the convergence check required knowing that `net["OPF_converged"]` exists separately from `net["converged"]`. Both are boolean flags but serve different solve types. Additionally, the objective value is accessed via `net.res_cost` (an attribute, not a DataFrame column), which differs from other result access patterns.

## Implications

Minor documentation/API consistency issue relevant to accessibility assessment (D-2, D-4). Not a major friction point but worth noting for the API design evaluation.

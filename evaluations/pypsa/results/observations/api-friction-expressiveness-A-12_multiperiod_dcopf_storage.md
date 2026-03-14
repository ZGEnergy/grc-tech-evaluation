---
tag: api-friction
source_dimension: expressiveness
source_test: A-12
tool: pypsa
severity: low
timestamp: 2026-03-13T00:00:00Z
---

# Observation: Multi-period DCOPF with storage requires minimal boilerplate in PyPSA

## Finding

PyPSA's multi-period DCOPF with storage is straightforward to set up. The `StorageUnit` component natively supports `efficiency_store`, `efficiency_dispatch`, `cyclic_state_of_charge`, and `max_hours` parameters. Setting up 24-hour snapshots and time-varying loads requires only `n.set_snapshots()` and assigning to `n.loads_t.p_set`. The quadratic cost term (`marginal_cost_quadratic`) is a first-class generator attribute. The overall API friction for A-12 is low.

## Context

The A-12 test loaded the Modified Tiny recipe (differentiated gen costs, 24-hour load profile, 70% branch derating, BESS at bus 16) and solved a QP-based multi-period DCOPF. The only notable friction point was the shared loader's gencost import being overridden by the recipe's differentiated costs, which required explicitly setting `marginal_cost` and `marginal_cost_quadratic` per generator.

## Implications

This positive finding supports a high expressiveness grade for PyPSA's multi-period optimization capabilities. The `StorageUnit` API with cyclic SoC is well-designed and requires no workarounds for inter-temporal storage modeling. The Accessibility audit should note that PyPSA's storage API is well-documented and intuitive for standard use cases.

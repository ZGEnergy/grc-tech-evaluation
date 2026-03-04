---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-3
tool: pypsa
severity: low
timestamp: 2026-03-04T19:12:50Z
---

# Observation: Manual generator cost assignment needed for OPF from MATPOWER data

## Finding

A stable workaround (setting `marginal_cost` on the generators DataFrame) is required to
run DC OPF when loading networks from MATPOWER `.m` files, because the pypower importer
drops `gencost` data.

## Context

The workaround uses fully documented public API (`net.generators.at[name, "marginal_cost"]`)
and is classified as **stable** -- it will not break across versions. However, it requires
the user to independently parse gencost data from the source file and correctly linearize
quadratic cost functions for PyPSA's LP formulation.

For case39, all generators have identical quadratic costs (`0.01*p^2 + 0.3*p + 0.2`), so
the linearization was straightforward. For heterogeneous cost functions, the workaround
would be more involved.

## Implications

- **Extensibility:** The workaround pattern (manual DataFrame assignment) is the standard
  way to configure PyPSA networks, so it doesn't indicate an API limitation -- just an
  import completeness gap.
- **Scalability:** For large networks (2000+ generators), manually iterating over generators
  to set costs is O(n) but trivial in practice.

---
tag: doc-gaps
source_dimension: expressiveness
source_test: A-3
tool: gridcal
severity: medium
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: OPF options parameter naming inconsistency and sparse documentation

## Finding

The `OptimalPowerFlowOptions` constructor uses `solver=` (not `solver_type=`) for the solver
parameter, despite `PowerFlowOptions` using `solver_type=`. This naming inconsistency caused
an initial `TypeError`. The parameter name was discovered by inspecting the constructor
signature at runtime, not from documentation.

Additionally, the `overloads` result attribute contains non-zero values for branches that
exceed their derated limits, but the relationship between `overloads` and branch shadow
prices is undocumented. Branch 2_3_1 shows 112% loading with an overload value of -42.85,
but it is unclear whether this represents a shadow price, penalty, or absolute violation.

## Context

The ReadTheDocs documentation for GridCal/VeraGrid covers up to version 5.0.2 and uses the
old `GridCalEngine` naming. The installed version is 5.6.28. Source code inspection was
required to determine the correct API patterns.

## Implications

For accessibility assessment: Documentation lag is a significant barrier. The API surface
is intuitive once discovered, but discovery requires source code reading or runtime
introspection. The naming inconsistency between `PowerFlowOptions.solver_type` and
`OptimalPowerFlowOptions.solver` should be noted.

For maturity assessment: The documentation gap between the published docs (v5.0.2) and
installed version (v5.6.28) suggests rapid development outpacing documentation updates.

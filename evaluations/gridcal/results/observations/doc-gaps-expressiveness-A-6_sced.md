---
tag: doc-gaps
source_dimension: expressiveness
source_test: A-6
tool: gridcal
severity: low
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: No documented SCED workflow or commitment-fixing API

## Finding

GridCal has no named SCED abstraction or API for fixing a commitment schedule and solving
economic dispatch. The two-stage UC-ED workflow must be implemented by the user via
`Pmax_prof`/`Pmin_prof` profile manipulation. This pattern works correctly but is not
documented -- it was discovered through API exploration and source code reading.

## Context

During A-6 (SCED), the commitment from A-5 was fixed by setting generator Pmax/Pmin profiles
to zero for decommitted hours and running the OPF in `Normal` dispatch mode with ramp
constraints. This approach uses documented public API methods (`Pmax_prof.set()`,
`OpfDispatchMode.Normal`, `consider_ramps=True`) but the overall pattern is not described in
any documentation or examples.

## Implications

The Accessibility audit should note that implementing a UC-ED two-stage workflow requires
understanding the profile system and dispatch mode enumeration without documentation
guidance. The pattern is stable (public API) but requires non-trivial domain knowledge to
discover.

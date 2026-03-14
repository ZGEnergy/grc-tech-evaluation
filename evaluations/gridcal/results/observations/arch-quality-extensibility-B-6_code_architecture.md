---
tag: arch-quality
source_dimension: extensibility
source_test: B-6
tool: gridcal
severity: medium
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: Monolithic OPF formulation limits extensibility

## Finding

The OPF formulation in `linear_opf_ts.py` (3146 LOC) is a single procedural function with no hook points, plugin architecture, or constraint injection API. All dispatch modes are handled via if/else branches in the same function. The data model layer (`assets.py`, 7671 LOC) is also very large.

## Context

During B-6 (code architecture audit), we traced the DCPF solve path through 5 abstraction layers. While macro-level separation of concerns is good (model/simulation/results), the OPF formulation layer is monolithic. The worker functions use double-underscore naming (`__solve_island_limited_support`) indicating they are private. The only documented internal interface is the LpModel abstraction for MIP solvers.

Internal docstring coverage varies: data model layer is well-documented (74-82%), but the simulation/worker layer has poor coverage (12-14%).

## Implications

The monolithic OPF architecture explains why B-1 (custom constraints) requires a fragile workaround. This architectural finding should inform the Maturity audit -- the tool has grown organically around a single developer's vision rather than being designed for extensibility. The rebranding from GridCal to VeraGrid in 5.4.0 was a namespace change, not an architectural refactor.

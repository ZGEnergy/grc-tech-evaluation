---
tag: api-friction
source_dimension: expressiveness
source_test: A-6
tool: pypsa
severity: low
timestamp: 2026-03-06T00:00:00Z
---

# Observation: No built-in SCUC-to-SCED commitment fixing method

## Finding

PyPSA lacks a dedicated method for fixing a commitment schedule from SCUC and re-dispatching as an LP. The user must manually encode the binary commitment into time-varying `p_min_pu`/`p_max_pu` bounds and set `committable=False`. This is ~10 lines of glue code using documented public API.

## Context

Test A-6 implements a two-stage SCUC-to-SCED workflow. After solving SCUC (MILP), the commitment schedule must be locked and economic dispatch re-solved as LP. `fix_optimal_dispatch()` exists but fixes all dispatch values, not just commitment status -- it is not suitable for this use case. `fix_optimal_capacities()` is for investment planning. The workaround of encoding commitment into generator bounds works correctly and is stable.

## Implications

Minor API gap. A `fix_commitment()` convenience method would improve the two-stage workflow ergonomics. This should be noted in the Accessibility assessment as a common power-systems workflow pattern that requires manual implementation. The workaround is straightforward and uses only public API, so the impact is low.

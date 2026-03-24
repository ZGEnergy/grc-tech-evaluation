---
tag: api-friction
source_dimension: expressiveness
source_test: A-1
tool: powermodels
severity: low
timestamp: 2026-03-12T03:24:30Z
---

# API Friction: compute_dc_pf does not populate branch flows in result dict

## Observation

`PowerModels.compute_dc_pf(data)` returns a result dict with `"solution"` containing only `"bus"` data (voltage angles). Branch flows are not post-processed into `"solution"]["branch"`. To get branch line flows, the caller must compute them manually from bus angles using the DC power flow formula.

Additionally, `termination_status` is returned as a `Bool` (not a JuMP `TerminationStatusCode`), inconsistent with the JuMP-based `solve_dc_opf` which returns `OPTIMAL` / `LOCALLY_SOLVED`.

## Code that triggers this

```julia

result = PowerModels.compute_dc_pf(data)
# result["solution"]["bus"]["1"]["va"]  -- works, has angle
# result["solution"]["branch"]          -- key does not exist
# result["termination_status"]          -- Bool, not String/Symbol

```

## Workaround

Compute branch flows from angles:

```julia

pf_pu = (va_from - va_to - shift) / (br_x * tap)

```

This requires accessing `data["branch"]` directly for `br_x`, `tap`, `shift`. All are public dict fields.

## Impact

Minor engineering friction. The calculation is ~10 lines of Julia. But the inconsistency with `solve_dc_pf` (which does populate branch flows in the solution dict) is a usability gap — users expecting consistent output structure between `compute_*` and `solve_*` variants will be surprised.

## Version

PowerModels.jl v0.21.5, Julia 1.10

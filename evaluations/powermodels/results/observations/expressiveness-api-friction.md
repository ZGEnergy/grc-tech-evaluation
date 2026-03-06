---
dimension: expressiveness
tag: api-friction
tool: powermodels
timestamp: 2026-03-05T19:00:00Z
---

# API Friction Observations -- Expressiveness

## 1. Inconsistent mutability conventions

- `compute_dc_pf(data)` returns a result dict and does NOT mutate `data`
- `compute_ac_pf!(data)` mutates `data` in-place (Julia `!` convention)
- Both are "native" (non-JuMP) solvers but have opposite data-flow patterns
- Impact: Users must remember which function mutates and which returns; easy to misuse

## 2. String-keyed Dict data model throughout

- All network data and results use `Dict{String,Any}` with string keys
- No typed structs, enums, or schema validation at the API boundary
- Generator ID `3` is accessed as `data["gen"]["3"]` -- string conversion required everywhere
- Impact: No IDE autocomplete, no compile-time type checking, easy to misspell keys
- Affected tests: All (A-1 through A-10)

## 3. Dual extraction requires explicit opt-in

- LMPs/shadow prices require `setting = Dict("output" => Dict("duals" => true))` parameter
- This is not the default, and the parameter name is not discoverable from function signature
- Impact: Users who don't know about this parameter get results without duals and may not realize they're missing
- Affected tests: A-3, A-10

## 4. Multi-network variable access pattern is underdocumented

- Accessing optimization variables requires `PowerModels.var(pm, nw_id, :pg, gen_id)`
- This pattern is not prominently documented; discovered through source code reading
- The `nw_id` is 1-indexed (not 0-indexed) and uses integers (not strings like the data dict)
- Impact: Significant friction when building custom formulations on top of PowerModels models
- Affected tests: A-5, A-9

## 5. No DataFrame or tabular output

- All results are nested dicts requiring manual iteration to extract
- No built-in conversion to DataFrames or CSV
- For time-series results (A-5, A-8), extracting commitment/dispatch schedules requires nested loops
- Impact: Post-processing burden on the user

## 6. Solver compatibility is not validated upfront

- `solve_dc_opf(data, GLPK.Optimizer)` with quadratic costs fails at solve time, not at model construction
- `solve_opf(data, DCPLLPowerModel, HiGHS.Optimizer)` fails because HiGHS can't handle quadratic constraints
- No warning or error at model construction about solver capability mismatch
- Impact: Users discover solver incompatibility only after waiting for model construction
- Affected tests: A-3 (GLPK), A-10 (HiGHS), A-5 (HiGHS with MIQP)

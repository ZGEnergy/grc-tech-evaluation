---
test_id: D-4
tool: powermodels
dimension: accessibility
status: qualified_pass
timestamp: 2026-03-05
---

# D-4: Error Diagnostic Quality

## Finding

PowerModels produces meaningful diagnostics for solver-level infeasibility and missing data, but silently accepts an invalid bus type (bus_type=99) without warning or error, returning a seemingly valid solution.

## Evidence

### (a) Infeasible OPF -- line limit set to 0

**Setup:** `data["branch"]["1"]["rate_a"] = 0.0` then `solve_dc_opf`

**Output:**

```

Model status        : Infeasible
Simplex   iterations: 30

```

**Result dict:**

```

Termination status: INFEASIBLE
Objective: 0.0
Solve time: 0.0016s
Solution buses: 39

```

**Classification: Meaningful diagnostic.** The solver (HiGHS) clearly reports `INFEASIBLE` status, which PowerModels propagates through the result dict as `termination_status: INFEASIBLE`. The solver also attempts to compute a dual ray for infeasibility diagnosis. However, the result still contains a `solution` dict with 39 buses -- a user who checks only for the presence of a solution (rather than termination status) could mistake this for a valid result. The solution values in this case are from the last iterate, not a feasible point.

### (b) Missing generator cost curve

**Setup:** `delete!(data["gen"]["1"], "cost")` then `solve_dc_opf`

**Output:**

```

EXCEPTION: KeyError
MESSAGE: KeyError("cost")
STACKTRACE:
  [1] getindex(h::Dict{String, Any}, key::String) at dict.jl:498
  [2] expression_pg_cost(pm::DCPPowerModel; report::Bool) at objective.jl:139
  [3] expression_pg_cost at objective.jl:119
  [4] objective_min_fuel_and_flow_cost(pm::DCPPowerModel) at objective.jl:3

```

**Classification: Meaningful diagnostic (with caveats).** The error is a raw Julia `KeyError` with a clear stacktrace pointing to `objective.jl:139` in the `expression_pg_cost` function. An experienced Julia developer can immediately see that the `"cost"` key is missing during objective construction. However, there is no domain-specific error message like "Generator 1 is missing required cost data" -- the user must read the stacktrace and infer the cause. This is a generic language-level error, not a PowerModels validation error. No upfront data validation catches the missing field before model construction begins.

### (c) Invalid bus type (bus_type = 99)

**Setup:** `data["bus"]["1"]["bus_type"] = 99` then `compute_dc_pf`

**Output:**

```

Termination status: true
Objective: 0.0
Solution buses: 39

```

**Classification: Silent failure.** PowerModels accepts `bus_type = 99` without any warning, error, or validation. The solve completes and returns a result with `termination_status: true`. The MATPOWER standard defines bus types 1 (PQ), 2 (PV), 3 (ref/slack), and 4 (isolated). Type 99 is meaningless, yet PowerModels does not validate bus type values before or during the solve. The returned solution may be incorrect (the bus is likely treated as a default type), but the user receives no indication of the problem.

### Cross-reference with expressiveness observations

The api-friction observations note that PowerModels uses `Dict{String,Any}` throughout with no typed structs or schema validation at the API boundary. This is the root cause of error (c) -- without a type system or validation layer, invalid values in the data dict are not caught. The solver-issues observations further note that solver-formulation incompatibilities are also only discovered at solve time, not at model construction.

## Implications

PowerModels has a mixed error quality profile:

- **Solver-level errors (infeasibility):** Well-handled. The solver status propagates cleanly and the status string is unambiguous.
- **Data structure errors (missing keys):** Caught at model construction as raw Julia exceptions. Informative to experienced users via stacktrace, but no domain-specific validation or error messages.
- **Data value errors (invalid values):** Not caught at all. The `Dict{String,Any}` data model provides no schema validation, so semantically invalid values pass silently. This is the most concerning finding -- a user who sets a wrong bus type, an invalid generator status, or a nonsensical cost model will get results without any indication of error.

The lack of input validation is the primary accessibility concern. A validation layer (similar to pandapower's `runpp` diagnostics or MATPOWER's `check_gen_data`) would significantly improve the user experience.

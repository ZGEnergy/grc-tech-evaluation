---
test_id: D-4
tool: powermodels
dimension: accessibility
network: N/A
status: qualified_pass
workaround_class: null
timestamp: 2026-03-13T23:00:00Z
protocol_version: v10
skill_version: v1
test_hash: "ac43ee93"
---

# D-4: Error Quality Test

## Three Error Scenarios

### Error (a): Infeasible OPF (all branch thermal limits set to zero)

**Setup:**
```julia
data = PowerModels.parse_file("case39.m")
for (id, br) in data["branch"]
    br["rate_a"] = 0.0
end
result = solve_dc_opf(data, HiGHS.Optimizer)
```

**Output:**
```
termination_status: INFEASIBLE
primal_status: INFEASIBLE_POINT
```

**Classification: Meaningful diagnostic**

PowerModels propagates the JuMP/HiGHS termination status directly. `INFEASIBLE` and `INFEASIBLE_POINT` are clear, standard MOI status codes. The user immediately knows the problem is infeasible and that the solver could not find a feasible point. No binding constraint identification is provided (which specific branch or constraint caused infeasibility), but the top-level status is unambiguous.

PowerModels does not perform pre-solve validation on `rate_a` values -- setting all limits to zero does not trigger a warning before the solve attempt. This is by design (the tool delegates feasibility assessment to the solver), but a pre-solve check for obviously invalid data would improve the user experience.

---

### Error (b): Missing generator cost curve

**Setup:**
```julia
data = PowerModels.parse_file("case39.m")
for (id, gen) in data["gen"]
    delete!(gen, "cost")
    delete!(gen, "ncost")
    delete!(gen, "model")
end
result = solve_dc_opf(data, HiGHS.Optimizer)
```

**Output:**
```
EXCEPTION: KeyError
Message: KeyError: key "model" not found
```

**Classification: Cryptic solver error**

The error is a `KeyError: key "model" not found` -- technically accurate but not user-friendly. It tells the user _what_ key is missing but not _which generator_ is affected, nor does it suggest how to fix the data (e.g., "Generator cost data must include 'model', 'ncost', and 'cost' fields"). The error originates in `objective.jl` during model construction, so it occurs before the solver is invoked.

The stack trace makes the error locatable for Julia developers: the call chain from `solve_dc_opf` -> `build_opf` -> `objective_min_fuel_and_flow_cost` -> `expression_pg_cost` is clear. A domain user without Julia experience would find the stack trace overwhelming.

A better error message would be: "Generator [id] is missing required field 'model'. All generators must have cost model data (fields: model, ncost, cost) for OPF."

Note: In the prior v9 evaluation, the error reported `key "cost" not found`. In this run, `key "model" not found` was reported instead, indicating the iteration order over generator dict fields is non-deterministic and the first missing key varies. Both are equally cryptic.

---

### Error (c): Invalid bus type (bus_type = 99)

**Setup:**
```julia
data = PowerModels.parse_file("case39.m")
for (id, bus) in data["bus"]
    bus["bus_type"] = 99
end
result = solve_dc_opf(data, HiGHS.Optimizer)
```

**Output:**
```
termination_status: OTHER_ERROR
objective: NaN
```

**Classification: Silent failure (partial)**

Setting all bus types to an invalid value (99) does not trigger any validation error or warning from PowerModels. No `check_*` validation function catches this. The model is constructed and submitted to HiGHS, which returns `OTHER_ERROR` with a `NaN` objective.

The `OTHER_ERROR` status from HiGHS is less informative than the `INFEASIBLE` status from Error (a). The user receives no indication that the root cause is invalid bus type data. In a debugging context, `OTHER_ERROR` + `NaN` objective could mean anything from numerical instability to malformed model construction.

In the prior v9 evaluation (with only bus 1 set to type 99), the OPF returned `OPTIMAL` since bus 1 was a PQ bus and the invalid type was silently treated as non-reference. Setting _all_ buses to type 99 causes a more severe failure because no reference bus exists, but the error message still does not identify `bus_type` as the cause.

**Validation gap:** PowerModels has `check_connectivity`, `check_reference_bus`, and `check_status` validation functions, but none validate that `bus_type` values are within the legal set {1, 2, 3, 4}. This is a latent correctness risk for AC OPF where bus_type determines voltage control mode.

---

## Convergence Diagnostics (from consumed observations)

As noted in the convergence-quality observation for A-2, `compute_ac_pf` does not expose NR iteration count or final convergence residual. The result dict contains only:
- `termination_status` -- Bool (true/false), not a JuMP `TerminationStatusCode`
- `solve_time` -- wall-clock seconds
- `objective` -- always 0.0

This is a separate but related diagnostic gap: users cannot verify convergence quality beyond the binary true/false status. The `solve_*` API variants (JuMP-based) provide richer solver diagnostics via MOI status codes.

## Summary Table

| Error Scenario | Output | Classification |
|---|---|---|
| Infeasible OPF (rate_a = 0) | `INFEASIBLE` / `INFEASIBLE_POINT` | Meaningful diagnostic |
| Missing generator cost curve | `KeyError: key "model" not found` + stack trace | Cryptic solver error |
| Invalid bus_type = 99 (all buses) | `OTHER_ERROR` / `NaN` objective | Silent failure |

## Cross-Reference to Consumed Observations

- **api-friction**: DCPLLPowerModel + HiGHS produces `UnsupportedConstraint` with no guidance to use Ipopt (A-10 observation)
- **api-friction**: `compute_dc_pf` returns Bool termination_status, inconsistent with JuMP-based API (A-1 observation)
- **convergence-quality**: No NR iteration count or residual from `compute_ac_pf` (A-2 observation)
- **solver-issues**: HiGHS QP `OTHER_ERROR` on quadratic costs at scale (A-3, A-9 observations)

## Pass/Fail Rationale

**qualified_pass**: Error handling is adequate for the most common user error (infeasible OPF). The missing cost key error, while cryptic, provides enough stack trace context for a Julia developer to locate the issue. The silent acceptance of invalid bus_type is a genuine diagnostic quality gap that could mask data corruption in production workflows. The tool relies on solver-level error reporting rather than pre-solve data validation, which is effective for well-formed problems but provides poor diagnostics for malformed input data.

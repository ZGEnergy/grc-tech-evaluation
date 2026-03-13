---
test_id: D-4
tool: powermodels
dimension: accessibility
network: N/A
status: qualified_pass
workaround_class: null
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "bb3636a0"
---

# D-4: Error Quality Test

## Three Error Scenarios

### Error 1: Infeasible OPF (near-zero branch thermal limit)

#### Setup:

```julia

data = parse_file("../../data/networks/case39.m")
data["branch"]["1"]["rate_a"] = 0.001  # near-zero limit, ~0.1 MVA
result = solve_dc_opf(data, optimizer_with_attributes(HiGHS.Optimizer, "output_flag"=>false))
println(result["termination_status"])  # INFEASIBLE
println(result["primal_status"])       # INFEASIBLE_POINT

```

#### Exact output:

```

termination_status: INFEASIBLE
primal_status: INFEASIBLE_POINT

```

#### Classification: Meaningful diagnostic

PowerModels propagates the JuMP/HiGHS termination status directly. `INFEASIBLE` and `INFEASIBLE_POINT` are clear, standard MOI status codes. The user immediately knows the problem is infeasible and that the primal solution is not a feasible point. No binding constraint identification is provided (which branch is causing infeasibility), but the top-level status is unambiguous.

Note: PowerModels logs angmin/angmax warnings during parse_file but does not emit any warning or annotation when a near-zero thermal limit is set — this is not flagged as unusual.

---

### Error 2: Missing Generator Cost Curve

#### Setup:

```julia

data = parse_file("../../data/networks/case39.m")
delete!(data["gen"]["1"], "cost")
result = solve_dc_opf(data, optimizer_with_attributes(HiGHS.Optimizer, "output_flag"=>false))

```

#### Exact error output:

```

ERROR: LoadError: KeyError: key "cost" not found
Stacktrace:
  [1] getindex(h::Dict{String, Any}, key::String)
    @ Base ./dict.jl:498
  [2] expression_pg_cost(pm::DCPPowerModel; report::Bool)
    @ PowerModels .../src/core/objective.jl:139
  [3] expression_pg_cost
    @ .../src/core/objective.jl:119 [inlined]
  [4] objective_min_fuel_and_flow_cost(pm::DCPPowerModel; kwargs::@Kwargs{})
    @ PowerModels .../src/core/objective.jl:3
  [5] objective_min_fuel_and_flow_cost
    @ .../src/core/objective.jl:2 [inlined]
  [6] build_opf(pm::DCPPowerModel)
    @ PowerModels .../src/prob/opf.jl:23
  [7] instantiate_model(...)
...
  [16] solve_dc_opf(file::Dict{String, Any}, optimizer::MathOptInterface.OptimizerWithAttributes)
    @ PowerModels .../src/prob/opf.jl:6
  [17] top-level scope
    @ /workspace/evaluations/powermodels/d4_test2.jl:6

```

#### Classification: Cryptic solver error (partial)

The error is a `KeyError: key "cost" not found` — technically accurate but not user-friendly. It tells you _what_ key is missing but not _which generator_ is missing the cost data, nor does it suggest how to fix the data. The full stack trace makes it findable: `expression_pg_cost` in `objective.jl:139` is the immediate source, which gives a developer enough context. A domain user without Julia experience would find the stack trace overwhelming.

A better error message would be: "Generator 1 is missing required field 'cost'. All generators must have cost data for OPF."

---

### Error 3: Invalid Bus Type

#### Setup:

```julia

data = parse_file("../../data/networks/case39.m")
data["bus"]["1"]["bus_type"] = 99  # invalid — valid values: 1 (PQ), 2 (PV), 3 (ref), 4 (isolated)

# Validation functions
PowerModels.check_connectivity(data)   # no output, no error
PowerModels.check_reference_bus(data)  # no output, no error
PowerModels.check_status(data)         # no output, no error

```

**Exact output:** No output, no error from any validation function.

## Second test: run OPF with bus_type=99:

```julia

result = solve_dc_opf(data, optimizer_with_attributes(HiGHS.Optimizer, "output_flag"=>false))
println(result["termination_status"])  # OPTIMAL
println(result["objective"])           # 41263.94

```

### Classification: Silent failure

`bus_type=99` is entirely ignored by all three validation functions. The OPF proceeds and returns `OPTIMAL` with what appears to be a valid result. In reality, the invalid bus_type value may or may not affect the formulation depending on how bus_type is used — for DC OPF, only the reference bus (type=3) matters for reference angle fixing. Since bus 1 was a PQ bus (type=1), setting it to type=99 effectively makes it a non-reference, non-PV bus, which is how PQ buses behave anyway.

However, the complete absence of validation feedback is a diagnostic gap. A user who accidentally corrupts bus_type data will receive no indication of the error. This is a latent correctness risk for more sensitive formulations (e.g., AC OPF where bus_type determines the voltage control mode).

---

## Summary Table

| Error Scenario | Output Quality | Classification |
|---|---|---|
| Infeasible OPF (near-zero limit) | `INFEASIBLE` / `INFEASIBLE_POINT` | Meaningful diagnostic |
| Missing generator cost key | `KeyError: key "cost" not found` + stack trace | Cryptic solver error |
| Invalid bus_type value | No output — silent acceptance | Silent failure |

## Convergence Diagnostics (from A-2 observation)

As noted in the convergence-quality observation for A-2, `compute_ac_pf` does not expose NR iteration count or final convergence residual. The result dict contains only:
- `termination_status` — Bool (true/false)
- `solve_time` — wall-clock seconds
- `objective` — always 0.0

This is a separate but related diagnostic gap: users cannot verify convergence quality beyond the binary true/false status.

## Pass/Fail Rationale

**qualified_pass**: Error handling is adequate for infeasible OPF (the most common user error in practice). The missing cost key error, while cryptic, provides enough stack trace context for a developer. The silent acceptance of invalid bus_type is a genuine diagnostic quality gap that could mask data corruption.

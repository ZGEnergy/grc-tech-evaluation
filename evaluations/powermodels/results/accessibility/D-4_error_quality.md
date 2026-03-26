---
test_id: D-4
tool: powermodels
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 9309430d
status: qualified_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: HiGHS
timestamp: 2026-03-24T18:00:00Z
---

# D-4: Error Quality

## Result: QUALIFIED PASS

## Finding

Of three deliberate error scenarios, PowerModels produces 1 meaningful diagnostic, 1 cryptic
error, and 1 silent failure. The tool delegates feasibility assessment to the solver and
performs minimal pre-solve input validation, which works well for solver-detectable problems
but provides poor diagnostics for malformed input data.

## Evidence

All tests run inside devcontainer on 2026-03-24 using case39.m with HiGHS.Optimizer.

### Error (a): Infeasible OPF (all branch thermal limits set to zero)

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

**Classification: Meaningful diagnostic.** `INFEASIBLE` and `INFEASIBLE_POINT` are standard
MOI status codes, immediately clear. No binding constraint identification, but the top-level
status is unambiguous. PowerModels does not pre-validate `rate_a` values (no warning before
solve), delegating feasibility assessment to the solver.

---

### Error (b): Missing generator cost curve

```julia
data = PowerModels.parse_file("case39.m")
for (id, gen) in data["gen"]
    delete!(gen, "cost"); delete!(gen, "ncost"); delete!(gen, "model")
end
result = solve_dc_opf(data, HiGHS.Optimizer)
```

**Output:**
```
EXCEPTION: KeyError
Message: KeyError("model")
```

**Classification: Cryptic error.** The `KeyError: key "model" not found` is technically
accurate but not user-friendly. It identifies the missing key but not which generator is
affected, nor does it suggest a fix. The error originates during model construction
(`objective.jl -> expression_pg_cost`), so it fires before the solver is invoked. The stack
trace makes it locatable for Julia developers but is overwhelming for domain users.

Note: The specific missing key varies between runs (`"model"` or `"cost"`) because Julia
Dict iteration order is non-deterministic.

---

### Error (c): Invalid bus type (bus_type = 99 on all buses)

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
primal_status: NO_SOLUTION
```

**Classification: Silent failure.** Setting all bus types to 99 triggers no validation error
or warning. The model is constructed and submitted to HiGHS, which returns `OTHER_ERROR` with
NaN objective. The user receives no indication that invalid `bus_type` is the root cause.
PowerModels has `check_connectivity`, `check_reference_bus`, and `check_status` validators,
but none validate that `bus_type` values are in the legal set {1, 2, 3, 4}. This is a latent
correctness risk.

---

### Summary Table

| Error Scenario | Output | Classification |
|---|---|---|
| Infeasible OPF (rate_a = 0) | `INFEASIBLE` / `INFEASIBLE_POINT` | Meaningful diagnostic |
| Missing generator cost | `KeyError("model")` + stack trace | Cryptic error |
| Invalid bus_type = 99 | `OTHER_ERROR` / `NaN` / `NO_SOLUTION` | Silent failure |

### Convergence Diagnostics (cross-reference)

As documented in [convergence-quality observation](../observations/convergence-quality-expressiveness-A2_acpf_no_nr_diagnostics.md),
`compute_ac_pf` does not expose NR iteration count or final residual. The result dict contains
only Bool `termination_status`, `solve_time`, and `objective` (always 0.0 for PF). Users
cannot verify convergence quality beyond binary true/false.

### Additional Error Quality Observations

- `DCPLLPowerModel` + HiGHS produces `UnsupportedConstraint` with no guidance to use Ipopt
  [solver-specific]
- HiGHS QP returns `OTHER_ERROR` on quadratic costs at scale [solver-specific]

## Implications

Error handling is adequate for solver-detectable problems (infeasibility) but poor for
data validation errors. The tool's design delegates all validation to the solver, which
means well-formed problems get clean diagnostics while malformed input produces opaque
errors. The bus_type validation gap is the most concerning finding -- invalid bus types
are silently accepted, potentially masking data corruption in production workflows.

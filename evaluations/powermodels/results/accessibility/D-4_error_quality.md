---
test_id: D-4
tool: powermodels
dimension: accessibility
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
timestamp: 2026-03-07T00:00:00Z
---

# D-4: Error quality for 3 deliberate errors

## Result: QUALIFIED PASS

## Finding

PowerModels error reporting ranges from excellent (infeasible OPF) to poor (missing cost, invalid bus type). The infeasible OPF case returns a clean solver status with no exception. The missing generator cost and invalid bus type cases throw raw Julia exceptions (KeyError and AssertionError) with no domain-specific error messages, requiring users to read the stack trace and understand the internal code structure to diagnose the problem.

## Evidence

### Test (a): Infeasible OPF (line thermal limit = 0)

**Setup**: Set `rate_a = 0.0` on all branches in case5, then run `solve_dc_opf`.

**Result**: No exception. Solver returns structured status.

```

Termination status: INFEASIBLE
Primal status: INFEASIBLE_POINT
Objective: 25000.0

```

**Classification**: GOOD. The solver termination status clearly communicates infeasibility. The user receives a result dictionary with `INFEASIBLE` status rather than an opaque crash. HiGHS outputs "Model status: Infeasible" to stdout, providing additional context. The objective value (25000.0) is meaningless for an infeasible problem but its presence does not mislead since the status is clear.

### Test (b): Missing generator cost

**Setup**: Delete `cost`, `ncost`, and `model` keys from all generators in case5, then run `solve_dc_opf`.

**Result**: Unhandled `KeyError` exception.

```

EXCEPTION: KeyError
Message: KeyError("model")

```

Stack trace points to `PowerModels/src/core/objective.jl:126` in `expression_pg_cost`.

**Classification**: POOR. The error is a raw Julia `KeyError` with no domain-specific message. A user unfamiliar with PowerModels internals would need to:
1. Understand that `"model"` refers to the cost model type (polynomial vs piecewise-linear)
2. Read the source code at `objective.jl:126` to understand the expected data structure
3. Know that generators require `model`, `ncost`, and `cost` fields for OPF

A helpful error would say something like: "Generator 1 missing required cost field 'model'. Expected cost_model=1 (piecewise) or cost_model=2 (polynomial)."

### Test (c): Invalid bus type (bus_type = 99)

**Setup**: Set `bus_type = 99` on all buses in case5, then run `solve_dc_pf`.

**Result**: `AssertionError` exception.

```

EXCEPTION: AssertionError
Message: AssertionError("bus[\"bus_type\"] == 2")

```

Stack trace points to `PowerModels/src/prob/pf.jl:49` in `build_pf`.

**Classification**: POOR-TO-MODERATE. The assertion message reveals the expected condition (`bus["bus_type"] == 2`) but provides no context about:
- Which bus failed the assertion
- What valid bus types are (1=PQ, 2=PV, 3=ref, 4=isolated)
- Why the power flow builder requires bus_type == 2 at that point in the code

The assertion is a developer-facing guard, not a user-facing validation. A helpful error would enumerate valid bus types and identify the offending bus.

### Summary Table

| Error Case | Exception Type | Domain-Specific Message | Actionable | Classification |
|------------|---------------|------------------------|------------|----------------|
| (a) Infeasible OPF | None (status return) | Yes (`INFEASIBLE`) | Yes | GOOD |
| (b) Missing gen cost | `KeyError("model")` | No | No | POOR |
| (c) Invalid bus type | `AssertionError` | Partial (shows assertion) | Partial | POOR-TO-MODERATE |

### Additional Observation from D-1 Testing

During D-1 testing, PowerModels emitted useful validation warnings during data parsing:
- `"bus 3 has an unrecongized bus_type 0, updating to bus_type 2"` (note: typo "unrecongized" in source)
- `"reversing the orientation of branch 6 (4, 3) to be consistent with other parallel branches"`
- `"the voltage setpoint on generator 4 does not match the value at bus 4"`

These warnings demonstrate that PowerModels has data validation capabilities during parsing, but they do not extend to runtime errors in the model building phase.

## Implications

PowerModels handles solver-level errors well (test a) because JuMP/MathOptInterface provides structured status reporting. However, data-level errors (tests b, c) produce raw Julia exceptions with no domain-specific context. This is a common pattern in research-oriented Julia packages where input validation is sparse and errors surface as internal implementation failures rather than user-facing diagnostics. Users working with programmatically-modified data (a common workflow in evaluation) will encounter opaque errors that require source code reading to debug.

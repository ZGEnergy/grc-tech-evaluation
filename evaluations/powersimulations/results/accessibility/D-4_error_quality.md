---
test_id: D-4
tool: powersimulations
dimension: accessibility
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "9309430d"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: "2026-03-14T00:00:00Z"
---

# D-4: Error Quality

## Result: INFORMATIONAL

## Finding

Of three deliberate error scenarios, PowerSimulations.jl produces a **meaningful diagnostic**
for one (infeasible OPF), a **type-system rejection** for one (wrong cost type), and a
**silent success** for one (zero-cost degenerate objective). The silent success case is the
most concerning — a user who accidentally sets all costs to zero gets `OPTIMAL` with
objective 0.0 and no warning. Bus type validation is mixed: structurally invalid states
(ISOLATED bus with connected branches) produce clear errors, but semantically invalid
states (REF bus with no generator) pass silently.

## Evidence

### Error (a): Infeasible OPF — Line Limits Set to Near-Zero

**Setup:** Set all 46 branch ratings to 0.001 pu (~0.1 MW), making power transfer
effectively impossible for a 6,254 MW load system.

**Result: MEANINGFUL DIAGNOSTIC**

```
┌ Error: Optimizer returned INFEASIBLE_POINT after 2 optimize! attempts
┌ Error: Serializing Infeasible Problem at /tmp/.../infeasible_GenericOpProblem.json
│    Solving model GenericOpProblem failed at 2024-01-01T00:00:00
Solve status: RunStatus.FAILED = 2
Termination status: INFEASIBLE
Primal status: INFEASIBLE_POINT
```

**Quality assessment:**
- The error message clearly states "INFEASIBLE" — no ambiguity
- PSI retries the solve (2 attempts) before declaring failure
- PSI automatically serializes the infeasible model to JSON for offline debugging
  (documented in the "debugging infeasible models" how-to)
- The `RunStatus.FAILED` return value is programmatically checkable
- HiGHS termination status is correctly propagated through PSI to the user

**Grade: A.** Best-in-class infeasibility reporting with automatic model export for diagnosis.

### Error (b): Missing/Invalid Generator Cost Curve

**Setup:** Three sub-tests of cost-related errors.

#### (b1) Set cost to `nothing`

```julia
set_operation_cost!(gen, nothing)
# => MethodError: Cannot `convert` an object of type Nothing to ...
```

**Result: TYPE-SYSTEM REJECTION** — Julia's type system prevents setting a `nothing` cost
on a `ThermalStandard` generator. The error is a Julia `MethodError`, not a domain-specific
PSI error. A power systems engineer unfamiliar with Julia would find this cryptic.

#### (b2) Set wrong cost type (RenewableGenerationCost on ThermalStandard)

```julia
set_operation_cost!(gen, RenewableGenerationCost(CostCurve(LinearCurve(0.0))))
# => MethodError: Cannot `convert` an object of type RenewableGenerationCost to ...
```

**Result: TYPE-SYSTEM REJECTION** — Same pattern. The Julia type system enforces that
`ThermalStandard` generators accept only `ThermalGenerationCost`. This is correct
validation but the error message is a generic Julia type error, not a domain-specific
message like "ThermalStandard requires ThermalGenerationCost, got RenewableGenerationCost."

#### (b3) Set all costs to zero (degenerate objective)

```julia
set_operation_cost!(gen, ThermalGenerationCost(CostCurve(LinearCurve(0.0)), 0.0, 0.0, 0.0))
# Builds and solves: OPTIMAL, objective = 0.0
```

**Result: SILENT SUCCESS** — PSI accepts zero-cost generators without warning, builds
the model, and HiGHS solves it to optimality with a zero objective value. There is no
warning that the objective function is trivial (all coefficients zero), no warning that
dispatch is arbitrary (any feasible dispatch is equally optimal), and no warning that
LMPs/duals from a zero-cost problem are degenerate.

**Grade: C.** Type-level errors are caught early (good) but with generic Julia messages
(poor). The zero-cost silent success is the most dangerous error mode — it produces
plausible-looking results that are economically meaningless.

### Error (c): Invalid Bus Type

**Setup:** Two sub-tests of bus type manipulation.

#### (c1) Set all buses to ISOLATED

```julia
set_bustype!(bus, ACBusTypes.ISOLATED)
# Then attempt DCPF:
# => ConflictingInputsError("Branch bus-26-bus-27-i_42 is set available and
#    connected to isolated bus bus-26")
```

**Result: MEANINGFUL DIAGNOSTIC** — PowerFlows.jl validates that branches cannot connect
to isolated buses before attempting the solve. The error message names the specific branch
and bus causing the conflict. This is a clear, actionable diagnostic.

#### (c2) Set a load bus (no generator) as REF

```julia
set_bustype!(bus1, ACBusTypes.REF)  # bus-1 is a pure load bus
result = solve_powerflow(DCPowerFlow(), sys)
# => DCPF completes successfully with no error or warning
```

**Result: SILENT SUCCESS** — PowerSystems.jl allows setting a load-only bus as the
reference bus with no validation. The DCPF solves and produces results. In a real
network model, the reference bus should have a generator to absorb the power balance
mismatch. This is a semantic error that the tool does not catch.

**Grade: B.** Structural validation (ISOLATED + connected branch) is excellent.
Semantic validation (REF bus requires generator) is absent but the consequence is a
solvable (if unconventional) problem rather than wrong results.

### Summary

| Error | Classification | Quality Grade |
|-------|---------------|--------------|
| (a) Infeasible OPF | Meaningful diagnostic | A |
| (b1) Cost = nothing | Type-system rejection (cryptic) | B- |
| (b2) Wrong cost type | Type-system rejection (cryptic) | B- |
| (b3) Zero cost | **Silent success** | D |
| (c1) All buses ISOLATED | Meaningful diagnostic | A |
| (c2) Load bus as REF | **Silent success** | C |

## Implications

PowerSimulations.jl's error quality is bifurcated. Structural errors that violate the
data model's type system or graph connectivity are caught early with clear messages —
this is a strength of Julia's type system and PSI's validation layer. However, semantic
errors that produce technically valid but meaningless problems (zero costs, wrong
reference bus) pass silently. The zero-cost silent success is particularly concerning
for an energy trading context where cost curve errors could produce incorrect dispatch
and LMP signals without any diagnostic indication.

The automatic serialization of infeasible models to JSON is a notable positive feature
not commonly found in competing tools.

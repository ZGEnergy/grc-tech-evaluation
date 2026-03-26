---
test_id: D-4
tool: powersimulations
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 9309430d
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# D-4: Error Quality

## Result: INFORMATIONAL

## Finding

Of three deliberate error scenarios, PowerSimulations.jl produces a **meaningful diagnostic**
for one (infeasible OPF), a **type-system rejection** for one (wrong cost type), and a
**silent success** for one (zero-cost degenerate objective). The silent success case is the
most concerning -- a user who accidentally sets all costs to zero gets `OPTIMAL` with
objective 0.0 and no warning. Bus type validation is mixed: structurally invalid states
(ISOLATED bus with connected branches) produce clear errors, but semantically invalid
states (REF bus with no generator) pass silently.

## Evidence

All error tests were executed in the devcontainer against IEEE 39-bus (case39.m) on
2026-03-24.

### Error (a): Infeasible OPF -- Line Limits Set to Near-Zero

**Setup:** Set all 46 branch ratings to 0.001 pu (~0.1 MW), making power transfer
effectively impossible for a 6,254 MW load system.

**Result: MEANINGFUL DIAGNOSTIC**

```
Build status: InfrastructureSystems.Optimization.ModelBuildStatusModule.ModelBuildStatus.BUILT = 0
┌ Error: Optimizer returned INFEASIBLE_POINT after 2 optimize! attempts
┌ Error: Serializing Infeasible Problem at /tmp/jl_oLxcFi/infeasible_GenericOpProblem.json
┌ Error: Decision Problem solve failed
Solve status: InfrastructureSystems.Simulation.RunStatusModule.RunStatus.FAILED = 2
```

**Quality assessment:**
- The error message clearly states "INFEASIBLE_POINT" -- no ambiguity
- PSI retries the solve (2 attempts) before declaring failure
- PSI automatically serializes the infeasible model to JSON for offline debugging
  (documented in the "debugging infeasible models" how-to)
- The `RunStatus.FAILED` return value is programmatically checkable
- HiGHS termination status is correctly propagated through PSI to the user

**Grade: A.** Best-in-class infeasibility reporting with automatic model export for diagnosis.

### Error (b): Missing/Invalid Generator Cost Curve

**Setup:** Three sub-tests of cost-related errors.

#### (b1) Set cost to `nothing`

```
set_operation_cost!(gen, nothing)
=> MethodError: Cannot `convert` an object of type Nothing to an object of type
   Union{MarketBidCost, ThermalGenerationCost}
```

**Result: TYPE-SYSTEM REJECTION** -- Julia's type system prevents setting a `nothing` cost
on a `ThermalStandard` generator. The error is a Julia `MethodError`, not a domain-specific
PSI error. A power systems engineer unfamiliar with Julia would find this cryptic. The
message mentions `Union{MarketBidCost, ThermalGenerationCost}` which at least hints at
valid types, but requires Julia type system knowledge to interpret.

#### (b2) Set wrong cost type (RenewableGenerationCost on ThermalStandard)

```
set_operation_cost!(gen, RenewableGenerationCost(CostCurve(LinearCurve(0.0))))
=> MethodError: Cannot `convert` an object of type RenewableGenerationCost to an object of type
   Union{MarketBidCost, ThermalGenerationCost}
```

**Result: TYPE-SYSTEM REJECTION** -- Same pattern. The Julia type system enforces that
`ThermalStandard` generators accept only `ThermalGenerationCost` or `MarketBidCost`. This
is correct validation but the error message is a generic Julia type error, not a
domain-specific message like "ThermalStandard requires ThermalGenerationCost, got
RenewableGenerationCost."

#### (b3) Set all costs to zero (degenerate objective)

```julia
set_operation_cost!(gen, ThermalGenerationCost(CostCurve(LinearCurve(0.0)), 0.0, 0.0, 0.0))
# Builds and solves successfully:
# Solve status: RunStatus.SUCCESSFULLY_FINALIZED = 0
# Objective value: 0.0
# Termination: OPTIMAL
```

**Result: SILENT SUCCESS** -- PSI accepts zero-cost generators without warning, builds
the model, and HiGHS solves it to optimality with a zero objective value. There is no
warning that the objective function is trivial (all coefficients zero), no warning that
dispatch is arbitrary (any feasible dispatch is equally optimal), and no warning that
LMPs/duals from a zero-cost problem are degenerate. This compounds with the undocumented
dual unit conversion (see [unit-mismatch A-3](../observations/unit-mismatch-expressiveness-A-3_dcopf.md))
-- a user could get zero LMPs from a zero-cost OPF and not realize the costs are wrong.

**Grade: C.** Type-level errors are caught early (good) but with generic Julia messages
(poor). The zero-cost silent success is the most dangerous error mode -- it produces
plausible-looking results that are economically meaningless.

### Error (c): Invalid Bus Type

**Setup:** Two sub-tests of bus type manipulation.

#### (c1) Set all buses to ISOLATED

```
set_bustype!(bus, ACBusTypes.ISOLATED)
=> InfrastructureSystems.ConflictingInputsError("Branch bus-26-bus-27-i_42 is set available
   and connected to isolated bus bus-26")
```

**Result: MEANINGFUL DIAGNOSTIC** -- PowerFlows.jl validates that branches cannot connect
to isolated buses before attempting the solve. The error message names the specific branch
and bus causing the conflict. This is a clear, actionable diagnostic.

#### (c2) Set a load bus (no generator) as REF

```julia
# bus-20 is a PQ bus with no generator
set_bustype!(bus20, ACBusTypes.REF)
result = solve_powerflow(DCPowerFlow(), sys)
# => DCPF completes successfully with no error or warning
```

**Result: SILENT SUCCESS** -- PowerSystems.jl allows setting a load-only bus (bus-20) as
the reference bus with no validation. The DCPF solves and produces results. In a real
network model, the reference bus should have a generator to absorb the power balance
mismatch. This is a semantic error that the tool does not catch.

**Grade: B.** Structural validation (ISOLATED + connected branch) is excellent.
Semantic validation (REF bus requires generator) is absent but the consequence is a
solvable (if unconventional) problem rather than wrong results.

### Summary

| Error | Classification | Quality Grade | Attribution |
|-------|---------------|--------------|-------------|
| (a) Infeasible OPF | Meaningful diagnostic | A | [tool-specific: PSI validation] |
| (b1) Cost = nothing | Type-system rejection (cryptic) | B- | [tool-specific: Julia type system] |
| (b2) Wrong cost type | Type-system rejection (cryptic) | B- | [tool-specific: Julia type system] |
| (b3) Zero cost | **Silent success** | D | [tool-specific: no semantic validation] |
| (c1) All buses ISOLATED | Meaningful diagnostic | A | [tool-specific: PSI validation] |
| (c2) Load bus as REF | **Silent success** | C | [tool-specific: no semantic validation] |

## Implications

PowerSimulations.jl's error quality is bifurcated. Structural errors that violate the
data model's type system or graph connectivity are caught early with clear messages --
this is a strength of Julia's type system and PSI's validation layer. However, semantic
errors that produce technically valid but meaningless problems (zero costs, wrong
reference bus) pass silently. The zero-cost silent success is particularly concerning
for an energy trading context where cost curve errors could produce incorrect dispatch
and LMP signals without any diagnostic indication.

The automatic serialization of infeasible models to JSON is a notable positive feature
not commonly found in competing tools. This aligns with the architectural quality noted
in [arch-quality B-1](../observations/arch-quality-extensibility-B-1_custom_constraints.md)
-- JuMP model access enables sophisticated debugging. However, the gap between structural
and semantic validation means users must rely on domain knowledge to catch economically
meaningless configurations.

The type-system error messages (b1, b2) illustrate a broader Julia accessibility pattern:
the type system catches errors at the right boundary but reports them in language-level
terms rather than domain-level terms. A user seeing `MethodError: Cannot convert Nothing
to Union{MarketBidCost, ThermalGenerationCost}` must understand Julia's type hierarchy
to diagnose the issue. This is a [tool-specific: Julia ecosystem] friction point that
affects all Julia-based power system tools equally.

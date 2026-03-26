---
test_id: A-10
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "0a550931"
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: 581.1
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 364
solver: HiGHS
timestamp: "2026-03-24T00:00:00Z"
---

# A-10: Lossy DCOPF with LMP Decomposition

## Result: FAIL

## Approach

Investigated all DC OPF formulations available through PowerModels.jl (accessed via
`PowerSimulations.PM`) for loss-approximation capability.

**Formulations checked:**
- `DCPPowerModel` -- angle-based lossless DC OPF
- `DCMPPowerModel` -- matrix-based lossless DC OPF
- `NFAPowerModel` -- network flow approximation (lossless)
- `PTDFPowerModel` -- PTDF-based lossless DC OPF
- `DCPLLPowerModel` -- DC Power with Linearized Losses
- `LPACCPowerModel` -- Linear Programming AC approximation

**DCPLLPowerModel discovered:** PowerModels.jl does provide a `DCPLLPowerModel` formulation
that includes linearized losses. However, this formulation uses **quadratic constraints**
(`ScalarQuadraticFunction-in-GreaterThan`) in the Ohm's law constraint (`constraint_ohms_yt_to`).

**Build failure:** When instantiated through PSI's `DecisionModel`, DCPLLPowerModel fails at
build time because HiGHS (an LP/MILP/QP solver) does not support quadratic constraints
(only quadratic objectives). The error is:

```
build! of the DecisionModel{GenericOpProblem} failed: ModelBuildStatus.FAILED
```

This requires a solver supporting SOCP or general quadratic constraints (e.g., Gurobi, CPLEX,
or potentially SCIP). The evaluation protocol specifies HiGHS as the solver.
[mixed: formulation exists in PowerModels but requires solver with QCP support; HiGHS only supports QP objectives]

**Lossless baseline established:** A standard DCPPowerModel solve completed successfully
(replicating A-3 results) with objective $215,211.33 and LMP range $7.76-$290.11/MWh.

## Output

**PowerModels loss-related symbols found:**
- `DCPLLPowerModel` (type)
- `AbstractDCPLLModel` (abstract type)
- `AbstractAPLossLessModels` (abstract type)
- `constraint_power_losses`, `constraint_power_losses_lb` (functions)
- `constraint_storage_losses`, `constraint_dcline_power_losses` (functions)

**Lossless DCOPF reference (for comparison):**
- Objective: $215,211.33/h
- LMP range: $7.76 - $290.11/MWh
- 2 binding branches at 70% derating

**DCPLLPowerModel attempt:** Build failed -- quadratic constraints not supported by HiGHS.

**v11 pass condition assessment:**
- (a) Loss component signs: Not testable (solve failed)
- (b) Losses 0.5-3% of total load: Not testable
- (c) Lossy objective > lossless objective: Not testable
- (d) LMP decomposition (energy + loss + congestion = total): Not testable

## Workarounds

- **What:** No workaround found. DCPLLPowerModel exists but requires a solver with
  quadratic constraint support (SOCP/QCP). HiGHS supports QP objectives but not
  quadratic constraints.
- **Why:** The linearized loss formulation in PowerModels uses quadratic power-flow
  constraints, which are architecturally incompatible with LP/MILP/QP-only solvers.
- **Durability:** blocking -- The formulation exists but cannot be used with the evaluation
  solver stack (HiGHS, SCIP, GLPK). A commercial solver (Gurobi, CPLEX) or a solver
  supporting SOCP (Mosek, SCS) would be needed. Alternatively, Ipopt could be used but
  it is an NLP solver, not the specified solver for this test.
- **Grade impact:** The tool has a lossy DC formulation but it is unusable with open-source
  LP/MILP solvers. LMP decomposition into energy + loss + congestion components is not
  achievable. This is a partial tool capability -- the formulation exists but the solver
  ecosystem is mismatched.

## Timing

- **Wall-clock:** not applicable (build failed)
- **Timing source:** measured
- **Peak memory:** 581.1 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a10_lossy_dcopf_lmp.jl`

## Observations

- **solver-issues:** HiGHS supports QP objectives but not quadratic constraints. DCPLLPowerModel
  uses `ScalarQuadraticFunction-in-GreaterThan` constraints for the linearized Ohm's law,
  which HiGHS rejects. This is a fundamental solver-formulation mismatch.
  [mixed: tool provides formulation but requires solver not in eval stack]
- **doc-gaps:** The DCPLLPowerModel formulation's solver requirements are not documented.
  The error only appears at build time, after the model is constructed.
- **api-friction:** There is no way to check solver compatibility with a formulation before
  attempting to build the model. The error message is from JuMP/MOI, not from PSI, and
  points to the constraint type rather than the formulation.

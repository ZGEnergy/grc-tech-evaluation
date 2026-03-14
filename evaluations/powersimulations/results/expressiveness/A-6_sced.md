---
test_id: A-6
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "5577e704"
status: qualified_pass
workaround_class: fragile
blocked_by: null
wall_clock_seconds: 1.064
timing_source: measured
peak_memory_mb: 1255.3
convergence_residual: null
convergence_iterations: null
loc: 529
solver: HiGHS
timestamp: "2026-03-14T00:00:00Z"
---

# A-6: Fix Commitment from A-5, Solve ED as LP

## Result: QUALIFIED PASS

## Approach

Two-stage UC-then-ED workflow:

1. **Stage 1 (SCUC):** Identical to A-5 — `DecisionModel` with `ThermalStandardUnitCommitment`,
   `DCPPowerModel`, linear costs (hydro $5, nuclear $10, coal $25, gas CC $40/MWh), 24-hour
   Modified Tiny load profile. `initialize_model=false` + `JuMP.optimize!()` due to PSI
   initialization bug.

2. **Stage 2 (ED):** New `DecisionModel` with `ThermalDispatchNoMin` (LP dispatch), quadratic
   costs (`c2 = c1 * 0.001`). Commitment from Stage 1 enforced by:
   - Extracting `OnVariable__ThermalStandard` from PSI internal variable containers
   - Fixing decommitted generators' `ActivePowerVariable` to 0 via `JuMP.fix()`
   - Adding ramp constraints between consecutive hours via `@constraint` (460 constraints)

**Key observation:** PSI does not provide a built-in UC-to-ED handoff mechanism. The commitment
schedule must be manually extracted and re-applied as JuMP variable fixes. Ramp constraints
in `ThermalDispatchNoMin` are not active by default — they must be added explicitly.

## Output

**UC Stage:** OPTIMAL (MIP gap 0.57%), objective $1,734,875. 3 generators cycle (gen-5, gen-7, gen-10).

**ED Stage:** OPTIMAL, objective $2,545,464 (higher due to quadratic costs).

**Commitment enforcement verified:** All decommitted hours have zero dispatch (29 variables fixed).

**Ramp constraints:** 460 added (2 per generator per inter-hour transition). 1 binding ramp constraint observed, confirming ramp limits are enforced in ED independently of UC.

**ED Dispatch Summary (selected generators):**

| Generator | Bus | Tech | Min MW | Max MW | Mean MW |
|-----------|-----|------|--------|--------|---------|
| gen-1 | 30 | Hydro | 647.3 | 900.0 | 840.3 |
| gen-7 | 36 | Gas CC | 0.0 | 467.8 | 86.1 |
| gen-10 | 39 | Gas CC | 0.0 | 336.0 | 101.5 |
| gen-5 | 34 | Coal | 0.0 | 508.0 | 361.0 |

Gas CC generators dispatch only during committed hours (HR 9-21 for gen-10, HR 15-22 for gen-7),
with zero output during decommitted hours — confirming commitment is correctly enforced.

**LMP extraction:** LMPs from ED stage returned null values. The `initialize_model=false` +
`JuMP.optimize!()` bypass prevents PSI's dual tracking from populating. This is a known
limitation of the fragile workaround — PSI's internal state does not register the solve.

## Workarounds

- **What:** (1) Extracted UC commitment via `PSI.get_variables()` internal API. (2) Fixed
  decommitted generators via `JuMP.fix()`. (3) Added ramp constraints manually via
  `@constraint`. (4) Used `initialize_model=false` and called `JuMP.optimize!()` directly
  for both UC and ED stages.
- **Why:** PSI does not provide a built-in two-stage UC-to-ED workflow. There is no API to
  transfer commitment decisions between models, no way to fix binary variables from a previous
  solve, and no ED-specific formulation that respects an external commitment schedule.
  `ThermalDispatchNoMin` is a pure LP dispatch without commitment awareness.
- **Durability:** fragile — Uses PSI internal APIs (`get_variables`, `get_optimization_container`,
  `get_jump_model`) that are not part of the documented public interface. The JuMP-level
  constraint injection is robust but depends on PSI's internal naming conventions for
  constraint arrays.
- **Grade impact:** The two-stage UC-ED separation is achievable but requires significant
  manual JuMP manipulation. The commitment transfer, variable fixing, and ramp constraint
  addition are all done outside PSI's modeling framework.

## Timing

- **Wall-clock:** 1.064 s total (UC: 0.803 s, ED: 0.261 s, second run after JIT warm-up)
- **Timing source:** measured
- **Peak memory:** 1255.3 MB (Julia process RSS)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a6_sced.jl`

Key API pattern:
```julia
# Stage 1: SCUC
uc_model = build_and_solve_scuc(sys_uc, solver)
commitment, gen_names, tsteps = extract_commitment(uc_model)

# Stage 2: ED with fixed commitment
# Fix decommitted hours to zero
JuMP.fix(p_arr[gname, t], 0.0; force=true)

# Add ramp constraints manually
@constraint(jm, p_arr[gname, t_curr] - p_arr[gname, t_prev] <= ramp_limit)
@constraint(jm, p_arr[gname, t_prev] - p_arr[gname, t_curr] <= ramp_limit)

JuMP.optimize!(jm)
```

## Observations

- **api-friction:** No built-in UC-to-ED handoff. The commitment schedule must be manually
  extracted, serialized, and re-applied as JuMP constraints in a second model.
- **workaround-needed:** Ramp constraints in ThermalDispatchNoMin are not active by default.
  For a proper ED formulation respecting ramp limits, constraints must be manually added
  via JuMP.
- **api-friction:** LMP extraction fails when using `initialize_model=false` +
  `JuMP.optimize!()`. PSI's dual tracking does not populate, requiring direct JuMP dual
  access for LMP recovery.

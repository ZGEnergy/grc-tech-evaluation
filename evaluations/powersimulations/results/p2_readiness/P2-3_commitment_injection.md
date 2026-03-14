---
test_id: P2-3
tool: powersimulations
dimension: p2_readiness
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "4a4fe24e"
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
depends_on: A-5
---

# P2-3: Commitment Injection Workflow (SCUC -> DCOPF -> ACPF)

## Result: INFORMATIONAL

## Capability Assessment

| Step | Capability | API Friction | Effort |
|------|-----------|-------------|--------|
| 1. SCUC (commit schedule) | Yes (A-5) | High -- requires `initialize_model=false` + `JuMP.optimize!()` bypass | Done |
| 2. Lock commitment -> DCOPF | Yes (A-6) | High -- manual `JuMP.fix()` on decommitted generators | Done |
| 3. DCOPF dispatch -> ACPF | Yes (A-4) | Low -- shared System object, `set_active_power!()` + `solve_powerflow()` | Done |
| Full 3-step chain | Yes, with workarounds | High overall | Medium |

## Step-by-Step Analysis

### Step 1: SCUC Produces Commitment Schedule

**Source:** A-5 (24-hour SCUC with Modified Tiny Data)

- **Formulation:** `ThermalStandardUnitCommitment` (built-in, includes binary on/off/start/stop
  variables, ramp constraints, min up/down time constraints)
- **Solver:** HiGHS with 1% MIP gap tolerance
- **Result:** OPTIMAL (MIP gap 0.57%), 3 of 10 generators cycle
- **Workaround required:** `initialize_model=false` + direct `JuMP.optimize!()` because
  PSI's initialization solve fails with HiGHS. Results extracted via internal API
  `PSI.get_variables()` because bypassing `solve!()` breaks PSI's result tracking.
- **Workaround class:** Fragile -- uses internal APIs not part of the public interface

### Step 2: Lock Commitment -> Solve DCOPF (Economic Dispatch)

**Source:** A-6 (Fix Commitment from A-5, Solve ED as LP)

- **Commitment transfer method:** Manual extraction of `OnVariable__ThermalStandard` from
  PSI internal containers, then `JuMP.fix()` to set decommitted generators' dispatch to zero
- **Ramp constraints:** Must be manually added via `@constraint` (460 constraints for 10 gens
  x 23 transitions x 2 directions) because `ThermalDispatchNoMin` does not include ramp
  limits by default
- **Result:** OPTIMAL, all commitment decisions correctly enforced (29 zero-dispatch hours verified)
- **Workaround required:** No built-in UC-to-ED handoff API exists. The entire commitment
  transfer is manual JuMP manipulation:
  ```julia
  JuMP.fix(p_arr[gname, t], 0.0; force=true)  # for decommitted hours
  @constraint(jm, p_arr[gname, t] - p_arr[gname, t-1] <= ramp_limit)  # manual ramp
  ```
- **Workaround class:** Fragile -- depends on PSI internal naming conventions for variables
  and requires direct JuMP model access

### Step 3: DCOPF Dispatch -> AC Power Flow

**Source:** A-4 (AC Feasibility Check on DC OPF Dispatch)

- **Dispatch transfer method:** `set_active_power!(gen, dispatch_pu)` on the shared
  `PowerSystems.System` object (MW to per-unit conversion required)
- **AC power flow:** `solve_powerflow(ACPowerFlow(), sys)` from PowerFlows.jl
- **Result:** ACPF converges, 5 voltage violations (max 0.014 pu over), 3 thermal violations
  (max 102.8% loading), 1 reactive power violation
- **Workaround required:** None for this step. The shared System data model makes
  DCOPF-to-ACPF seamless.
- **Workaround class:** None

## End-to-End Workflow Assessment

### What Works Well

1. **Shared data model:** All three Sienna packages (PowerSystems, PowerSimulations,
   PowerFlows) operate on the same `System` object. No file export/reimport between steps.
2. **SCUC formulation quality:** `ThermalStandardUnitCommitment` is a complete built-in
   formulation with binary commitment, ramp, and min up/down constraints.
3. **ACPF convergence:** The DC dispatch produces a feasible AC operating point on first
   attempt with flat start.

### What Requires Manual Work

1. **UC initialization bypass:** PSI's initialization model fails with HiGHS, requiring
   `initialize_model=false` and direct JuMP optimization.
2. **Commitment extraction:** No public API to read commitment results. Must access PSI
   internal containers via `PSI.get_variables()`.
3. **Commitment injection:** No API to fix commitment decisions in a subsequent ED model.
   Must use `JuMP.fix()` on individual dispatch variables for decommitted hours.
4. **Ramp constraints:** The LP dispatch formulation (`ThermalDispatchNoMin`) does not
   include ramp limits. They must be manually added via JuMP `@constraint`.
5. **LMP extraction:** Bypassing `solve!()` breaks PSI's dual tracking. LMPs from the ED
   stage return null; direct JuMP dual access would be needed.

### API Friction Summary

| Operation | Public API? | Internal API? | Manual JuMP? |
|-----------|------------|--------------|-------------|
| Build SCUC model | Yes | -- | -- |
| Solve SCUC | -- | -- | Yes (`JuMP.optimize!`) |
| Extract commitment | -- | Yes (`PSI.get_variables`) | -- |
| Build ED model | Yes | -- | -- |
| Inject commitment | -- | -- | Yes (`JuMP.fix`) |
| Add ramp constraints | -- | -- | Yes (`@constraint`) |
| Solve ED | -- | -- | Yes (`JuMP.optimize!`) |
| Transfer dispatch to ACPF | Yes (`set_active_power!`) | -- | -- |
| Solve ACPF | Yes (`solve_powerflow`) | -- | -- |

**5 of 9 operations require manual JuMP manipulation or PSI internal APIs.**

## Effort Estimate for Production Workflow

| Component | Effort | Notes |
|-----------|--------|-------|
| SCUC with initialization workaround | Done (A-5 pattern) | Could be eliminated by using GLPK for initialization |
| UC-to-ED commitment transfer | 2-3 days | Needs robust extraction + injection utility |
| Ramp constraint injection | 1-2 days | Template of per-generator ramp constraints |
| LMP extraction from ED | 1-2 days | Direct JuMP dual access needed |
| End-to-end pipeline integration | 1 week | Error handling, logging, validation |
| **Total** | **2-3 weeks** | For a robust, tested pipeline |

### Alternative: PSI Simulation API

PSI provides a `SimulationModels` + `SimulationSequence` API designed for multi-stage
problems (e.g., DA -> RT). This API includes built-in feedforward mechanisms
(`SemiContinuousFeedforward`, `FixValueFeedforward`) that could potentially handle
commitment transfer between stages. However:

- The Simulation API was not tested in Phase 1 (it requires `PowerSystemCaseBuilder`
  test systems for the documented examples)
- It is designed for rolling-horizon simulations, not single-shot UC-ED chains
- Whether `FixValueFeedforward` can lock binary commitment variables into an LP dispatch
  model would need to be verified

## Implications for Phase 2

The three-step commitment injection workflow is **achievable but requires significant
manual JuMP manipulation**. The core capability exists -- PSI can solve SCUC, the shared
System object enables seamless dispatch transfer to ACPF, and all individual steps produce
correct results. The friction is in the commitment handoff between SCUC and ED, where PSI
provides no public API and requires direct JuMP model access.

For a production deployment, the recommended approach would be:
1. Build a thin utility layer that wraps the JuMP manipulation (commitment extraction,
   variable fixing, ramp constraint injection)
2. Investigate the `SimulationSequence` + feedforward API as a potentially cleaner
   alternative for the UC-ED handoff
3. Consider using GLPK for the initialization solve to eliminate the `initialize_model=false`
   workaround, then switch to HiGHS for the main solve

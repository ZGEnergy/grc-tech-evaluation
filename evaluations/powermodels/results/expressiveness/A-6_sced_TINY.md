---
test_id: A-6
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 4.909
peak_memory_mb: null
loc: 406
solver: HiGHS
timestamp: "2026-03-06T00:00:00Z"
---

# A-6: SCED (Economic Dispatch with Fixed Commitment) on TINY (IEEE 39-bus)

## Result: QUALIFIED PASS

PowerModels.jl has **no built-in SCED capability**. Like A-5, the entire formulation was user-assembled using JuMP. The UC-ED two-stage decomposition was implemented manually: (1) solve MILP unit commitment to obtain a binary commitment schedule, then (2) fix the commitment as parameters in a separate LP model and re-solve for economic dispatch with independently enforced ramp rate constraints.

## Approach

1. **UC stage (MILP):** Reproduced the A-5 SCUC formulation to obtain the commitment schedule. Same constraints: min up/down times, startup/shutdown, ramp rates, reserve requirements, DC power flow, branch limits. Linearized costs (HiGHS cannot solve MIQP).
2. **ED stage (LP):** Built a new JuMP model with:
   - Fixed commitment: generators with `commitment[g][t] == 0` have `pg` fixed to 0; committed generators bounded by `[pmin, pmax]`
   - DC power flow constraints (same network topology)
   - Branch flow limits
   - **Ramp rate constraints independently enforced** in the ED stage (not inherited from UC):
     - Between consecutive committed periods: `|pg[g,t] - pg[g,t-1]| <= 0.5 * pmax[g]`
     - Startup ramp: `pg[g,t] <= ramp_limit` when transitioning from off to on
     - Shutdown ramp: `pg[g,t-1] <= ramp_limit` when transitioning from on to off
   - Objective: minimize linearized generation cost (no startup costs in ED)
3. **Solver:** HiGHS with `time_limit=300s, presolve="on", threads=1`

## Output

- **UC termination:** OPTIMAL
- **ED termination:** OPTIMAL
- **ED objective:** 37,225.18 (linearized cost, same as UC since costs are linear)
- **ED solve time:** 0.012s (HiGHS LP)
- **Commitment schedule:** 10 generators x 24 hours
  - 8 generators committed all 24 hours
  - Gen 4 and Gen 8 decommitted in hours 23-24 (low demand)
- **Ramp constraints binding:** 77 instances across all generators and periods
  - Example: Gen 1 period 7: ramp = 5.2 p.u. = limit (binding)
  - Example: Gen 1 period 9: ramp = 5.2 p.u. = limit (binding)
- **UC-ED dispatch differences:** 170 (gen, period) pairs differ between UC and ED dispatch
  - This demonstrates the ED is truly re-optimizing with the fixed commitment, not just replaying the UC solution
- **UC-ED cleanly separable:** Yes -- the two-stage workflow is cleanly implementable

## Workarounds

1. **No built-in SCED (stable workaround):** PowerModels provides no economic dispatch or unit commitment formulation. The entire two-stage UC+ED workflow was built from scratch in JuMP. PowerModels contributed only MATPOWER file parsing (`parse_file`). This required ~200 lines of manual JuMP code for both stages combined.

2. **Cost linearization (stable workaround):** Same as A-5 -- HiGHS cannot solve MIQP, so quadratic generator costs were linearized. The ED stage is LP (no integer variables), so a QP-capable solver like Gurobi could handle quadratic costs directly.

## What PowerModels Contributed vs. What Was Manual

| Component | Source |
|-----------|--------|
| MATPOWER parsing | PowerModels (`parse_file`) |
| Network topology data | PowerModels (parsed `Dict`) |
| UC formulation (MILP) | Manual (JuMP) |
| ED formulation (LP) | Manual (JuMP) |
| Commitment schedule transfer | Manual (extract binary values, fix in LP) |
| Ramp rate constraints (ED) | Manual (JuMP, independently enforced) |
| DC power flow constraints | Manual (JuMP) |
| Branch flow limits | Manual (JuMP) |

## Timing

- Wall-clock: ~5s (UC + ED + data parsing, excludes JIT)
- UC solve time: ~0.09s (HiGHS MIP)
- ED solve time: 0.012s (HiGHS LP)
- Peak memory: not measured

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a6_sced.jl`

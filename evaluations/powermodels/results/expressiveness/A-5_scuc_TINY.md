---
test_id: A-5
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 4.909
peak_memory_mb: null
loc: 295
solver: HiGHS
mip_gap: 0.0
timestamp: "2026-03-06T00:00:00Z"
---

# A-5: 24-hour SCUC (Unit Commitment) on TINY (IEEE 39-bus)

## Result: QUALIFIED PASS

PowerModels.jl has **no built-in SCUC capability**. It is a steady-state OPF tool. The entire SCUC formulation was user-assembled using JuMP, with PowerModels providing only data parsing (`parse_file`) and basic network utilities (`make_basic_network`). This is a significant expressiveness limitation: ~140 lines of manual JuMP code were required to implement what other tools may provide natively.

## Approach

1. **Data parsing:** `PowerModels.parse_file("case39.m")` for network topology, generator parameters, and branch data
2. **Load profile:** Applied a 24-hour demand profile (0.56-1.00 scaling) to all loads
3. **Manual JuMP formulation (MILP):**
   - Decision variables: `pg[g,t]` (generation), `u[g,t]` (binary commitment), `v_start[g,t]` (startup), `v_shut[g,t]` (shutdown), `theta[b,t]` (bus angles)
   - DC power flow constraints built manually using branch susceptances from parsed data
   - Branch flow limits enforced
   - Generator output linked to commitment: `pmin*u <= pg <= pmax*u`
   - Startup/shutdown variable linking
   - Minimum up-time: 3 hours
   - Minimum down-time: 2 hours
   - Ramp rates: 50% of Pmax per hour
   - Reserve requirement: 10% of total load per period
4. **Cost linearization:** Generator quadratic costs were linearized (linear term only) because HiGHS cannot solve MIQP problems. This is a necessary workaround.
5. **Solver:** HiGHS with `mip_rel_gap=0.01`, `time_limit=300s`

## Output

- **Termination status:** OPTIMAL
- **Objective value:** 37,225.18 (linearized cost)
- **MIP gap:** 0.0% (well within 1% requirement)
- **Solve time:** 0.093s (HiGHS)
- **Commitment schedule:** 10 generators x 24 hours binary matrix extracted
  - 8 generators committed all 24 hours
  - 2 generators (Gen 4, Gen 8) decommitted in hours 23-24 (low demand)
- **Committed units per period:** 10 for hours 1-22, 8 for hours 23-24
- **Total startups:** 0 (all units assumed initially on; shutdowns occur but no re-starts needed)
- **Dispatch schedule:** Time-varying generation matching load profile with ramp constraints

## Workarounds

1. **No built-in SCUC (stable workaround):** PowerModels provides no unit commitment formulation. The entire SCUC was built from scratch in JuMP. PowerModels contributed only MATPOWER file parsing. This is a fundamental design choice -- PowerModels focuses on steady-state OPF, and UC is delegated to the separate `UnitCommitment.jl` package (ANL-CEEESA).

2. **Cost linearization (stable workaround):** HiGHS cannot solve MIQP (mixed-integer quadratic programs). The quadratic generator cost terms from case39.m were dropped, keeping only the linear cost coefficient. A production implementation would use a MIQP-capable solver (Gurobi, CPLEX) or piecewise-linear cost approximation.

## What PowerModels Contributed vs. What Was Manual

| Component | Source |
|-----------|--------|
| MATPOWER parsing | PowerModels (`parse_file`) |
| Network topology (bus/branch/gen data) | PowerModels (parsed `Dict`) |
| Basic network utilities | PowerModels (`make_basic_network`) |
| DC power flow constraints | Manual (JuMP) |
| Branch flow limits | Manual (JuMP) |
| Binary commitment variables | Manual (JuMP) |
| Min up/down time constraints | Manual (JuMP) |
| Startup/shutdown linking | Manual (JuMP) |
| Ramp rate constraints | Manual (JuMP) |
| Reserve requirements | Manual (JuMP) |
| Objective function | Manual (JuMP, linearized) |

## Timing

- Wall-clock: 4.909s (including parse, model build, solve; excludes JIT)
- Solve time: 0.093s (HiGHS MIP)
- Peak memory: not measured
- MIP nodes: 1
- LP iterations: 670

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a5_scuc.jl`

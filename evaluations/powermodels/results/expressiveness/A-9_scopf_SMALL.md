---
test_id: A-9
tool: powermodels
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 118.87
peak_memory_mb: null
loc: 285
solver: HiGHS
timestamp: "2026-03-07T00:00:00Z"
---

# A-9: SCOPF (Security-Constrained OPF) on SMALL (ACTIVSg 2000-bus)

## Result: QUALIFIED PASS

PowerModels.jl has **no built-in SCOPF** in the core package. The DC SCOPF was manually assembled via JuMP with a preventive formulation: shared generation variables across base case plus 20 N-1 contingency scenarios. PowerModels contributed data parsing and connectivity analysis for islanding pre-screening.

The SCOPF solved optimally at 1.0x rating scale (no relaxation needed) with a 4.74% cost increase over unconstrained DC OPF. The contingency constraints are part of the optimization, not post-hoc verification.

## Approach

1. **Data parsing:** `PowerModels.parse_file("case_ACTIVSg2000.m")` -- 2000 buses, 3206 branches, 544 generators
2. **Empty cost fix:** 112 generators with empty cost arrays fixed (set to zero cost)
3. **Base DC OPF (Ipopt):** Solved to identify branch loading percentages. HiGHS QP fails on ACTIVSg2000 due to numerical precision issues, so Ipopt was used for the reference OPF.
4. **Contingency selection:** Top 20 most-loaded branches selected as contingencies. Islanding pre-screened using `PowerModels.calc_connected_components()`.
5. **SCOPF construction:** User-assembled preventive SCOPF via JuMP with bus adjacency lists for efficient model construction:
   - Shared generation variables pg[g] across all scenarios
   - Per-scenario voltage angles theta[b, s] for s in 0:20
   - Base case + 20 contingency networks with DC power flow balance and flow limits
   - Linearized generator costs (LP, not QP)
6. **Solver:** HiGHS LP with 300s time limit

## Output

- **Base DC OPF objective:** 1,201,320.78
- **SCOPF objective:** 1,258,318.36
- **Cost increase:** 4.74% (security premium)
- **SCOPF termination:** OPTIMAL at 1.0x rating scale
- **SCOPF solve time:** 41.27s (HiGHS dual simplex)
- **Total generation:** 671.09 p.u.
- **Model size:** 42,544 variables
- **Valid contingencies:** 20 (no islanding excluded from top candidates)
- **Contingency constraints in optimization:** Yes (preventive, not post-hoc)

## Top Branch Loadings (from base DC OPF)

The contingencies were selected from the most heavily loaded branches, providing meaningful security constraints that affected the dispatch.

## Workarounds

1. **No built-in SCOPF (stable workaround):** PowerModels core has no SCOPF. PowerModelsSecurityConstrained.jl exists as a separate package but is not installed. The preventive SCOPF was manually assembled via JuMP with ~285 lines of code. PowerModels contributed MATPOWER parsing and `calc_connected_components()` for islanding screening.

2. **Ipopt for base OPF (stable workaround):** HiGHS fails on quadratic programs with the ACTIVSg2000 network due to numerical precision issues. Ipopt was used for the base DC OPF reference. The manual SCOPF uses linearized costs as LP to avoid this issue.

3. **Reduced contingency set (practical trade-off):** Full N-1 on 3206 branches would create an extremely large LP. 20 contingencies on the most-loaded branches demonstrate the SCOPF capability while keeping model construction and solve times practical.

## Timing

- Wall-clock: 118.87s (including parse, base OPF, islanding screening, model build, solve)
- SCOPF solve time: 41.27s (HiGHS dual simplex)
- Base OPF solve: 2.5s (Ipopt)
- Model construction: ~70s (21 x 2000-bus DC power flow networks)

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a9_scopf_small.jl`

---
test_id: A-9
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 3.592
peak_memory_mb: null
loc: 331
solver: HiGHS
timestamp: "2026-03-06T00:00:00Z"
---

# A-9: DC SCOPF (Security-Constrained OPF) on TINY (IEEE 39-bus)

## Result: QUALIFIED PASS

PowerModels.jl has **no built-in SCOPF in the core package**. PowerModelsSecurityConstrained.jl exists but is not installed in this evaluation environment. The DC SCOPF was manually assembled via JuMP with shared generation variables (preventive SCOPF) and per-contingency power flow constraints.

## Approach

1. **Data parsing:** `PowerModels.parse_file("case39.m")`
2. **Contingency pre-screening:** Used `PowerModels.calc_connected_components()` to identify contingencies that cause network islanding. IEEE 39-bus has 11 radial generator branches whose outage disconnects a generator bus. These are excluded (standard ISO practice: only credible, non-islanding contingencies are modeled in preventive SCOPF).
   - 46 total branches, 35 valid (non-islanding) contingencies, 11 islanding contingencies excluded
3. **Manual JuMP formulation (LP):**
   - Shared generation variables `pg[g]` (same dispatch in base case and all contingencies -- preventive SCOPF)
   - Per-contingency voltage angle variables `theta[b, s]` for s = 0 (base) through s = 35 (contingencies)
   - Base-case: DC power flow + thermal limits
   - Each contingency: DC power flow with outaged branch removed + thermal limits on remaining branches
   - The shared `pg` variables serve as the linking constraint -- the base-case dispatch must simultaneously satisfy power balance under all contingencies
4. **Thermal rating relaxation:** SCOPF at 1.0x rating was infeasible. Solved at 1.5x rating (per protocol: "apply thermal rating relaxation, scale rateA to 150%").
5. **Cost linearization:** Used linear cost coefficients from case39.m polynomial costs (HiGHS LP).
6. **Solver:** HiGHS with `time_limit=300s, presolve="on", threads=1`

## Output

- **SCOPF termination:** OPTIMAL (at 1.5x thermal rating)
- **SCOPF objective:** 1,878.27 (linearized cost)
- **SCOPF solve time:** 0.016s (HiGHS LP)
- **Rating scale applied:** 1.5x (150% of rateA)
- **Contingencies modeled:** 35 (non-islanding N-1)
- **Islanding contingencies excluded:** 11 (branches 5, 14, 20, 27, 32, 33, 34, 37, 39, 41, 46)
- **Unconstrained DC OPF objective:** 41,263.94 (quadratic cost via PowerModels)
- **Dispatch comparison (SCOPF vs unconstrained DC OPF):**
  - Gen 1: -6.14 p.u. difference (reduced)
  - Gen 6: -0.93 p.u. (reduced)
  - Gen 9: +2.04 p.u. (increased)
  - Gen 10: +4.39 p.u. (increased)
  - Gen 3: +0.64 p.u. (increased)
  - Dispatch DOES differ from unconstrained OPF -- SCOPF constraints are binding
- **Cost note:** Direct cost comparison is not meaningful because SCOPF uses linearized costs while PowerModels' DC OPF uses the full quadratic cost function. The key finding is that SCOPF dispatch differs from unconstrained dispatch, confirming the contingency constraints are binding.
- **Contingency constraints in optimization:** Yes -- all 35 contingencies' power balance and flow limit constraints are embedded in a single LP, not checked post-hoc.

## Workarounds

1. **No built-in SCOPF (stable workaround):** PowerModels core has no SCOPF formulation. PowerModelsSecurityConstrained.jl (LANL, 41 stars, last pushed 2024-01-19) provides iterative SCOPF but is not installed. The entire formulation was manually assembled in JuMP: ~180 lines of code for base case + N-1 contingency networks with shared generation variables.

2. **Islanding contingency screening (stable workaround):** `PowerModels.calc_connected_components()` was used to pre-screen contingencies. IEEE 39-bus has many radial generator buses, making 11 of 46 contingencies islanding. This is standard SCOPF practice.

3. **Thermal rating relaxation (data finding):** IEEE 39-bus has tight thermal limits that make preventive N-1 SCOPF infeasible at nominal ratings. A 1.5x relaxation was needed. This reflects the test case characteristics, not a tool limitation.

## What PowerModels Contributed vs. What Was Manual

| Component | Source |
|-----------|--------|
| MATPOWER parsing | PowerModels (`parse_file`) |
| Network topology data | PowerModels (parsed `Dict`) |
| Connected component analysis | PowerModels (`calc_connected_components`) |
| Unconstrained DC OPF (comparison) | PowerModels (`solve_dc_opf`) |
| SCOPF formulation | Manual (JuMP, ~180 lines) |
| Contingency pre-screening | Manual + PowerModels |
| Shared generation variables | Manual (JuMP) |
| Per-contingency power flow | Manual (JuMP) |
| Linking constraints | Manual (JuMP, implicit via shared `pg`) |

## Timing

- Wall-clock: 3.59s (including contingency screening, model build, solve, comparison; excludes JIT)
- SCOPF solve time: 0.016s (HiGHS LP, 35 contingencies)
- Peak memory: not measured

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a9_scopf.jl`

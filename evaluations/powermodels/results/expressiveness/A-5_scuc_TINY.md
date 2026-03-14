---
test_id: A-5
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: v10
skill_version: v1
test_hash: b1978b9f
status: qualified_pass
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 1.466
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 250
solver: HiGHS
timestamp: 2026-03-13T18:00:00Z
---

# A-5: 24-Hour SCUC as MILP

## Result: QUALIFIED PASS

## Approach

PowerModels.jl v0.21.5 does NOT natively support SCUC. The entire unit commitment formulation was user-assembled as a JuMP MILP, using PowerModels only for MATPOWER data parsing (`parse_file`). PowerModels' multi-network infrastructure (`replicate`) was evaluated but not used -- the custom JuMP model with explicit time indexing was more direct and required fewer workarounds than adapting PowerModels' multi-network OPF to include binary commitment variables.

### Implementation

1. **Data loading:** `PowerModels.parse_file("case39.m")` for network topology and impedance data. Modified Tiny augmentation applied from `gen_temporal_params.csv` (differentiated costs, UC parameters) and `load_24h.csv` (24-hour load profile).

2. **Custom JuMP MILP with the following constraint types** (all user-assembled):

   | Constraint | Type | Description |
   |-----------|------|-------------|
   | Commitment bounds | User-assembled | `Pmin * u[g,t] <= pg[g,t] <= Pmax * u[g,t]` |
   | Startup/shutdown logic | User-assembled | `v[g,t] - w[g,t] = u[g,t] - u[g,t-1]` |
   | Minimum up time | User-assembled | Rolling sum: `sum(v[g,tau] for tau in t-L+1:t) <= u[g,t]` |
   | Minimum down time | User-assembled | Rolling sum: `sum(w[g,tau] for tau in t-L+1:t) <= 1-u[g,t]` |
   | Ramp rates | User-assembled | `pg[g,t] - pg[g,t-1] <= ramp + Pmax*v[g,t]` |
   | Power balance | User-assembled | Nodal balance with B-theta DC power flow |
   | Thermal limits | User-assembled | `|b*(theta_f - theta_t)| <= rate_a` per branch per hour |

3. **Objective:** Minimize total cost = marginal cost + no-load cost + startup cost over 24 hours.

4. **Solver:** HiGHS with `mip_rel_gap = 0.01` (1%), `time_limit = 300s`, `threads = 1`.

### Generator cycling guardrail

Per cross-tool-watchpoints.md, case39 has a high capacity-to-load ratio (7,367 MW capacity vs 6,254 MW peak load). With differentiated costs from Modified Tiny data (hydro $5, nuclear $10, coal $25, gas CC $40 $/MWh), the optimizer has economic incentive to decommit expensive gas and coal units during low-load hours. Nuclear units (min_up = 24h, min_down = 48h) cannot cycle within a 24-hour horizon; gas CC units (min_up = 4-8h, min_down = 2-5h) can.

## Output

| Metric | Value |
|--------|-------|
| Termination status | OPTIMAL |
| Objective | $1,621,465/24h |
| MIP gap | 0.004% (well below 1% threshold) |
| Solve time (HiGHS) | 0.077s |
| Wall clock | 1.466s (includes JIT) |
| Variables | 1,896 (240 binary) |
| Constraints | 5,450 |
| LP iterations | 200 |
| B&B nodes | 1 |

### Commitment schedule (binary matrix)

```
Gen | Tech       | H1  H2  H3  H4  H5  H6  H7  H8  H9  H10 H11 H12 H13 H14 H15 H16 H17 H18 H19 H20 H21 H22 H23 H24
  1 | hydro      |  1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1
  2 | nuclear    |  1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1
  3 | nuclear    |  1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1
  4 | coal       |  1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   0  <-- cycles
  5 | coal       |  1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1
  6 | nuclear    |  1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1
  7 | gas_CC     |  1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   0   0   0  <-- cycles
  8 | nuclear    |  1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1
  9 | nuclear    |  1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1
 10 | gas_CC     |  1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   0   0  <-- cycles
```

**3 generators cycle** (exceeds the >= 2 requirement):
- Gen 4 (coal, bus 33): shuts down at H24 (1 transition)
- Gen 7 (gas CC, bus 36): shuts down at H22, stays off H22-H24 (1 transition)
- Gen 10 (gas CC, bus 39): shuts down at H23, stays off H23-H24 (1 transition)

Total shutdowns: 3. Total startups: 0 (generators only decommit toward end of horizon, no recommitment needed within 24h).

The cycling pattern is economically rational: gas CC units ($40/MWh) are the most expensive and are shed first during late-night low-load hours (H22-H24 system load drops to 4,591-5,264 MW, well below the 6,187 MW capacity of the remaining committed units).

## Workarounds

- **What:** Entire SCUC formulation is user-assembled as a JuMP MILP (~250 LOC of model construction code). PowerModels provides only data parsing.
- **Why:** PowerModels v0.21.5 is a steady-state single-period power network optimization library. Unit commitment -- requiring binary commitment variables, minimum up/down time constraints, startup/shutdown costs, and multi-period coupling -- falls outside its scope. No `build_uc`, `build_scuc`, or `solve_uc` functions exist.
- **Durability:** blocking -- No API path exists (public or private) to achieve SCUC without assembling the full MILP from scratch. PowerModels' `replicate()` multi-network infrastructure provides multi-period data structure but no UC constraints. The workaround requires writing a substantial custom optimization problem.
- **Grade impact:** C or below for the SCUC sub-question. The tool's JuMP foundation makes the user-assembly feasible (JuMP's constraint API is excellent), but the lack of any built-in UC capability is a significant expressiveness gap.

## Timing

- **Wall-clock:** 1.466s (first invocation, includes JIT)
- **HiGHS solve only:** 0.077s
- **Timing source:** measured
- **Peak memory:** not measured
- **MIP gap:** 0.004%
- **LP iterations:** 200
- **B&B nodes:** 1
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a5_scuc_tiny.jl`

Key structure (showing the user-assembly effort required):

```julia
# PowerModels used ONLY for data parsing
data = PowerModels.parse_file(network_file)

# Everything else is raw JuMP:
model = Model(HiGHS.Optimizer)
@variable(model, u[1:G, 1:T], Bin)           # commitment
@variable(model, v[1:G, 1:T] >= 0)           # startup
@variable(model, w[1:G, 1:T] >= 0)           # shutdown
@variable(model, pg[1:G, 1:T] >= 0)          # dispatch
@variable(model, theta[1:N, 1:T])            # angles

# ~100 lines of constraint construction:
# commitment bounds, startup/shutdown logic, min up/down,
# ramp rates, nodal power balance, thermal limits

optimize!(model)
commitment_matrix = [round(Int, value(u[g,t])) for g in 1:G, t in 1:T]
```

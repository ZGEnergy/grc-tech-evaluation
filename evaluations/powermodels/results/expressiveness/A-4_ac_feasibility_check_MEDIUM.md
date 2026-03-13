---
test_id: A-4
tool: powermodels
dimension: expressiveness
network: MEDIUM
protocol_version: "v9"
skill_version: v1
test_hash: 2e877921
status: fail
workaround_class: blocking
blocked_by: A-2_medium_acpf_failure
wall_clock_seconds: 2084.33
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 195
solver: Ipopt (build_pf / ACPPowerModel)
timestamp: 2026-03-12T00:00:00Z
---

# A-4: AC Feasibility Check — MEDIUM

## Result: FAIL

## Approach

The test implements the same in-memory workflow as TINY: (1) reproduce A-3 MEDIUM DC OPF dispatch, (2) fix generator outputs to that dispatch, (3) attempt ACPF with Ipopt.

### Step 1 — DC OPF (reproduced A-3 MEDIUM exactly):

Applied the same preprocessing (2462 branches rate_a→9999 MVA, 1130 generators cost-linearized from QP→LP). Solved with HiGHS:

```

DC OPF status:    OPTIMAL
DC OPF objective: $2,401,337.08/h
DC OPF wall clock: 10.03s (JIT-warmed run)
Total dispatch:   150,916.88 MW (1937 generators)

```

#### Step 2 — Fix generator dispatch (in per-unit):

Generator pg values transferred in per-unit from DC OPF result to data dict. pmin == pmax == pg_dispatch set to pin active power. Unit consistency confirmed: baseMVA=100, DC OPF result and ACPF data dict use the same per-unit base.

#### Step 3 — Ipopt-based ACPF attempt:

Given A-2 MEDIUM's failure (compute_ac_pf / NLsolve cannot converge on 10k-bus), the test used the alternative Ipopt-based path:

```julia

ac_result = PowerModels.solve_model(
    data, PowerModels.ACPPowerModel, ipopt_opt, PowerModels.build_pf;
    setting = Dict("output" => Dict("branch_flows" => true))
)

```

Ipopt settings: max_iter=10000, tol=1e-6, acceptable_tol=1e-4, max_cpu_time=300s (but actual CPU time was 2059.82s due to Ipopt's restoration phase not being interrupted by the CPU limit during MUMPS reallocation loops).

#### What happened:

Ipopt diverged numerically. The primal infeasibility started at 7.01e+02 (the fixed-dispatch AC equations are highly infeasible from flat start). Dual infeasibility grew catastrophically:

| Iter | inf_pr | inf_du |
|------|--------|--------|
| 0 | 7.01e+02 | 0.00e+00 |
| 5 | 2.60e+01 | 1.95e+04 |
| 10 | 1.93e+01 | 3.60e+10 |
| 13 | 1.97e+02 | 6.97e+14 |
| 14 | 2.03e+04 | 9.90e+20 |

At iter 12–13, Ipopt entered watchdog restoration mode (`w` flag). The MUMPS linear solver ran out of memory and reallocated 4 times (icntl[13] doubled repeatedly: 1000→2000→4000→8000→16000). By iter 14, dual infeasibility reached 9.90e+20 and Ipopt hit `EXIT: Maximum CPU time exceeded` after 2035s CPU time (2093.72s wall clock).

**Root cause:** The ACPF formulation with pmin=pmax=pg_dispatch (generators as PV buses with fixed P) creates a highly constrained NLP where Ipopt cannot find a feasible interior point from flat start. The fixed dispatch from the DC OPF leaves no reactive slack for voltage regulation, and the flat-start point is very far from the AC solution manifold for a 10,000-bus network.

## Output

| Metric | Value |
|--------|-------|
| Buses | 10000 |
| Branches | 12706 |
| Generators (total) | 2485 |
| Generators dispatched | 1937 |
| Base MVA | 100 |
| Preprocessing: rate_a fixed | 2462 |
| Generators cost-linearized | 1130 |
| DC OPF status | OPTIMAL |
| DC OPF objective | $2,401,337.08/h |
| DC OPF wall clock | 10.03s |
| Total dispatch transferred | 150,916.88 MW |
| Ipopt ACPF method | solve_model(ACPPowerModel, build_pf) |
| Ipopt ACPF status | TIME_LIMIT (converged=false) |
| Ipopt iterations | 14 (all diverging) |
| Ipopt CPU time | 2059.82s |
| Ipopt wall clock | 2071.38s |
| Final inf_pr | 17.40 (unscaled) |
| Final inf_du | 1.35e+12 (unscaled) |
| Total wall clock | 2084.33s (~34.7 minutes) |

## Workarounds

- **What:** Ipopt-based ACPF attempted via `solve_model(ACPPowerModel, build_pf)` instead of `compute_ac_pf` (NLsolve), after NLsolve was known to fail at MEDIUM scale (A-2 MEDIUM FAIL).
- **Why:** `compute_ac_pf` uses NLsolve which cannot solve 10k-bus ACPF. The Ipopt path via `build_pf` was the only alternative within PowerModels.jl.
- **Durability:** blocking — Ipopt also fails at MEDIUM scale for this problem formulation. Neither available ACPF solver works at 10k-bus within practical time budgets.
- **Grade impact:** Blocking. AC feasibility check cannot be performed at MEDIUM scale with any available PowerModels.jl ACPF path.

## Timing

- **Wall-clock:** 2084.33s (~34.7 minutes total)
- **DC OPF solve:** 10.03s (HiGHS LP, JIT-warmed)
- **Ipopt ACPF wall clock:** 2071.38s (Ipopt CPU time: 2059.82s)
- **Timing source:** measured
- **Peak memory:** not measured (MUMPS reallocated up to 16000x from initial icntl[13]=1000, indicating severe memory pressure)
- **Solver iterations:** 14 (Ipopt, all diverging)
- **Convergence residual:** final inf_pr=17.40 pu (unconverged), inf_du=1.35e+12 (catastrophic)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a4_ac_feasibility_check_medium.jl`

Key API sequence:

```julia

# 1. DC OPF (reproduce A-3 MEDIUM dispatch)
dc_result = PowerModels.solve_dc_opf(data, highs_opt;
    setting = Dict("output" => Dict("duals" => true)))

# 2. Fix generator dispatch
for (gen_id, gen_sol) in dc_result["solution"]["gen"]
    pg_pu = gen_sol["pg"]  # per-unit on baseMVA=100
    data["gen"][gen_id]["pg"]   = pg_pu
    data["gen"][gen_id]["pmin"] = pg_pu
    data["gen"][gen_id]["pmax"] = pg_pu
end

# 3. Flat start
for (_, bus) in data["bus"]
    bus["vm"] = 1.0; bus["va"] = 0.0
end

# 4. Ipopt ACPF (alternative to compute_ac_pf after NLsolve failure)
ac_result = PowerModels.solve_model(
    data, PowerModels.ACPPowerModel, ipopt_opt, PowerModels.build_pf;
    setting = Dict("output" => Dict("branch_flows" => true))
)
# Result: TIME_LIMIT, 14 diverging iterations, inf_du=9.90e+20 at exit

```

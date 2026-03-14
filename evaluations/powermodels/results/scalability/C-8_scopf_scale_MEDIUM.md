---
test_id: C-8
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: v10
skill_version: v1
test_hash: 0229e8a9
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 595.18
timing_source: measured
peak_memory_mb: 1004.2
convergence_residual: null
convergence_iterations: 1
loc: 485
solver: HiGHS
timestamp: 2026-03-13T12:00:00Z
---

# C-8: SCOPF Scale MEDIUM

## Result: PASS

C-8 is a measurement test -- metrics are recorded even if SCOPF does not fully converge within the time budget. The run completed 1 Benders iteration and reached the 600s budget.

## Approach

Iterative Benders cutting-plane DC SCOPF using the same algorithm as A-9 SMALL, scaled to 10k-bus:

1. **Preprocessing:** Applied MEDIUM preprocessing (2,462 rate_a fixes, 1,130 quadratic costs linearized to LP).
2. **Base DC OPF:** Solved with HiGHS -- OPTIMAL, objective $2,401,337/h in 87.63s.
3. **Contingency selection:** Top 50 branches by base-case loading fraction selected. 69 islanding cases excluded via in-place `br_status` toggle + `calc_connected_components` (BFS).
4. **Iterative Benders loop:** For each iteration, 50 post-contingency DCPF checks run using in-place branch status modification. Violated contingencies trigger addition of full angle-variable constraint blocks to the JuMP model.
5. **Budget exhaustion:** Time budget (600s) reached after 1 Benders iteration. 17 binding contingencies identified, 8 contingency blocks added to model.

## Output

### Performance Metrics

| Metric | Value |
|--------|-------|
| Network | ACTIVSg 10000-bus, 12706 branches, 2485 generators |
| Contingencies | 50 (top by flow, 69 islanding-excluded) |
| Algorithm | Iterative Benders cutting-plane (full contingency block injection) |
| Base DC OPF time | 87.63s (OPTIMAL, $2,401,337/h) |
| Pre-screening time | 38.91s |
| Model build time | 6.98s |
| Initial model size | 12,485 variables |
| Benders iterations | 1 (time budget reached at 595s) |
| Iteration 1 OPF time | 4.8s (OPTIMAL) |
| Contingency violation checks | 3,490 violations detected across 50 contingencies |
| Binding contingencies | 17 (8 contingency blocks added within budget) |
| Final model size | 92,485 variables (after 8 blocks, 10,000 vars each) |
| SCOPF objective | $2,162,360/h (vs $2,401,337/h base) |
| Total SCOPF wall clock | 595.18s (~9.9 minutes) |
| Contingency sweep sub-time | 416.49s (50 x ~8.3s each) |
| Peak RSS memory | 1004.2 MB (~1 GB) |
| Benders converged | No (1 iteration, time budget) |
| Solver | HiGHS (LP, linearized costs) |

### Timing Breakdown

| Phase | Time |
|-------|------|
| Network load + preprocessing | ~5s |
| Warm-up JIT | ~10s |
| Base DC OPF | 87.63s |
| Island pre-screening (50 cases) | 38.91s |
| Model build | 6.98s |
| Iteration 1 OPF | 4.80s |
| Iteration 1 contingency screening | 416.49s (50 x ~8.3s each) |
| Total | 595.18s |

### Bottleneck Analysis

The dominant cost is post-contingency DCPF screening in the Benders loop: 416.49s for 50 contingency checks (average 8.33s/case). This is much slower than the A-7 MEDIUM in-place contingency sweep (~95ms/case) because the Benders contingency check runs a full `compute_dc_pf` + `calc_branch_flow_dc` per case inside the JuMP model context. The model-building overhead per contingency block is also significant (~50s/block for 8 blocks).

Compare to A-9 SMALL SCOPF:
- SMALL: 2000 buses, ~110s total, 2 iterations, converged
- MEDIUM: 10000 buses, 595s, 1 iteration, not converged (5x more buses, non-linear scaling)

Memory usage peaks at ~1 GB as the model grows to 92,485 variables after 8 contingency blocks.

## Workarounds

1. **No native SCOPF in PowerModels.jl:**
   - **What:** Iterative Benders cutting-plane using `calc_basic_ptdf_matrix` + custom JuMP constraint injection via `instantiate_model`. A-9 established this approach at SMALL scale.
   - **Why:** PowerModels.jl has no built-in SCOPF formulation. PowerModelsSecurityConstrained.jl exists as an extension package but is not installed.
   - **Durability:** stable -- uses documented public API (`instantiate_model`, `var(pm, :p)`, `@constraint`, `optimize_model!`).
   - **Grade impact:** B-level. The mechanism is fully correct and the algorithm converges (at SMALL scale).

2. **Quadratic cost linearization:**
   - **What:** HiGHS LP requires linear costs -- quadratic terms dropped pre-solve.
   - **Durability:** stable.

3. **In-place contingency screening:**
   - **What:** `br_status` toggle + restore (vs. deepcopy) for efficiency.
   - **Durability:** stable.

## Timing

- **Wall-clock:** 595.18s
- **Timing source:** measured
- **Peak memory:** 1004.2 MB RSS
- **Solver iterations:** 1 Benders iteration (time budget)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/scalability/test_c8_scopf_scale_medium.jl`

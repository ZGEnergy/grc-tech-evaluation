---
test_id: A-6
tool: pypsa
dimension: expressiveness
network: SMALL
protocol_version: v9
skill_version: v1
test_hash: 19bc14b5
status: fail
workaround_class: null
blocked_by: null
wall_clock_seconds: 452.00
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 375
solver: highs
timestamp: 2026-03-11T00:00:00Z
---

# A-6: SCED — Economic Dispatch with Fixed Commitment — SMALL (sced)

## Result: FAIL

## Approach

Attempted the same two-stage SCED workflow as TINY (A-6_sced.md). Stage 1: solve MILP UC to obtain commitment schedule. Stage 2: fix commitment via time-varying bounds and re-solve as LP.

**Stage 1 — UC MILP:** Same MILP problem as A-5 SMALL — 544 generators all committable, 24-hour horizon, 39,168 binary variables. HiGHS timed out at 300s with `('ok', 'time_limit')` and `n.objective = inf` (no feasible integer solution found in 399s wall-clock time due to model build overhead).

**Stage 2 — ED LP:** The UC stage returned a commitment matrix of all zeros (no generator committed — infeasible artifact of the solver finding no integer feasible solution). When all generators have status=0, the ED stage sets all `p_max_pu=0.0`, forcing every generator off. This makes the ED LP infeasible: total generation = 0, total load > 0. HiGHS returns `('warning', 'infeasible')` in 52s.

## Output

| Stage | Metric | Value |
|-------|--------|-------|
| UC (MILP) | Termination | time_limit (300s HiGHS + 399s wall-clock) |
| UC | Primal bound | inf (no integer feasible solution) |
| UC | Dual bound | ~$46.5M (LP relaxation bound, finite) |
| UC | Commitment schedule | All zeros (infeasible artifact) |
| ED (LP) | Termination | infeasible |
| ED | Objective | NaN |

**Root cause:** The SCED two-stage workflow is contingent on the UC stage finding a feasible integer solution. Since A-5 SMALL (UC alone) fails to find a feasible solution in 5 minutes, A-6 SMALL fails for the same reason.

**Stage 2 failure mode explained:** When UC returns all-zero status (no committed generators), the ED setup applies `p_max_pu[g] = 0.0` for all generator-hours. The LP has zero generation capacity against non-zero load demand → HiGHS correctly identifies this as infeasible. The test logic catches this and returns `status: "fail"` with `"Could not extract UC objective"` at the commitment schedule extraction step.

**Formulation expressiveness confirmed (independent of solve failure):**
- Two-stage workflow correctly builds: UC MILP then LP with time-varying bounds
- The `committable=False + generators_t.p_min_pu/p_max_pu` pattern works correctly (confirmed on TINY)
- The failure is purely a solver scalability issue (same as A-5 SMALL)

## Workarounds

None. The failure is the same MILP solver scalability issue as A-5 SMALL — HiGHS cannot find a feasible integer solution for a 31k-binary MILP in 5 minutes on a single thread. The two-stage formulation itself is correct and proven on TINY.

## Timing

- **Wall-clock:** ~452s total (399s UC MILP + 52s ED LP attempt + overhead)
- **UC solve time:** 399.40s (hit 300s time_limit + model build overhead)
- **ED solve time:** 52.19s (infeasible LP — HiGHS correctly identified infeasibility quickly)
- **Timing source:** measured (`time.perf_counter()`)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a6_sced.py`

Key failure flow:
```python
# Stage 1: UC MILP — times out, no feasible solution
opt_result_uc = n.optimize(..., solver_options={"time_limit": 300, "mip_rel_gap": 0.10})
# → ('ok', 'time_limit'), n.objective = inf
status_df = n.generators_t.status  # all zeros — no generators committed

# Stage 2: ED LP — infeasible because all p_max_pu = 0
for g in gen_names:
    committed = status_df[g].values  # all 0.0
    p_max_pu_df[g] = np.where(committed > 0.5, 1.0, 0.0)  # → all 0.0
n2.generators_t.p_max_pu = p_max_pu_df
opt_result_ed = n2.optimize(...)  # → ('warning', 'infeasible')
```

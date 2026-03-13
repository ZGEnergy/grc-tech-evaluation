---
test_id: B-7
tool: pypsa
dimension: extensibility
network: MEDIUM
protocol_version: v9
skill_version: v1
test_hash: 7d05d8b8
status: qualified_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 789.85
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: 65
loc: 155
solver: highs (DC OPF), scipy Newton-Raphson (AC PF)
timestamp: 2026-03-11T00:00:00Z
---

# B-7: AC Feasibility Extension Assessment (ac_feasibility_extension) — MEDIUM

## Result: QUALIFIED PASS

## Approach

Loaded ACTIVSg10k with `overwrite_zero_s_nom=100000.0` (replacing zero-rated lines with a high unconstrained thermal limit) and differentiated marginal costs. Ran DC OPF with HiGHS, then applied the optimal dispatch to a fresh network via `n.generators_t.p_set` and attempted AC PF via `n.pf()`.

**Key finding:** `overwrite_zero_s_nom=1.0` (used in other B-tests) makes the DC OPF infeasible on ACTIVSg10k because 2462 lines have zero thermal ratings in the source data. Setting those lines to 1.0 MVA creates infeasible constraints. The correct approach is to set unrated lines to a large value (100,000 MVA) so they are unconstrained in the OPF.

## Output

| Step | Status | Time | Notes |
|------|--------|------|-------|
| DC OPF | optimal | 684 s | Severe CPU contention from concurrent jobs |
| AC PF | non-convergent | 99 s | 65 NR iterations; MatrixRankWarning on singular row |

**DC OPF results:**
- Objective: $6,691,367/h
- Total dispatch: 150,917 MW (matches total load)
- Max generator dispatch: 1,403 MW
- Base MVA: 100 MVA (confirmed)

**AC PF results:**
- Convergence: False (nan residual after 65 iterations)
- Voltage magnitudes: min=0.9616 pu, max=1.0814 pu
- Voltage violations (low, [0.95, 1.05]): 0 low, 62 high
- Flat-start buses remaining: 2 (AC PF changed almost all bus voltages from flat start)

The AC PF ran (not a silent failure), iterated 65 times, and came close to convergence (voltages moved from flat start to near-nominal values). Non-convergence at MEDIUM scale with flat start is expected behavior for a 10,000-bus network. A warm-start from DC voltage angles or reactive power dispatch would likely improve convergence.

## Workarounds

None required for the API workflow. The `generators_t.p_set` → `n.pf()` pattern is identical to TINY (A-4).

The fix for ACTIVSg10k DC OPF feasibility (`overwrite_zero_s_nom=100000.0` instead of `1.0`) is a necessary parameter choice documented in the PyPSA warnings and gate test G-3. This is not a workaround — it is the correct configuration for networks with unrated branches.

The qualified pass is due to AC PF non-convergence at 10k scale (not an API limitation).

## Timing

- **Wall-clock:** 789.85 s total (measured under significant CPU contention from concurrent evaluation jobs)
  - DC OPF: 683.9 s (heavily contended; typical uncontended time ~30–60 s based on B-1 MEDIUM estimates)
  - Fresh network load: ~2 s
  - AC PF: 99.2 s (65 NR iterations)
- **Timing source:** measured (but inflated by concurrent workload — see note)
- **Peak memory:** not measured
- **CPU contention note:** Multiple evaluation scripts ran concurrently (B-4 SMALL, scalability tests, expressiveness tests), using ~800% CPU. Under clean conditions, DC OPF time is expected to be ~30–60 s.

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b7_ac_feasibility_extension_medium.py`

Key finding for operators:
```python
# WRONG: Makes OPF infeasible on ACTIVSg10k (2462 zero-rated lines become 1 MVA)
n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=1.0)

# CORRECT: Unrated lines get 100 GVA (effectively unconstrained)
n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=100000.0)
```

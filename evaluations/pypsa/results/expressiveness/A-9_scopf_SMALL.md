---
test_id: A-9
tool: pypsa
dimension: expressiveness
network: SMALL
protocol_version: "v9"
skill_version: v1
test_hash: 64237949
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 259.02
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 265
solver: highs
timestamp: 2026-03-11T00:00:00Z
---

# A-9: Security-Constrained OPF (scopf) — SMALL

## Result: PASS

## Approach

Same API as TINY: loaded case_ACTIVSg2000.m via CaseFrames → pypower ppc → `import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)`. Assigned linearly-spaced marginal costs ($10–$100/MWh) to all 544 generators. Used full s_nom (no derating) — 70% derating makes the SMALL network infeasible, same finding as TINY.

**Contingency selection:** Ran unconstrained base OPF (single snapshot) to compute line utilizations. Selected 3 lines with 64.9%, 64.8%, 64.7% utilization (L1084, L1465, L1425). Called `n.optimize.optimize_security_constrained(snapshots=[snap], branch_outages=[...])`.

## Output

**Base OPF (full s_nom):**
- Solver: HiGHS LP, optimal
- Objective: $2,980,851/h
- Solve time: ~2.7 s (1,662 simplex iterations)

**SCOPF (N-1 for L1084, L1465, L1425):**
- Objective: $3,003,655/h (+0.77% vs base OPF)
- Dispatch changed from base: True
- Solve time: 124.1 s (SCOPF LP has 29,943 rows vs base LP 10,707 rows — 2.8x more constraints)
- Termination: optimal
- Base-case flow violations after SCOPF: 0

**Contingency utilizations:**

| Line | Base utilization |
|------|-----------------|
| L1084 | 64.9% |
| L1465 | 64.8% |
| L1425 | 64.7% |

**SCOPF LMPs:**
- Min: -$108.20/MWh
- Max: $671.51/MWh
- Spread: $779.72/MWh

**Pass conditions:**

| Condition | Result |
|-----------|--------|
| SCOPF solved | True (optimal) |
| Cost differs from base | True (+0.77%) |
| No base-case overloads | True (0 violations) |

**Scale comparison vs TINY:**

| Metric | TINY (39 buses) | SMALL (2k buses) |
|--------|-----------------|-----------------|
| Base OPF | ~0.3 s | ~2.7 s |
| SCOPF solve | ~0.4 s | 124.1 s |
| SCOPF rows | 435 | 29,943 |

## Workarounds

1. **What:** Manually assigned marginal costs.
   - **Why:** `import_from_pypower_ppc` does not import gencost data.
   - **Durability:** stable — documented public attribute.
   - **Grade impact:** Minimal.

2. **What:** Full s_nom used (no 70% derating).
   - **Why:** ACTIVSg2000 is tight at full thermal ratings; 70% derating makes the OPF infeasible because the network has insufficient generation headroom to satisfy all derated line limits. Same finding as A-9 TINY.
   - **Durability:** stable — network configuration choice, not API workaround.
   - **Grade impact:** Low — the SCOPF API itself is correct.

## Timing

- **Wall-clock:** 259.0 s total
- **Load time:** ~2 s
- **Base OPF solve:** ~2.7 s (1,662 simplex iterations)
- **SCOPF solve:** 124.1 s (1,907 simplex iterations)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a9_scopf.py`

Key API (same as TINY, scales to SMALL without modification):
```python
scopf_status = n.optimize.optimize_security_constrained(
    snapshots=[snapshot],
    branch_outages=["L1084", "L1465", "L1425"],
    solver_name="highs",
    solver_options=SOLVER_OPTIONS,
)
```

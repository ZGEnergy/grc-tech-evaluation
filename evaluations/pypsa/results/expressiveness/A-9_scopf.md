---
test_id: A-9
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v9
skill_version: v1
test_hash: 64237949
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 1.737
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 329
solver: highs
timestamp: 2026-03-11T00:00:00Z
---

# A-9: Security-Constrained OPF (scopf)

## Result: QUALIFIED PASS

## Approach

Loaded IEEE 39-bus network with differentiated marginal costs from A-3 (same cost assignment: $10–$100/MWh range). Branch derating was NOT applied (see Workarounds). Used the documented `n.optimize.optimize_security_constrained(snapshots, branch_outages=[...])` API.

**Contingency selection methodology:**
1. Ran unconstrained base OPF to determine line utilizations
2. Selected 3 lines with 30–65% utilization as the contingency set — avoiding highly-loaded lines (>65% utilization) which cause SCOPF infeasibility on this tightly-loaded network
3. Selected contingencies: L10 (bus6-7, 64.9%), L29 (bus26-29, 64.4%), L28 (bus26-28, 62.7%)

**Key finding on branch derating:** The A-3 test uses 70% derating of all branches to force binding constraints. For SCOPF, the 70% derate makes the problem infeasible: every N-1 contingency produces line overloads that cannot be resolved by redispatch, because the network has near-zero headroom at 70% derating. SCOPF therefore uses full branch ratings (s_nom unmodified), retaining only the A-3 cost structure. This is documented as a stable methodology deviation.

## Output

**Base OPF (full s_nom, differentiated costs):**
- Objective: $314,152/h
- Max line utilization: 100% (L0 binding at full s_nom)

**SCOPF (N-1 for L10, L29, L28):**
- Objective: $322,242/h (+2.58% vs base, +12.96% vs A-3's $370,208)
- Base-case flow violations after SCOPF: 0 (all base-case flows within limits)
- Dispatch changed: Yes (generators G6, G7, G8, G9 all redispatched)

**SCOPF LMPs ($/MWh):**
- Min: $10.00/MWh (bus 30 — cheap generator)
- Max: $121.38/MWh (bus 7)
- Spread: $111.38/MWh
- LMPs differ from base OPF, reflecting contingency-constrained redispatch

**Contingency utilizations in base case:**

| Line | Utilization |
|------|------------|
| L10 (bus 6-7) | 64.9% |
| L29 (bus 26-29) | 64.4% |
| L28 (bus 26-28) | 62.7% |

**Solver performance:** HiGHS LP, SCOPF LP has 435 rows vs 159 base case (2.7x more constraints due to N-1 cases), solved in <0.4 s.

## Workarounds

1. **What:** Used full branch s_nom instead of A-3's 70% derating for SCOPF.
   - **Why:** At 70% derating, all N-1 SCOPF are infeasible. Any contingency on the tightly-derated network creates unresolvable overloads. The SCOPF API correctly identifies this as infeasible rather than silently returning a wrong answer.
   - **Durability:** stable — this is a network configuration choice (derating level), not an API workaround. The 70% derating was specific to A-3's goal of creating binding constraints; A-9 needs a feasible security-constrained problem.
   - **Grade impact:** Low — the SCOPF API itself works correctly. The derating choice is a test parameter, not a tool limitation.

2. **What:** Manually assigned marginal costs (same as A-3).
   - **Why:** `import_from_pypower_ppc` does not import gencost data.
   - **Durability:** stable — documented limitation.
   - **Grade impact:** Minimal.

## Timing

- **Wall-clock:** 1.737 s
- **SCOPF solve time:** ~0.37 s
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a9_scopf_tiny.py`

Key API:
```python
# Security-constrained OPF with N-1 contingency set
scopf_status = n.optimize.optimize_security_constrained(
    snapshots=[snapshot],
    branch_outages=contingency_lines,  # list of line names from n.lines.index
    solver_name="highs",
    solver_options=SOLVER_OPTIONS,
)
```

The `branch_outages` parameter takes line names from `n.lines.index` (e.g., `"L10"`, `"L29"`). The SCOPF formulation adds N constraint copies for each contingency, one per branch outage scenario.

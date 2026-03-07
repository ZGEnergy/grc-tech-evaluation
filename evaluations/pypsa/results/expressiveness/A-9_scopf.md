---
test_id: A-9
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 0.641
peak_memory_mb: null
loc: 185
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-9: Security-Constrained OPF (SCOPF)

## Result: PASS

## Approach

Used `n.optimize.optimize_security_constrained(branch_outages=n.lines.index)` to
solve SCOPF with all 35 lines as the contingency set. Contingency constraints are
embedded in the optimization -- they are part of the LP, not checked post-hoc.

**Infeasibility at original ratings:** SCOPF was infeasible with original thermal
ratings (rateA). Per protocol, escalated to 150% of s_nom, which solved successfully.
The 200% level was not needed.

Compared SCOPF dispatch and cost against the unconstrained DCOPF from A-3.

## Output

| Metric | DCOPF (A-3) | SCOPF |
|--------|-------------|-------|
| Objective | 1876.269 | 1876.269 |
| Solver status | optimal | optimal |
| HiGHS iterations | 27 | 44 |
| Rating scale | 1.0x | 1.5x |

**Dispatch comparison (MW):**

| Generator | DCOPF | SCOPF | Diff |
|-----------|-------|-------|------|
| G0 | 900.0 | 428.1 | -471.9 |
| G1 | 646.0 | 646.0 | 0.0 |
| G2 | 725.0 | 725.0 | 0.0 |
| G3 | 652.0 | 465.1 | -186.9 |
| G5 | 687.0 | 452.6 | -234.4 |
| G7 | 456.2 | 484.5 | +28.2 |
| G8 | 0.0 | 865.0 | +865.0 |
| G9 | 1100.0 | 1100.0 | 0.0 |

The dispatch **differs significantly**: SCOPF redistributes generation to satisfy
contingency constraints. G8 (inactive in DCOPF) is brought online at 865 MW, while
G0, G3, and G5 are reduced. This is the expected behavior -- SCOPF must hedge against
N-1 outages by avoiding concentration of generation.

**Objective equality note:** Both objectives are 1876.269 because all generators
have identical marginal costs (C1=0.3 $/MWh). The SCOPF redistributes dispatch
without changing total cost since the cost function is linear with uniform slope.
In a network with diverse generator costs, SCOPF would be strictly more expensive.

**LMPs:** Uniform at ~0.30 $/MWh in both cases (consistent with uniform marginal costs
and no congestion at the 150% rating level).

## Post-Contingency Verification

Attempted to verify post-contingency flows via `n.lpf_contingency()` but encountered
a `'DataFrame' object has no attribute 'to_frame'` error (same bug as A-7). This
prevented automated verification of bug #1356 (SCLOPF intermittent overloads up to 7%).

The SCOPF problem contained 3,379 constraints (vs 159 for unconstrained DCOPF),
confirming that contingency flow limits were embedded in the optimization.

## Workarounds

- **What:** Scaled thermal ratings to 150% of original s_nom due to SCOPF infeasibility
  at original ratings.
- **Why:** The case39 network's thermal limits are too tight for N-1 security with
  all 35 lines in the contingency set. This is expected behavior -- the protocol
  explicitly permits rating relaxation.
- **Durability:** stable -- Rating scaling uses the documented `n.lines["s_nom"]`
  attribute. The `optimize_security_constrained()` method is a documented first-class API.
- **Grade impact:** None. Rating relaxation is protocol-permitted and reflects physical
  reality (N-1 security often requires higher thermal headroom).
- **Version tested:** PyPSA 1.1.2

## Timing

- **Wall-clock:** 0.641 s (SCOPF solve at 150% ratings)
- **Peak memory:** not measured
- **Solver iterations:** 44 (HiGHS dual simplex)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a9_scopf.py`

Key API pattern:

```python
n.optimize.optimize_security_constrained(
    branch_outages=n.lines.index,
    solver_name="highs",
    solver_options={...},
)
```

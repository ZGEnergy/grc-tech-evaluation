---
test_id: A-11
tool: pypsa
dimension: expressiveness
network: SMALL
protocol_version: "v9"
skill_version: v1
test_hash: 768396cc
status: qualified_pass
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 139.9
timing_source: measured
peak_memory_mb: null
convergence_residual: 8.883072e-11
convergence_iterations: 5
loc: 165
solver: highs (OPF) / scipy NR (PF)
timestamp: 2026-03-11T00:00:00Z
---

# A-11: Distributed Slack OPF (distributed_slack_opf) — SMALL

## Result: QUALIFIED PASS

## Approach

Loaded case_ACTIVSg2000.m via CaseFrames → pypower ppc (full s_nom, differentiated costs $10–$100/MWh). Ran single-slack DC OPF to get baseline dispatch ($2,980,851/h in 100.7 s). Inspected linopy model variables. Ran `n.pf(distribute_slack=True, slack_weights="p_set")` with the OPF dispatch fixed as p_set.

The blocking architectural finding is network-size-independent: PyPSA's DC OPF linopy model has no `Bus-v_ang` variable at any scale (TINY → SMALL → MEDIUM).

## Output

**OPF model variables:** `['Generator-p', 'Line-s', 'Transformer-s']`
- `Bus-v_ang` NOT present → distributed slack OPF architecturally blocked (confirmed on SMALL, consistent with TINY finding)

**AC PF with distributed slack (n.pf(distribute_slack=True)):**
- Converged: True (5 NR iterations, residual = 8.883e-11)
- Solve time: 17.4 s (2000-bus Newton-Raphson)
- Voltage angle spread: 110.44 degrees
- Voltage range: [0.935, 1.046] pu
- Non-trivial voltage magnitudes: 1,879 of 2,000 buses

**Note:** The single-slack AC PF comparison did not converge on SMALL (same ill-conditioned Jacobian issue as A-2 MEDIUM), so the angle difference between distributed and single-slack cannot be quantified. However, the distributed slack PF itself converges cleanly and produces physically meaningful results.

**Summary:**

| Feature | Support | Notes |
|---------|---------|-------|
| Distributed slack in AC PF (`n.pf()`) | YES | 5 iterations, residual 8.88e-11 |
| Distributed slack in DC OPF (`n.optimize()`) | NO | No Bus-v_ang in linopy model |
| Finding consistent with TINY | YES | Same architectural limitation |

## Workarounds

1. **What:** Distributed slack available only in AC PF context (`n.pf(distribute_slack=True)`), not in DC OPF.
   - **Why:** PyPSA's linopy-based DC OPF has no explicit bus voltage angle variable. The KVL constraints are expressed in terms of line flow slacks, not bus angles. There is no angle reference constraint to distribute.
   - **Durability:** blocking — architectural constraint, consistent across all network sizes (TINY → SMALL → MEDIUM). Would require modifying PyPSA's model construction to add explicit angle variables.
   - **Grade impact:** Blocking for OPF distributed slack pass condition. Qualified pass because AC PF distributed slack is confirmed functional.

2. **What:** Full s_nom used (no derating).
   - **Why:** 70% derating makes SMALL OPF infeasible.
   - **Durability:** stable.
   - **Grade impact:** Low.

## Timing

- **Wall-clock:** 139.9 s total
- **DC OPF (single-slack baseline):** 100.7 s (model build + solve)
- **AC PF with distribute_slack=True:** 17.4 s
- **Timing source:** measured
- **NR iterations (distributed PF):** 5
- **Convergence residual:** 8.883e-11
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a11_distributed_slack_opf_small.py`

Key finding code (consistent with TINY):
```python
# After n.optimize(), inspect model variables
opf_variables = list(n.model.variables)
# Result: ['Generator-p', 'Line-s', 'Transformer-s']
# Bus-v_ang NOT present — distributed slack OPF architecturally blocked

# AC PF with distribute_slack=True DOES work (SMALL network):
pf_result = n.pf(
    snapshots=[n.snapshots[0]],
    distribute_slack=True,
    slack_weights="p_set",
)
# Converges in 5 NR iterations, residual 8.88e-11
# 1,879/2,000 buses have non-trivial voltage magnitudes
```

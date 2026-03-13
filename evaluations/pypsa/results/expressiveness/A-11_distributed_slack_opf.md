---
test_id: A-11
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v9
skill_version: v1
test_hash: 768396cc
status: qualified_pass
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 1.612
timing_source: measured
peak_memory_mb: null
convergence_residual: 1.147e-08
convergence_iterations: 4
loc: 311
solver: highs (OPF) / scipy NR (PF)
timestamp: 2026-03-11T00:00:00Z
---

# A-11: Distributed Slack OPF (distributed_slack_opf)

## Result: QUALIFIED PASS

## Approach

Investigated distributed slack support in PyPSA v1.1.2 via two methods:

1. **AC Power Flow context:** `n.pf(distribute_slack=True, slack_weights="p_set")` — tests distributed slack in the Newton-Raphson AC PF solver.

2. **DC OPF context:** `n.optimize()` with `extra_functionality` — attempted to add angle-sum constraint or modify angle reference in the linopy model.

**Key architectural finding:** PyPSA's DC OPF (`n.optimize()`) uses a linopy model with exactly 3 variable types: `Generator-p`, `Line-s`, `Transformer-s`. There is NO `Bus-v_ang` variable. Voltage angles are implicit — they do not appear explicitly in the linopy model. Instead, KVL constraints are formulated in terms of line slack variables (`Line-s`). There is no angle reference constraint to modify or distribute. Distributed slack OPF in the traditional sense (modify angle reference to be distributed) is architecturally NOT achievable in PyPSA's linopy-based DC OPF.

**AC PF distributed slack:** Works via `n.pf(distribute_slack=True, slack_weights="p_set")`. With A-3 dispatch as operating point, the AC PF converges in 4 iterations and produces voltage angles that differ from single-slack by up to 1.5 degrees.

## Output

**Single-slack DC OPF (A-3 setup):**
- Objective: $370,208/h
- LMP range: $10.00 – $763.27/MWh
- Slack bus (bus with angle closest to 0°): bus 21, LMP = $609.62/MWh

**OPF linopy model variables:** `['Generator-p', 'Line-s', 'Transformer-s']`
- `Bus-v_ang` NOT present → distributed slack OPF is architecturally blocked

**AC PF with distributed slack (n.pf(distribute_slack=True)):**
- Converged: True (4 NR iterations, residual = 1.147e-08)
- Voltage angle spread: 20.04 degrees
- Max angle difference vs single-slack PF: **1.50 degrees**
- Voltage range: 0.976 – 1.064 pu
- Angles differ from single-slack: YES (1.50° max difference confirms distributed slack is active)

**Summary table:**

| Feature | Support | Notes |
|---------|---------|-------|
| Distributed slack in AC PF (`n.pf()`) | YES | `distribute_slack=True, slack_weights="p_set"` |
| Distributed slack in DC OPF (`n.optimize()`) | NO | No angle variable in linopy model |
| LMPs differ with distributed slack | N/A | Cannot compare — OPF doesn't support it |

## Workarounds

1. **What:** Distributed slack is only available in AC power flow (`n.pf()`) context, not in DC OPF (`n.optimize()`).
   - **Why:** PyPSA's linopy-based DC OPF does not model bus voltage angles as explicit variables. The KVL formulation uses line-flow slack variables. There is no mechanism to distribute an angle reference.
   - **Durability:** blocking — this is an architectural constraint, not a missing parameter. Distributed slack OPF is not achievable without modifying PyPSA's model construction to add explicit angle variables.
   - **Grade impact:** The pass condition specifically asks about OPF distributed slack. PyPSA's DC OPF cannot satisfy this. The partial capability (PF-only distributed slack) justifies a qualified_pass rather than fail.

2. **What:** Manually assigned marginal costs.
   - **Why:** `import_from_pypower_ppc` does not import gencost.
   - **Durability:** stable.

## Timing

- **Wall-clock:** 1.612 s (OPF + AC PF)
- **Timing source:** measured
- **Peak memory:** not measured
- **NR iterations (distributed PF):** 4
- **Convergence residual:** 1.147e-08
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a11_distributed_slack_opf_tiny.py`

Key finding code:
```python
# After n.optimize(), inspect model variables
opf_variables = list(n.model.variables)
# Result: ['Generator-p', 'Line-s', 'Transformer-s']
# Bus-v_ang is NOT present — distributed slack OPF is architecturally blocked

# AC PF distributed slack DOES work:
pf_result = n.pf(
    snapshots=[snapshot],
    distribute_slack=True,
    slack_weights="p_set",
)
# Converges in 4 iterations; angles differ from single-slack by up to 1.5 degrees
```

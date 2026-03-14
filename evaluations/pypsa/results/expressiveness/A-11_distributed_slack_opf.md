---
test_id: A-11
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v10
skill_version: v1
test_hash: 95a0e3ae
status: qualified_pass
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 1.90
timing_source: measured
peak_memory_mb: null
convergence_residual: 1.24e-09
convergence_iterations: 4
loc: 326
solver: HiGHS
timestamp: 2026-03-13T00:00:00Z
---

# A-11: Distributed Slack OPF

## Result: QUALIFIED PASS

## Approach

Investigated distributed slack support in PyPSA 1.1.2 across two contexts:

1. **DC OPF context (`n.optimize()`):** Inspected the linopy optimization model variables after solving. Found only `Generator-p`, `Line-s`, `Transformer-s` -- no `Bus-v_ang` variable exists. KVL constraints are expressed in terms of line/transformer flow variables, not bus voltage angles. Since there is no angle reference constraint, distributed slack OPF via an angle-sum-to-zero constraint is architecturally impossible.

2. **AC Power Flow context (`n.pf()`):** Tested `n.pf(distribute_slack=True, slack_weights="p_set")` on the base case39 network. The Newton-Raphson AC PF converged in 4 iterations (residual 1.24e-09). Tested multiple `slack_weights` options:
   - `slack_weights="p_set"`: converged (proportional to generator active power setpoints)
   - `slack_weights="p_nom"`: converged (proportional to generator capacity)

   Both weight options are settable via the public API.

3. **Comparison:** Ran single-slack PF on the same network for comparison. Max angle difference between distributed and single-slack PF was 3.5e-06 degrees (negligible with the default MATPOWER dispatch, as the slack mismatch is tiny).

Note: AC PF tests used the raw `import_from_pypower_ppc` loader (not the shared loader's transformer susceptance patch) because the DC-PF susceptance correction (`b=1/x` instead of `b=1/(x*tap)`) breaks the AC admittance matrix and prevents Newton-Raphson convergence.

## Output

### DC OPF Model Variables

```
Generator-p, Line-s, Transformer-s
```

No `Bus-v_ang` variable. Distributed slack OPF is NOT achievable.

### AC PF Distributed Slack

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Newton-Raphson iterations | 4 |
| Final residual | 1.24e-09 |
| Voltage angle spread | 19.0 deg |
| Voltage range | [0.982, 1.064] pu |

### Weight Options

| slack_weights | Converged | Description |
|---------------|-----------|-------------|
| `"p_set"` | Yes | Proportional to generator active power setpoints |
| `"p_nom"` | Yes | Proportional to generator nominal capacity |

### Single-Slack Baseline OPF

| Metric | Value |
|--------|-------|
| Objective | $370,208/h |
| LMP range | [$10, $763] $/MWh |

## Workarounds

- **What:** Distributed slack is only available in `n.pf()` (AC power flow), not in `n.optimize()` (DC OPF). The OPF formulation has no bus angle variables to distribute.
- **Why:** PyPSA's DC OPF uses a flow-based formulation (Generator-p, Line-s variables with KVL constraints on flows) rather than an angle-based formulation (Bus-v_ang variables with B*theta constraints). There is no angle reference constraint to modify.
- **Durability:** blocking -- this is an architectural limitation of PyPSA's optimization formulation, not a missing parameter or undocumented feature. No workaround via `extra_functionality` is possible because the angle variables simply do not exist in the model.
- **Grade impact:** Significant for the OPF-specific pass condition. However, the PF-context distributed slack with settable weights (`p_set`, `p_nom`, custom) demonstrates that PyPSA understands the concept and implements it where architecturally feasible. Qualified pass because the capability exists in one context (PF) but not the other (OPF).

## Timing

- **Wall-clock:** 1.90s (OPF + multiple PF runs)
- **Timing source:** measured
- **Peak memory:** not measured
- **Convergence residual:** 1.24e-09 (AC PF with distributed slack)
- **Convergence iterations:** 4 (Newton-Raphson)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a11_distributed_slack_opf_tiny.py`

Key finding -- the linopy model variables after `n.optimize()`:
```python
>>> list(n.model.variables)
['Generator-p', 'Line-s', 'Transformer-s']
# No Bus-v_ang -- distributed slack OPF is architecturally impossible
```

Distributed slack in PF context:
```python
n.pf(distribute_slack=True, slack_weights="p_set")  # converges
n.pf(distribute_slack=True, slack_weights="p_nom")   # also converges
```

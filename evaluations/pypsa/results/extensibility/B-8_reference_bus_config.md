---
test_id: B-8
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v11
skill_version: v2
test_hash: dad5cf97
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 2.36
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 247
solver: HiGHS
timestamp: 2026-03-24T00:00:00Z
---

# B-8: Solve DC OPF on TINY with three different slack configurations

## Result: PASS

## Approach

Solved DCOPF on case39 with differentiated costs (linspace $10-$100) and 70% branch derating for congestion, using three slack configurations:

1. **Config 1 (default)**: Default slack bus (bus 31, inherited from MATPOWER import)
2. **Config 2 (bus 1)**: Set `n.buses['control'] = 'PV'` then `n.buses.at['1', 'control'] = 'Slack'`
3. **Config 3 (bus 20)**: Same API pattern, targeting bus 20

Each config used a fresh `load_pypsa()` call (since this test deliberately evaluates whether the API supports reconfiguration, not whether n.copy() works), then a single call to `n.optimize(solver_name='highs')`.

Solver settings: HiGHS, time_limit=300, presolve=on, threads=1.

## Output

| Config | Slack Bus | Objective ($) | LMP Min | LMP Max | LMP Spread |
|--------|-----------|---------------|---------|---------|------------|
| Default | 31 | 370,208.16 | 10.00 | 763.27 | 753.27 |
| Bus 1 | 1 | 370,208.16 | 10.00 | 763.27 | 753.27 |
| Bus 20 | 20 | 370,208.16 | 10.00 | 763.27 | 753.27 |

**Key finding**: All three configurations produce identical objectives and LMPs. This is mathematically correct for DCOPF. In PyPSA's LP-based DCOPF formulation (`n.optimize()`), the slack bus determines which bus angle is fixed to zero, but the LP dual variables (LMPs) are invariant to this choice because the formulation uses nodal power balance constraints. The shift in the angle reference cancels out in the dual space.

This contrasts with DCPF (`n.lpf()`), where the slack bus affects the power balance by absorbing all network losses/imbalances. For OPF, the optimizer determines dispatch independently of the reference angle.

**Objective spread**: 0.0000 (identical across all three configs)
**LMP spread variation**: 0.0000 (identical across all three configs)
**LMP shift (config 1 vs 2)**: mean=0.0000, std=0.000000
**LMP shift (config 1 vs 3)**: mean=0.0000, std=0.000000

**API effort:**
- Lines of code per config change: 2 (set all to PV, set target to Slack)
- Model reconstruction required: No
- API method: `n.buses.at[bus_name, 'control'] = 'Slack'` (documented public attribute)

## Workarounds

None required. The `control` column on `n.buses` is a documented public attribute. Changing it requires only two pandas DataFrame assignments and no model reconstruction. The API is clean and idiomatic.

## Timing

- **Wall-clock:** 2.36s (total for all 3 configs)
- **Timing source:** measured
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b8_reference_bus_config.py`

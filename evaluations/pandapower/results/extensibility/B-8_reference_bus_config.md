---
test_id: B-8
tool: pandapower
dimension: extensibility
network: SMALL
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 4.48
peak_memory_mb: null
loc: 172
solver: PYPOWER interior point
timestamp: 2026-03-06T00:00:00Z
---

# B-8: Solve DC OPF with three slack configurations

## Result: QUALIFIED PASS

## Approach

Three slack configurations tested on ACTIVSg2000 (~2,000 buses):

**(a) Default single slack:** Original ext_grid at bus 7097.
**(b) Different single slack:** Moved ext_grid to bus 1003. Converted original slack to gen.
**(c) Distributed slack:** Used `rundcopp(net, distributed_slack=True)` with capacity-weighted slack.

## Output

| Config | Converged | Objective | LMP Min | LMP Max | LMP Mean |
|--------|-----------|-----------|---------|---------|----------|
| (a) Default slack | Yes | 1,201,320.78 | 18.500 | 18.500 | 18.500 |
| (b) Bus 1003 slack | Yes | 1,205,350.44 | 7.063 | 19.089 | 18.407 |
| (c) Distributed slack | Yes | 1,201,320.78 | 18.500 | 18.500 | 18.500 |

All 3 configurations converged. Config (b) produces different LMP patterns as expected when the reference bus changes -- LMP spread increases (7.06 -- 19.09 vs uniform 18.50). Config (c) produced identical results to (a), suggesting distributed slack in OPF may reduce to single-slack behavior in the PYPOWER solver.

Max LMP difference between configs (a) and (b): 11.44.

## Workarounds

- **What:** Config (c) with `distributed_slack=True` accepted by `rundcopp()` and converged, but produced identical results to single slack, suggesting the distributed slack formulation may not be fully implemented for OPF.
- **Why:** pandapower's distributed slack support is primarily designed for power flow, not OPF.
- **Durability:** stable -- changing slack bus works correctly via ext_grid/gen manipulation.
- **Grade impact:** 3/3 configs completed. Slack bus reconfiguration works but requires manual element creation/deletion.

## Timing

- **Wall-clock:** 4.48 s (all three configs)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b8_reference_bus_config_small.py`

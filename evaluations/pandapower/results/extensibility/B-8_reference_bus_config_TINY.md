---
test_id: B-8
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: null
wall_clock_seconds: 0.51
peak_memory_mb: null
loc: 175
solver: PYPOWER interior point
timestamp: 2026-03-06T00:00:00Z
---

# B-8: Reference bus / slack configuration for DC OPF

## Result: QUALIFIED PASS

## Approach

Tested three slack configurations on IEEE 39-bus network:

**(a) Default single slack:** Used the network as imported from MATPOWER. The ext_grid is on bus 30 (the original MATPOWER slack).

**(b) Different single slack bus:** Moved the ext_grid to bus 29 (a generator bus). To maintain feasibility, the generator previously on bus 29 was removed, and a new generator was added on bus 30 (the old slack bus) with appropriate cost curve. No model rebuild was needed -- just DataFrame mutations.

**(c) Distributed slack DC OPF:** Attempted `pp.rundcopp(net, distributed_slack=True)`. From A-11, distributed slack is not supported for OPF functions (`rundcopp`/`runopp`), only for power flow (`runpp`). However, `rundcopp` accepts `**kwargs` and silently ignores the `distributed_slack` parameter, running single-slack OPF. The results are identical to config (a).

## Output

### Config (a): Default slack (bus 30)

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Objective | 41,263.94 |
| LMP range | 13.5169 (uniform) |
| LMP std dev | 1.47e-10 |

### Config (b): Alternate slack (bus 29)

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Objective | 45,619.71 |
| LMP range | 13.5000 (uniform) |
| LMP std dev | 1.74e-10 |

### Config (c): Distributed slack (attempted)

| Metric | Value |
|--------|-------|
| Converged | Yes (but ran single-slack) |
| Objective | 41,263.94 (identical to a) |
| LMP diff vs (a) | 0.0 |
| Note | `distributed_slack` parameter silently ignored |

### LMP Comparison: (a) vs (b)

| Metric | Value |
|--------|-------|
| Max LMP abs diff | 0.0169 |
| Mean LMP abs diff | 0.0169 |
| Objective diff | 4,355.76 |

LMPs change between configurations (a) and (b), reflecting the different slack bus locations. The LMP differences are small because line constraints are not binding on this network. The objective value difference (4,355.76) is due to the different cost structure (the new generator on bus 30 has a $13.5/MWh linear cost vs the original MATPOWER polynomial cost).

### Reconfiguration Method

Slack bus reconfiguration was achieved by modifying `net.ext_grid.at[0, "bus"]` -- a simple DataFrame cell assignment. No model reconstruction was required.

## Workarounds

None required for configs (a) and (b). Config (c) is not achievable for OPF -- this is a known limitation documented in A-11 (distributed slack only available for power flow, not OPF). The `distributed_slack` parameter is silently ignored by `rundcopp`, which is a minor API friction (no error or warning).

## Timing

- **Wall-clock:** 0.51 s (all three configurations)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b8_reference_bus_config.py`

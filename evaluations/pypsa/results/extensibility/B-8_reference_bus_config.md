---
test_id: B-8
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 3.24
peak_memory_mb: null
loc: 257
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# B-8: Reference Bus Configuration

## Result: PASS

## Approach

Tested three slack/reference bus configurations on the IEEE 39-bus network:

**(a) Default single slack bus:** Ran DC OPF with the slack bus as imported from
MATPOWER (bus 31, type 3 = reference). Used `n.optimize()` directly.

**(b) Different single slack bus:** Changed bus 31 from Slack to PV and bus 30 to
Slack via simple DataFrame edits (`n.buses.loc[bus, 'control'] = ...`), then
re-ran `n.optimize()`.

**(c) Distributed slack:** After OPF, transferred dispatch to `p_set` and ran
`n.pf(distribute_slack=True, slack_weights='p_set')` for AC power flow with
distributed slack proportional to generator dispatch.

## Output

**OPF Results (configs a, b, c):**

| Config | Slack Bus | Objective | Converged |
|--------|-----------|-----------|-----------|
| (a) Default | Bus 31 | 1893.42 | Yes |
| (b) Changed | Bus 30 | 1893.42 | Yes |
| (c) Distributed (OPF) | Bus 31 | 1893.42 | Yes |

**LMP comparison (configs a vs b):**

| Statistic | Value |
|-----------|-------|
| LMPs changed (a vs b) | No |
| Max LMP difference | 0.0 |

All three OPF configurations produce identical LMPs and objectives. This is
mathematically correct: in PyPSA's DCOPF formulation, all generators are decision
variables and power balance is enforced as a constraint. The slack bus designation
does not affect the optimization -- it only matters for power flow.

**Sample LMPs (identical across all configs):**

| Bus | LMP ($/MWh) |
|-----|-------------|
| 1 | 0.3201 |
| 2 | 0.3164 |
| 3 | 0.3316 |
| 4 | 0.3294 |
| 5 | 0.3285 |

**Power flow angle comparison (single vs distributed slack):**

| Statistic | Value |
|-----------|-------|
| Angles changed | Yes |
| Max angle diff | 0.0206 rad (1.18 deg) |

Distributed slack produces different voltage angle profiles as expected -- the
slack power is distributed proportional to generator dispatch rather than
concentrated at a single bus.

## API Configuration Summary

| Config | API Call | Reconstruction Needed |
|--------|---------|----------------------|
| Default slack | `n.optimize(...)` | No |
| Change slack | `n.buses.loc[bus, 'control'] = 'Slack'` | No |
| Distributed slack | `n.pf(distribute_slack=True, slack_weights='p_set')` | No |

All configurations require only DataFrame edits or method parameters. No model
reconstruction is needed for any configuration change. The `distribute_slack`
parameter also supports `'p_nom'`, `'p_nom_opt'`, or custom weight dictionaries.

## Workarounds

None required. Slack bus configuration is fully supported via the public API:
- `n.buses['control']` for single slack assignment (documented)
- `n.pf(distribute_slack=True, slack_weights=...)` for distributed slack (documented)
- Both are API-level changes, no internals accessed

Note: The inherited gencost workaround (manual `marginal_cost` assignment) applies
but is not specific to this test.

## Timing

- **Wall-clock:** 3.24 s (three OPF solves + two AC PF solves)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b8_reference_bus_config.py`

Key API pattern:

```python
# Change slack bus (no reconstruction)
n.buses.loc["31", "control"] = "PV"
n.buses.loc["30", "control"] = "Slack"
n.optimize(solver_name="highs", solver_options={...})

# Distributed slack (power flow)
n.pf(distribute_slack=True, slack_weights="p_set")
```

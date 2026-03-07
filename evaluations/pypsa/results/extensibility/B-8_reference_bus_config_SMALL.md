---
test_id: B-8
tool: pypsa
dimension: extensibility
network: SMALL
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 217.3
peak_memory_mb: null
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# B-8: Reference Bus Configuration (SMALL)

## Result: PASS

## Approach

Tested three slack bus configurations on the 2000-bus network:
- **(a)** Default single slack bus from PPC import (bus 7098)
- **(b)** Changed slack to bus 1004 via DataFrame edit
- **(c)** Distributed slack via `n.pf(distribute_slack=True, slack_weights='p_set')`

## Output

| Config | Converged | Objective ($) | Slack Bus |
|--------|-----------|--------------|-----------|
| (a) Default | Yes | 845,625 | 7098 |
| (b) Changed | Yes | 845,625 | 1004 |
| (c) Distributed | Yes | 845,625 | all (weighted) |

**Key finding:** In PyPSA's DCOPF, the slack bus assignment does NOT affect LMPs because
the optimizer enforces power balance as a constraint. The slack bus only matters for power
flow (angle reference). All three configurations produce identical objectives and LMPs.

**LMP sample (first 5 buses, all configs identical):**

| Bus | LMP ($/MWh) |
|-----|-------------|
| 1001 | 17.56 |
| 1002 | 17.18 |
| 1003 | 17.45 |
| 1004 | 18.06 |
| 1005 | 8.02 |

**Voltage angle comparison (single vs distributed slack PF):** Angles differ
significantly between single and distributed slack power flow, confirming the
distributed slack is functioning correctly.

## API Pattern

Changing the slack bus requires only a DataFrame edit — no model reconstruction:

```python
n.buses.loc[old_slack, 'control'] = 'PV'
n.buses.loc[new_slack, 'control'] = 'Slack'
n.optimize(...)  # No model rebuild needed
```

Distributed slack uses the power flow API:

```python
n.pf(distribute_slack=True, slack_weights='p_set')
```

## Timing

- **Wall-clock:** 217.3 s (3 separate DCOPF solves + 2 PF solves on 2000-bus)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b8_reference_bus_config_small.py`

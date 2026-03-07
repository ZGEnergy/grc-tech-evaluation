---
test_id: A-11
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 1.46
peak_memory_mb: null
loc: 155
solver: PYPOWER interior point
timestamp: 2026-03-06T00:00:00Z
---

# A-11: Solve DC OPF with distributed slack (load-proportional)

## Result: FAIL

## Approach

Checked whether `distributed_slack` parameter is accepted by pandapower's OPF functions. Used `inspect.signature()` to enumerate accepted parameters for `rundcopp()`, `runopp()`, and `runpp()`.

### Parameter Inspection Results

| Function | Has `distributed_slack` | Purpose |
|----------|------------------------|---------|
| `pp.runpp()` | Yes | AC power flow |
| `pp.rundcopp()` | No | DC OPF |
| `pp.runopp()` | No | AC OPF |

Distributed slack is only available for power flow (`runpp`), not for any OPF formulation.

### `rundcopp()` Parameters

`net`, `verbose`, `check_connectivity`, `suppress_warnings`, `switch_rx_ratio`, `delta`, `trafo3w_losses`, `kwargs`

### `runopp()` Parameters

`net`, `verbose`, `calculate_voltage_angles`, `check_connectivity`, `suppress_warnings`, `switch_rx_ratio`, `delta`, `init`, `numba`, `trafo3w_losses`, `consider_line_temperature`, `kwargs`

## Output

### Single-Slack DC OPF (Reference from A-3)

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Objective | 41,263.94 |
| LMP range | 13.517 (uniform) |

### Distributed Slack Power Flow Demonstration

Demonstrated that `pp.runpp(net, distributed_slack=True)` works correctly for power flow:

- Slack weights are settable via `net.gen["slack_weight"]` column (proportional to max_p_mw).
- ACPF with distributed slack converges.
- API: `pp.runpp(net, distributed_slack=True)`

Slack weight distribution (proportional to generator capacity):

| Gen | slack_weight |
|-----|-------------|
| 0 | 0.155 |
| 1 | 0.108 |
| 2 | 0.097 |
| 3 | 0.076 |
| 4 | 0.102 |
| 5 | 0.086 |
| 6 | 0.084 |
| 7 | 0.129 |
| 8 | 0.164 |

### Capability Summary

| Feature | Available |
|---------|-----------|
| Distributed slack for PF | Yes |
| Distributed slack for DC OPF | No |
| Distributed slack for AC OPF | No |
| Slack weight setting via API | Yes (`net.gen["slack_weight"]`) |

## Workarounds

- **What:** No workaround exists for distributed slack in OPF.
- **Why:** `rundcopp()` and `runopp()` do not accept the `distributed_slack` parameter. The PYPOWER interior point solver used by these functions has no distributed slack formulation.
- **Durability:** blocking -- the capability is not present in the OPF formulation. Distributed slack in OPF would require a fundamentally different solver formulation.
- **Grade impact:** pandapower supports distributed slack for power flow analysis (which is useful for studies) but not for economic dispatch/OPF. This limits its usefulness for market-oriented analysis where distributed slack affects LMP computation.

## Timing

- **Wall-clock:** 1.46 s (single-slack DC OPF + distributed slack PF demonstration)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a11_distributed_slack_opf.py`

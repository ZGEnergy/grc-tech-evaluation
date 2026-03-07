---
test_id: B-8
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.173
peak_memory_mb: null
loc: 284
solver: HiGHS
timestamp: 2026-03-06T02:30:00Z
---

# B-8: Reference Bus Configuration

## Result: PASS

## Approach

Solved DC OPF on IEEE 39-bus with three slack bus configurations:
- **(a)** Default single slack (bus 31, index 30)
- **(b)** Different single slack (bus 33, index 32)
- **(c)** Two slack buses (bus 31 + bus 33) as attempted distributed slack

## Output

| Config | Slack Bus(es) | Converged | Total Gen (MW) | LMP Range ($/MWh) |
|--------|--------------|-----------|----------------|-------------------|
| (a) Default | Bus 31 | Yes | 6254.23 | 0.3 -- 0.3 |
| (b) Moved | Bus 33 | Yes | 6254.23 | 0.3 -- 0.3 |
| (c) Multi | Bus 31 + 33 | Yes | 6254.23 | 0.3 -- 0.3 |

### LMP Comparison

LMPs are identical across all three configurations. This is mathematically correct: in a DC OPF LP formulation, the slack bus determines the voltage angle reference but does not affect the economic dispatch or LMPs. All 10 generators in case39.m have identical marginal costs (0.3 $/MWh), so LMPs are uniform regardless of slack selection.

With heterogeneous generator costs, LMPs would differ spatially due to congestion, but would still be independent of the slack bus choice in the LP formulation (unlike in DCPF, where the slack bus absorbs the mismatch).

## API Quality

### Slack Bus Reconfiguration

Slack bus is changed via the `bus.is_slack` boolean property:

```python
for bus in grid.buses:
    bus.is_slack = False
grid.buses[new_idx].is_slack = True
```

- No model reconstruction needed -- property change on existing grid object
- Works before calling `vge.linear_opf()`
- Multiple buses can be set as slack simultaneously

### Bus Slack-Related Attributes

Only `is_slack` found on bus objects. No participation factor or weight attribute for distributed slack weighting in OPF. Distributed slack with custom weights is available for ACPF (`SolverType.NR`) but not for the LP-based OPF.

## Timing

| Config | Wall-clock (s) |
|--------|---------------|
| (a) Default | 0.164 |
| (b) Moved | 0.009 |
| (c) Multi | 0.007 |

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b8_reference_bus_config.py`

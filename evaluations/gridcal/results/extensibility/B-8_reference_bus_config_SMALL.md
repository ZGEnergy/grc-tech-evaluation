---
test_id: B-8
tool: gridcal
dimension: extensibility
network: SMALL
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 2.585
peak_memory_mb: null
loc: 160
solver: HiGHS
timestamp: 2026-03-06T03:00:00Z
---

# B-8: Reference Bus Configuration (SMALL)

## Result: PASS

## Approach

Tested three slack bus configurations on the 2000-bus network via DC OPF:
- (a) Default single slack (WADSWORTH 3, bus 1505)
- (b) Different single slack (O DONNELL 1 1, bus 3)
- (c) Two slack buses (buses 1505 + 3, distributed slack)

## Output

### Configuration Results

| Config | Converged | Total Gen (MW) | LMP Range ($/MWh) | LMP Mean | Solve Time |
|--------|-----------|----------------|-------------------|----------|------------|
| (a) Default slack | Yes | 67,109.21 | 17.702 -- 17.702 | 17.702 | 1.176s |
| (b) Moved slack | Yes | 67,109.21 | 17.702 -- 17.702 | 17.702 | 0.699s |
| (c) Two slack buses | Yes | 67,109.21 | 11.128 -- 32.923 | 18.552 | 0.711s |

### LMP Comparison

| Comparison | Max Absolute Diff | Mean Absolute Diff | Identical |
|------------|-------------------|---------------------|-----------|
| (a) vs (b) | 0.0 | 0.0 | Yes |
| (a) vs (c) | 15.221 | 1.267 | No |

Configs (a) and (b) produce identical LMPs (expected -- the LP formulation is slack-bus-independent for single slack). Config (c) with two slack buses produces different LMPs, confirming the distributed slack changes the optimization.

### API Method

Slack bus reconfigured via `bus.is_slack` property. No model reconstruction needed. Setting multiple buses as slack is supported and changes the OPF formulation.

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b8_reference_bus_config_small.py`

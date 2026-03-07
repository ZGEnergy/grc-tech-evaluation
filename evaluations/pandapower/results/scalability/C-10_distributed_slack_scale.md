---
test_id: C-10
tool: pandapower
dimension: scalability
network: N/A
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# C-10: Distributed slack DC OPF at scale

## Result: FAIL

## Approach

**Skipped.** Dependency test A-11 (distributed slack OPF) FAILED. pandapower supports distributed slack for power flow (`pp.runpp(net, distributed_slack=True)`) but NOT for OPF (`pp.rundcopp()` / `pp.runopp()`). The `distributed_slack` parameter is not accepted by OPF functions. Without distributed slack OPF capability, scalability testing is not applicable.

## Output

No test executed.

## Workarounds

None possible. Distributed slack is a power-flow-only feature in pandapower.

## Timing

- **Wall-clock:** N/A
- **Peak memory:** N/A

## Test Script

No test script written (dependency A-11 failed).

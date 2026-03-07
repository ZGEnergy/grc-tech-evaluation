---
test_id: C-8
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

# C-8: SCOPF (N-1, 500 contingencies) at scale

## Result: FAIL

## Approach

**Skipped.** Dependency test A-9 (SCOPF) FAILED. pandapower has no native security-constrained OPF capability. It cannot formulate or solve a SCOPF problem where contingency constraints are enforced within the optimization. While contingency sweeps are possible (see C-5), incorporating contingency constraints into the OPF formulation itself is not supported.

## Output

No test executed.

## Workarounds

None possible. SCOPF is outside pandapower's optimization capabilities.

## Timing

- **Wall-clock:** N/A
- **Peak memory:** N/A

## Test Script

No test script written (dependency A-9 failed).

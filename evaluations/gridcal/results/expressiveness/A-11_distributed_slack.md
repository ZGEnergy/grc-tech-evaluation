---
test_id: A-11
tool: gridcal
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: 55
solver: "HiGHS"
timestamp: 2026-03-06T03:00:00Z
---

# A-11: Distributed Slack OPF (Grade: SMALL)

## Result: FAIL

Same failure as TINY -- not re-tested on grade network. The failure is architectural:

1. No `distributed_slack` option in `OptimalPowerFlowOptions`.
2. Distributed slack exists only in ACPF (`PowerFlowOptions`), not in OPF.
3. ACPF distributed slack cannot produce LMPs (shadow prices require OPF).
4. No participation factor attributes on generators.

These are fundamental capability gaps unrelated to network size.

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a11_distributed_slack.py` (TINY version; grade test not run)

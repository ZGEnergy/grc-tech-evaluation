---
test_id: C-10
tool: gridcal
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: 0
solver: "HiGHS"
timestamp: 2026-03-06T04:00:00Z
---

# C-10: Distributed Slack Scale (Grade: MEDIUM)

## Result: FAIL

Not tested. Distributed slack OPF failed at the TINY tier (A-11) due to architectural limitations:

1. No `distributed_slack` option in `OptimalPowerFlowOptions`.
2. Distributed slack exists only in ACPF (`PowerFlowOptions`), not in OPF.
3. ACPF distributed slack cannot produce LMPs (shadow prices require OPF).
4. No participation factor attributes on generators.

These are fundamental capability gaps unrelated to network size. No scalability test is possible.

## Reference

- **A-11 result:** FAIL
- **Test script:** N/A (not run)

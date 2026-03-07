---
test_id: C-4
tool: gridcal
dimension: scalability
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: null
peak_memory_mb: null
loc: 0
solver: "HiGHS"
timestamp: 2026-03-06T04:00:00Z
---

# C-4: SCUC Scale (Grade: SMALL)

## Result: FAIL

Not tested. SCUC failed at the TINY tier (A-5) due to architectural limitations:

1. Time-series OPF crashes with `ValueError: 0 is not a valid TapPhaseControl` on MATPOWER files.
2. Snapshot UC has no inter-temporal coupling (no ramp/min-up-down enforcement).
3. Even if time-series OPF worked, UC constraints are not enforced (issue #397).

These are fundamental capability gaps unrelated to network size. No scalability test is possible.

## Reference

- **A-5 result:** FAIL (blocking)
- **Test script:** N/A (not run)

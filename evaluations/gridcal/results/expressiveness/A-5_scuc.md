---
test_id: A-5
tool: gridcal
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: null
peak_memory_mb: null
loc: 85
solver: "HiGHS"
timestamp: 2026-03-06T03:00:00Z
---

# A-5: SCUC (Grade: SMALL)

## Result: FAIL

Same failure as TINY -- not re-tested on grade network. The failure is architectural:

1. Time-series OPF crashes with `ValueError: 0 is not a valid TapPhaseControl`.
2. Snapshot UC has no inter-temporal coupling (no ramp/min-up-down enforcement).
3. Even if time-series OPF worked, issue #397 indicates UC constraints are not enforced.

These are fundamental capability gaps unrelated to network size.

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a5_scuc.py` (TINY version; grade test not run)

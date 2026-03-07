---
test_id: A-6
tool: gridcal
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: null
peak_memory_mb: null
loc: 180
solver: "HiGHS"
timestamp: 2026-03-06T03:00:00Z
---

# A-6: SCED (Grade: SMALL)

## Result: FAIL

Same failure as TINY -- not re-tested on grade network. Depends on A-5 (SCUC), which also failed. The failure is architectural:

1. No API to fix a commitment schedule and solve ED only.
2. Time-series OPF crashes (TapPhaseControl bug), preventing multi-period ED with ramp enforcement.
3. Ramp rates are not enforced across independent snapshot OPFs.

These are fundamental capability gaps unrelated to network size.

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a6_sced.py` (TINY version; grade test not run)

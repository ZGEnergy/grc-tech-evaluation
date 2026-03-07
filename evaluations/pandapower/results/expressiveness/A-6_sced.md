---
test_id: A-6
tool: pandapower
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# A-6: Fix commitment schedule from A-5, solve economic dispatch as LP/QP

## Result: FAIL

## Approach

Skipped on MEDIUM. A-6 FAILED on TINY because it depends on A-5 (SCUC), which failed due to pandapower having no unit commitment formulation. Without a commitment schedule, the two-stage UC/ED workflow cannot be demonstrated. pandapower also lacks multi-period temporal optimization and ramp rate constraints needed for SCED.

See `A-6_sced_TINY.md` for full analysis.

## Workarounds

- **What:** No workaround exists.
- **Why:** Depends on A-5 (failed) and requires multi-period temporal constraints absent from pandapower.
- **Durability:** blocking
- **Grade impact:** Complete capability gap.

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a6_sced.py`

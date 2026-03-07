---
test_id: A-5
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

# A-5: Solve 24-hour unit commitment as MILP

## Result: FAIL

## Approach

Skipped on MEDIUM. A-5 FAILED on TINY due to architectural limitation: pandapower has no MILP solver interface, no unit commitment formulation, no temporal optimization, and no binary commitment variables. This is a fundamental capability gap that does not depend on network size.

See `A-5_scuc_TINY.md` for full analysis.

## Workarounds

- **What:** No workaround exists.
- **Why:** SCUC requires MILP formulation with temporal constraints, architecturally absent from pandapower.
- **Durability:** blocking
- **Grade impact:** Complete capability gap.

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a5_scuc.py`

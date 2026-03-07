---
test_id: A-9
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

# A-9: Solve security-constrained OPF (SCOPF)

## Result: FAIL

## Approach

Skipped on MEDIUM. A-9 FAILED on TINY due to architectural limitation: pandapower has no native SCOPF formulation. SCOPF requires simultaneous optimization of base case and contingency scenarios with coupled constraints, which is not supported.

See `A-9_scopf_TINY.md` for full analysis.

## Workarounds

- **What:** No workaround exists. SCOPF requires joint optimization across contingency scenarios.
- **Why:** pandapower solves single-snapshot problems only.
- **Durability:** blocking
- **Grade impact:** Complete capability gap.

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a9_scopf.py`

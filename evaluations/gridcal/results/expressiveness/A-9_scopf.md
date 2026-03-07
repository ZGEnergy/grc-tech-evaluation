---
test_id: A-9
tool: gridcal
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: 60
solver: "HiGHS"
timestamp: 2026-03-06T03:00:00Z
---

# A-9: SCOPF (Grade: SMALL)

## Result: FAIL

Same failure as TINY -- not re-tested on grade network. The failure is architectural:

1. `consider_contingencies` flag in OPF options does not modify the optimization formulation.
2. OPF with contingencies produces identical dispatch to baseline (constraints are ignored).
3. `ContingencyAnalysis` is post-hoc N-1 screening, not preventive SCOPF.
4. No custom constraint injection API to build SCOPF manually.

These are fundamental capability gaps unrelated to network size (issue #364).

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a9_scopf.py` (TINY version; grade test not run)

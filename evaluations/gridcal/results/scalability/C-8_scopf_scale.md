---
test_id: C-8
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

# C-8: SCOPF Scale (Grade: MEDIUM)

## Result: FAIL

Not tested. SCOPF failed at the TINY tier (A-9) due to architectural limitations:

1. `consider_contingencies` flag in OPF options does not modify the optimization formulation.
2. OPF with contingencies produces identical dispatch to baseline (constraints are ignored).
3. `ContingencyAnalysis` is post-hoc N-1 screening, not preventive SCOPF.
4. No custom constraint injection API to build SCOPF manually (issue #364).

These are fundamental capability gaps unrelated to network size. No scalability test is possible.

## Reference

- **A-9 result:** FAIL
- **Test script:** N/A (not run)

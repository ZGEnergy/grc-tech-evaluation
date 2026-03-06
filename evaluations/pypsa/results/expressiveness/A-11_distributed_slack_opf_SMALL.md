---
test_id: A-11
tool: pypsa
dimension: expressiveness
network: SMALL
status: fail
workaround_class: blocking
wall_clock_seconds: 0
peak_memory_mb: null
loc: 0
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# A-11: Distributed Slack OPF on SMALL (ACTIVSg2000)

## Result: FAIL

## Approach
`n.optimize()` does not support distributed slack. This was confirmed as FAIL on TINY. The limitation carries forward to SMALL.

## Output
No test script run. PyPSA's OPF inherently distributes generation via cost minimization, but there is no way to specify participation factors for slack distribution. The `distribute_slack` parameter only applies to `n.pf()` (power flow), not `n.optimize()` (OPF).

## Workarounds
No workaround available. This is a blocking limitation of PyPSA's OPF formulation.

## Timing
- Wall-clock: 0s (no test run)
- Peak memory: null

## Test Script
Path: N/A (known FAIL from TINY)

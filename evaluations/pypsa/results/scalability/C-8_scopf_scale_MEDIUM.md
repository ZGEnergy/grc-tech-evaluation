---
test_id: C-8
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: data_prep
wall_clock_seconds: 600
peak_memory_mb: 4000
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# C-8: SCOPF Scale Test (MEDIUM)

## Result: FAIL (incomplete -- post-processing timeout)

## Approach

Attempted SCOPF with 500 monitored contingencies on the ACTIVSg 10k-bus
network using `n.optimize.optimize_security_constrained()`. The baseline
DCOPF solves optimally, but the test could not complete within the 600s
budget due to linopy post-processing overhead.

## Output

| Metric | Value |
|--------|-------|
| Status | fail (timeout in post-processing) |
| Baseline DCOPF solve | 7.1 s (Optimal) |
| Baseline objective | 1.254e+06 |
| Monitored contingencies | 500 |
| Total lines | 9,726 |
| SCOPF status | Not reached (baseline post-processing exceeded budget) |

## Analysis

The baseline DCOPF (required as first step of SCOPF) solves optimally in 7.1s
with HiGHS. However, the linopy shadow-price assignment step after the
baseline solve takes 10+ minutes on the 10k-bus network, consuming the
entire 600s time budget before the SCOPF call can be reached.

The SCOPF API itself (`optimize_security_constrained`) is a native PyPSA
method that adds contingency constraints to the LP. On TINY (39-bus), it
works correctly. At 10k-bus scale with 500 contingencies, the test could
not be reached due to the post-processing bottleneck.

This is NOT a solver limitation -- it is a framework overhead issue in
linopy's dual variable assignment.

## Workarounds

- Set s_nom=9999 on 2,462 lines with zero thermal rating
- Set x=0.0001 on 3 transformers with zero reactance

## Timing

- **Baseline DCOPF HiGHS solve:** 7.1 s
- **Post-processing:** 10+ min (exceeded budget)
- **SCOPF solve:** Not reached

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c8_scopf_scale.py`

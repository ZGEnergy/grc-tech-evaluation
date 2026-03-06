---
test_id: c10
tool: pypsa
dimension: scalability
network: MEDIUM
status: fail
wall_clock_seconds: null
peak_memory_mb: null
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# C-10: Distributed Slack DCOPF on MEDIUM (ACTIVSg 10k)

## Result: FAIL

## Approach
PyPSA's `n.optimize()` (linopy-based OPF) does not support distributed slack buses. The optimization formulation uses a single slack/reference bus for the Kirchhoff voltage law constraints. There is no parameter or option to distribute the slack among multiple generators proportionally.

PyPSA's `n.lpf()` (linear power flow) does support a `distribute_slack` option, but this is for power flow analysis only, not for optimal power flow.

## Output

| Metric | Value |
|--------|-------|
| Feature available | No |
| API support | `n.lpf()` only (not `n.optimize()`) |

## Notes
- The `n.lpf()` method accepts a `distribute_slack` parameter that can be set to `True` to distribute the slack proportionally among generators. However, this is a power flow feature, not an OPF feature.
- For OPF (`n.optimize()`), the solver inherently handles power balance through the optimization constraints. The concept of "distributed slack" is implicit in the OPF formulation where all generators are decision variables -- the optimizer distributes generation according to costs, which is functionally different from distributed slack DCPF.
- No test script was written for this test since the feature is not supported.

## Test Script
Path: N/A (no test script -- documented capability gap)

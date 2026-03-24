---
test_id: C-4
tool: powermodels
dimension: scalability
network: SMALL
protocol_version: v11
skill_version: v2
test_hash: 229e85b4
status: fail
workaround_class: null
blocked_by: A-5
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
cpu_threads_used: null
cpu_threads_available: null
timestamp: 2026-03-24T16:00:00Z
---

# C-4: SCUC Scale — SMALL (ACTIVSg 2000-bus)

## Result: FAIL

## Approach

C-4 tests 24-hour SCUC as MILP on the SMALL (ACTIVSg 2000-bus) network. This test is **blocked by A-5**, which established that PowerModels.jl v0.21.5 does not natively support Security-Constrained Unit Commitment (SCUC). The tool is a steady-state single-period power network optimization library; unit commitment -- requiring binary commitment variables, minimum up/down time constraints, startup/shutdown costs, and multi-period coupling -- is entirely outside its scope.

Since A-5 failed with `failure_reason: unsupported_in_installed_version`, C-4 is a cascaded failure. No SCUC test was attempted at SMALL scale.

## Output

Not applicable. Test not executed due to cascaded failure from A-5.

| Metric | Value |
|--------|-------|
| Blocked by | A-5 (SCUC unsupported) |
| 1-thread timing | N/A |
| Max-thread timing | N/A |

## Workarounds

None attempted. The prerequisite capability (SCUC) does not exist in the tool.

## Timing

- **Wall-clock:** N/A (test not executed)
- **Timing source:** N/A
- **Peak memory:** N/A
- **CPU threads used:** N/A
- **CPU threads available:** N/A

## Test Script

No test script executed. See prior v10 script at `evaluations/powermodels/tests/scalability/test_c4_scuc_scale_small.jl` for reference on the user-assembled JuMP MILP approach that was used in the v10 evaluation (before A-5 was reclassified as fail under v11).

## Observations

- [cascaded-failure observation](../observations/cascaded-failure-scalability-C-4_scuc_blocked_by_A5.md)

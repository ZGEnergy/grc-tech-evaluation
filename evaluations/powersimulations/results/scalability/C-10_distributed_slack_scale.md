---
test_id: C-10
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: HiGHS
timestamp: "2026-03-07T05:30:00Z"
---

# C-10: Distributed Slack OPF Scale — MEDIUM

## Result: FAIL

## Rationale

PowerSimulations.jl has **no native distributed slack formulation** for OPF. The
`PTDFPowerModel` uses a single reference bus (the system slack) implicitly.

The A-11 test on TINY requires manual reformulation to implement distributed slack
weights, which is beyond PSI's built-in capabilities. Scaling this manual approach
to the MEDIUM network (10,000 buses) is not feasible without a native implementation.

PSI's `DCPPowerModel` (via PowerModels.jl) also uses single-slack formulation.
No configuration option exists to switch to distributed slack weights.

## Dependency

This test depends on A-11 (distributed slack OPF on TINY). Since PSI lacks this
capability natively, the MEDIUM-scale test cannot proceed.

## Test Script

No test script — blocked by missing A-11 capability.

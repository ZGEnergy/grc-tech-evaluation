---
test_id: C-8
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

# C-8: SCOPF Scale — N-1 SCOPF on MEDIUM

## Result: FAIL

## Rationale

PowerSimulations.jl has **no native SCOPF formulation**. The A-9 SCOPF test on TINY
required manually building contingency constraints via PTDF matrix multiplication and
JuMP's `@constraint` macro on the extracted jump model. This approach is theoretically
possible on MEDIUM (10,000 buses, 12,706 branches) but would require:

1. Computing PTDF matrix (12706 × 10000) — feasible per C-9
2. Computing LODF matrix for N-1 post-contingency flows — O(branches²) memory
3. Adding 500 × monitored_branches constraints to the JuMP model

The LODF-based approach for 500 contingencies on 12,706 branches would generate
approximately 6.35 million additional constraints, which is computationally prohibitive
without the iterative contingency screening that a native SCOPF implementation provides.

## Dependency

This test depends on A-9 (SCOPF on TINY). Since PSI lacks native SCOPF, scaling to
MEDIUM is not feasible without a custom implementation that goes well beyond what the
tool provides.

## Test Script

No test script — blocked by missing A-9 capability at scale.

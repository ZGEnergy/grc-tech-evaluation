---
test_id: C-1
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.85
peak_memory_mb: 121.3
loc: 103
solver: null
timestamp: 2026-03-07T00:00:00Z
---

# C-1: DCPF Scalability on MEDIUM (ACTIVSg 10000-bus)

## Result: PASS

## Metrics

| Metric | Value |
|--------|-------|
| Parse time | 1.62s |
| Solve time | 0.234s |
| Wall-clock (parse + solve) | 1.85s |
| Peak memory (total live) | 121.3 MB |
| Memory delta (DCPF only) | 81.8 MB |
| CPU utilization | Single-threaded (direct solve) |
| Network size | 10,000 buses, 12,706 branches |

## Scaling Context

Compared to TINY (39-bus, solve ~0.0006s), the 10,000-bus DCPF solve takes 0.234s -- a ~390x increase for a ~256x increase in bus count. This is consistent with the O(n^1.2-1.5) expected complexity of sparse direct linear solvers on power system matrices.

Parse time (1.62s) dominates total wall-clock. The MATPOWER text parser scales linearly with file size.

## Methodology

- JIT warm-up: solved case39 DCPF before timing
- Timing: `time()` calls around parse and solve separately
- Memory: `Base.gc_live_bytes()` before and after (approximation; Julia GC makes precise peak measurement difficult)
- Single invocation (no averaging) after warm-up

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a1_dcpf_medium.jl`
Batch runner: `evaluations/powermodels/tests/test_medium_all.jl`

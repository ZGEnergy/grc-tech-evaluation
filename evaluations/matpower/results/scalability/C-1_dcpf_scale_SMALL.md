---
test_id: C-1
tool: matpower
dimension: scalability
network: SMALL
protocol_version: v10
skill_version: v1
test_hash: 5d7a4436
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.103
timing_source: measured
peak_memory_mb: 1.9
convergence_residual: null
convergence_iterations: null
loc: 96
solver: null
timestamp: 2026-03-14T00:00:00Z
---

# C-1: DCPF on SMALL — wall-clock time and peak memory

## Result: PASS

## Approach

Ran `rundcpf(mpc, mpopt)` on ACTIVSg 2000-bus network with suppressed output
(`verbose=0, out.all=0`). DCPF is a direct linear solve (no iterative solver needed).
Timing measured with `tic/toc` around the `rundcpf` call only (excludes network loading).
Peak memory measured via `/proc/self/status` VmHWM.

## Output

| Metric | Value |
|--------|-------|
| Buses | 2000 |
| Branches | 3206 |
| Generators | 544 |
| Wall clock | 0.103 s |
| Peak memory (VmHWM) | 1.9 MB |
| Total generation | 67,109.21 MW |
| Total load | 67,109.21 MW |
| Max branch flow | 2,438.74 MW |
| Nonzero voltage angles | 1999 / 2000 |
| Angle range | [-35.34, 41.73] deg |

DCPF converged immediately with balanced generation/load and meaningful voltage angles
across all non-slack buses.

## Workarounds

None required.

## Timing

- **Wall-clock:** 0.103 s
- **Timing source:** measured
- **Peak memory:** 1.9 MB (VmHWM — includes Octave runtime baseline)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/scalability/test_c1_dcpf_scale_SMALL.m`

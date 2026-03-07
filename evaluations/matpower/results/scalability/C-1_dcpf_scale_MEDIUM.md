---
test_id: C-1
tool: matpower
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.0142
peak_memory_mb: 4.2
loc: 40
timestamp: "2026-03-06T16:00:00Z"
---

# C-1: DCPF Scale (MEDIUM, ACTIVSg 10k)

## Result: PASS

## Approach

Standard `rundcpf(mpc, mpopt)` on ACTIVSg 10k (10,000 buses, 12,706 branches, 2,485 generators). No modifications needed. Verbose output suppressed via `mpoption('verbose', 0, 'out.all', 0)`.

## Output

| Metric | Value |
|--------|-------|
| Buses | 10,000 |
| Branches | 12,706 |
| Generators | 2,485 |
| Case load time | 4.53s |
| **Solve time** | **1.01s** |
| Total wall clock | 5.77s |
| Voltage angle range | [-71.04, 55.48] degrees |
| Voltage angle std dev | 25.03 degrees |
| Max line flow | 2,035 MW |
| Mean abs(flow) | 89.1 MW |
| Non-zero flows | 11,990 / 12,706 |
| Total generation | 150,917 MW |
| Total load | 150,917 MW |

## Timing

- Case load: 4.53s (dominated by parsing the large .m file)
- DCPF solve: 1.01s (sparse linear system solve)
- Total: 5.77s
- Peak memory estimate: ~4.2 MB for data structures + 0.6 MB for sparse B matrix

## Notes

- DCPF on 10k buses solves in ~1 second on Octave — well within practical limits
- Load time (4.5s) dominates total time; the actual linear solve is fast
- All 10,000 buses have non-trivial voltage angles, confirming a meaningful solution

## Test Script

`evaluations/matpower/tests/scalability/test_c1_dcpf_scale_medium.m`

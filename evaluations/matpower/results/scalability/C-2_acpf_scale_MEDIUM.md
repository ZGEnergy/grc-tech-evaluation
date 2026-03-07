---
test_id: C-2
tool: matpower
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.1507
peak_memory_mb: null
loc: 60
timestamp: "2026-03-06T16:00:00Z"
---

# C-2: ACPF Scale (MEDIUM, ACTIVSg 10k)

## Result: PASS

## Approach

Standard `runpf(mpc, mpopt)` with Newton-Raphson (default) on ACTIVSg 10k. Flat start (default). No warm start or convergence fallback needed.

## Output

| Metric | Value |
|--------|-------|
| Solver | Newton-Raphson (built-in) |
| Iterations | 4 |
| Converged | Yes |
| **Solve time** | **1.15s** |
| Total wall clock | 2.31s |
| Vm range | [0.957, 1.089] pu |
| Va range | [-90.4, 17.3] degrees |
| Max P flow | 2,775 MW |
| Max Q flow | 3,530 MVAr |
| Total P generation | 153,503 MW |
| Total P load | 150,917 MW |
| Total P losses | 2,586 MW (1.71%) |

## Timing

- Case load: 1.11s
- AC PF solve: 1.15s (4 Newton iterations)
- Total: 2.31s

## Notes

- AC power flow converges from flat start in only 4 Newton iterations on the 10k bus system
- Solve time (1.15s) is comparable to DCPF (1.01s) — the Newton method is efficient
- Losses are 1.71% of load, a reasonable value for a large network
- No convergence difficulties; flat start is sufficient

## Test Script

`evaluations/matpower/tests/scalability/test_c2_acpf_scale_medium.m`

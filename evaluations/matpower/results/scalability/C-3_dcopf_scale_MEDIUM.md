---
test_id: C-3
tool: matpower
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 107.76
peak_memory_mb: null
loc: 80
timestamp: "2026-03-06T16:00:00Z"
---

# C-3: DC OPF Scale (MEDIUM, ACTIVSg 10k)

## Result: PASS

## Approach

DC OPF on ACTIVSg 10k with two solvers: MIPS (native QP, quadratic costs) and GLPK (LP, requires PWL cost conversion). 19.4% of branches have zero RATE_A — set to 9999 MW to avoid unbounded flows.

## Output

| Metric | MIPS | GLPK |
|--------|------|------|
| Converged | Yes | Yes |
| **Solve time** | **9.72s** | **92.99s** |
| Objective | $2,436,631.23/hr | $2,436,635.72/hr |
| Total generation | 150,917 MW | 150,917 MW |
| LMP range | [20.74, 20.74] | [20.74, 20.74] |
| Binding branch constraints | 0 | 0 |

### Cross-Solver Consistency

| Metric | Value |
|--------|-------|
| Objective difference | $4.50/hr (1.84e-6 relative) |
| Max dispatch difference | 22.7 MW |
| Max LMP difference | $0.001/MWh |

## Timing

- Case load + prep: 4.22s
- MIPS solve: 9.72s
- GLPK solve: 93.0s (9.6x slower — LP reformulation + simplex vs interior point)
- Total: 107.8s

## Notes

- Uniform LMPs ($20.74/MWh) indicate no binding branch constraints — the network is uncongested at this operating point with 9999 MW limits on zero-RATE_A branches
- MIPS (interior point QP) is ~10x faster than GLPK (simplex LP with PWL costs)
- Objective values are consistent across solvers (1.84e-6 relative difference from PWL approximation)
- Zero-RATE_A handling: 2,462 of 12,706 branches (19.4%) had zero RATE_A; setting to large value is the standard MATPOWER convention

## Test Script

`evaluations/matpower/tests/scalability/test_c3_dcopf_scale_medium.m`

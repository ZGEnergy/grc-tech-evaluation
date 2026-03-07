---
test_id: C-3
tool: gridcal
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 15.17
peak_memory_mb: 127.15
loc: 35
solver: "HiGHS"
timestamp: 2026-03-06T04:00:00Z
---

# C-3: DC OPF Scale (Grade: MEDIUM)

## Result: PASS

## Network

ACTIVSg10k -- 10,000 buses, 12,706 branches, 2,485 generators.

## Approach

`vge.linear_opf()` with HiGHS solver on the 10k-bus network.

## Output

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Solve time | 15.17s |
| Peak memory (solve) | 127.15 MB |
| File load time | 11.57s |
| Total generation (MW) | 150,916.88 |
| Active generators | 1,937 / 2,485 |
| LMP range | 20.064 to 20.064 |
| LMP mean | 20.064 |
| Max loading | 84.72% |
| Binding branches | 0 |
| Load shedding | 0.0 MW |

## Scaling

DC OPF solves in 15.2s on 10k buses with HiGHS. Uniform LMPs (all 20.064) indicate no binding transmission constraints, consistent with zero binding branches. Memory footprint is modest at 127 MB.

## Workarounds

None required.

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c3_dcopf_scale.py`

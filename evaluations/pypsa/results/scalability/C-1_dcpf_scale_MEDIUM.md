---
test_id: C-1
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: data_prep
wall_clock_seconds: 36.8
peak_memory_mb: 2382
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# C-1: DCPF Scale Test (MEDIUM)

## Result: PASS

## Approach

Ran DC power flow (linear power flow) on the ACTIVSg 10k-bus network using
`n.lpf()`. Required fixing 3 transformers with zero reactance (x=0.0001) to
avoid singular matrix in the B-matrix factorization.

## Output

| Metric | Value |
|--------|-------|
| Status | pass |
| Wall-clock (total) | 36.8 s |
| Network load time | 8.5 s |
| Solve time (LPF) | 28.3 s |
| Peak memory | 2,382 MB |
| Buses | 10,000 |
| Generators | 2,485 |
| Lines | 9,726 |
| Transformers | 2,980 |
| Loads | 4,170 |
| Voltage angle range | -0.437 to 2.707 rad |
| Line flow range | -1,936 to 1,781 MW |
| Power balance (sum) | ~0 MW |

## Analysis

DCPF on the 10k-bus network converges successfully in ~28s solve time. The
B-matrix factorization is the dominant cost. Output is structured as pandas
DataFrames (voltage angles, line flows, nodal injections).

The ACTIVSg 10k case has 3 transformers with zero reactance which cause a
singular admittance matrix. Setting x=0.0001 on these transformers is required
as a workaround.

## Workarounds

- Set x=0.0001 on 3 transformers with zero reactance to avoid singular matrix

## Timing

- **Wall-clock:** 36.8 s
- **Solve time:** 28.3 s
- **Peak memory:** 2,382 MB

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c1_dcpf_scale.py`

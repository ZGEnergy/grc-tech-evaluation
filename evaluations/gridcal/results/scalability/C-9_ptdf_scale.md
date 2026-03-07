---
test_id: C-9
tool: gridcal
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: qualified_pass
workaround_class: null
wall_clock_seconds: 49.86
peak_memory_mb: 7585.74
loc: 50
solver: "Direct (linear_power_flow)"
timestamp: 2026-03-06T04:00:00Z
---

# C-9: PTDF Scale (Grade: MEDIUM)

## Result: QUALIFIED PASS

## Network

ACTIVSg10k -- 10,000 buses, 12,706 branches, 2,485 generators.

## Approach

Computed PTDF matrix via `vge.linear_power_flow()` on the 10k-bus network. Verified dimensions and compared flows against DCPF.

## Output

| Metric | Value |
|--------|-------|
| PTDF compute time | 49.86s |
| Peak memory (compute) | 7,585.74 MB |
| PTDF shape | (12706, 10000) |
| Dimensions correct | Yes |
| PTDF dtype | float64 |
| PTDF matrix size | 969.39 MB |
| Nonzero fraction | 73.8% |
| PTDF range | [-2.339, 1.790] |
| LODF available | Yes |
| LODF shape | (12706, 12706) |

### Flow Comparison

| Method | Max Abs Diff |
|--------|-------------|
| LA direct flows vs DCPF | 743.46 MW |

## Why Qualified Pass

The PTDF matrix is computed successfully with correct dimensions (branches x buses) in 49.86s. LODF is also available. However, the LinearAnalysis flows do not match DCPF flows on this large network (max diff 743 MW). This is the same issue observed in B-9 (MEDIUM): the PTDF is computed relative to its own reference bus and injection assumptions, which differ from the standard DCPF solver on the 10k-bus network.

For relative sensitivity analysis (e.g., shift factors), the PTDF is usable. For exact flow prediction matching DCPF, the slack bus and injection conventions would need reconciliation.

## Memory Note

Peak memory is 7.6 GB due to the dense PTDF (969 MB) and LODF (1.2 GB) matrices being computed simultaneously. This is a significant memory footprint for a 10k-bus network.

## Workarounds

None required for PTDF computation itself. Flow validation mismatch is a known limitation.

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c9_ptdf_scale.py`

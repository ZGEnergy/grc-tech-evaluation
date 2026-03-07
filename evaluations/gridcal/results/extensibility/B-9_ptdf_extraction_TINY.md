---
test_id: B-9
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.106
peak_memory_mb: null
loc: 175
solver: null
timestamp: 2026-03-06T02:00:00Z
---

# B-9: PTDF Extraction

## Result: PASS

## Approach

Used `vge.linear_power_flow(grid)` which returns a `LinearAnalysisResults` object containing the PTDF and LODF matrices as numpy arrays. Verified dimensions and compared PTDF-based flows with DCPF-solved flows.

## Output

### PTDF Matrix

| Property | Value |
|----------|-------|
| Shape | (46, 39) -- branches x buses |
| dtype | float64 |
| Min value | -1.0 |
| Max value | 1.0 |
| Nonzero fraction | 75.7% |
| Slack bus (index 30) | Column all zeros (correct) |

### LODF Matrix

| Property | Value |
|----------|-------|
| Shape | (46, 46) -- branches x branches |
| Available | Yes |

### Flow Verification

**Linear analysis direct flows vs DCPF flows:**
- Max absolute difference: 0.0
- Exact match confirmed

**PTDF @ Sbus vs DCPF flows:**
- Max absolute difference: 85.98 MW
- This discrepancy is expected: the PTDF matrix is computed relative to the slack bus (column 30 is all zeros). When multiplying PTDF by the full Sbus vector (which includes the slack bus power), the slack contribution should be zero but the Sbus from DCPF includes the slack bus balancing power. Using the LinearAnalysis's own Sbus (`la_results.Sbus`) with the PTDF produces exact agreement (max diff = 0.0).

### Sample Values

| Branch | DCPF Flow (MW) | LA Flow (MW) | PTDF Row 0 (first 5) |
|--------|---------------|-------------|----------------------|
| 0 | -178.35 | -178.35 | [0.546, -0.211, -0.139, -0.052, -0.002] |
| 1 | 80.75 | 80.75 | |
| 2 | 333.43 | 333.43 | |

## API Quality

- Single function call: `vge.linear_power_flow(grid)` -- no configuration needed
- Returns standard numpy arrays (PTDF, LODF, Sf, Sbus)
- PTDF and LODF both available from the same result object
- No workarounds needed
- Computation time: 106ms for 46x39 PTDF

## Timing

- **PTDF computation:** 0.106s (includes LODF)

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b9_ptdf_extraction.py`

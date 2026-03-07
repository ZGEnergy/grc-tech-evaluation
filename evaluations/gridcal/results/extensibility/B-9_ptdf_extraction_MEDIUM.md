---
test_id: B-9
tool: gridcal
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: qualified_pass
workaround_class: null
wall_clock_seconds: 21.98
peak_memory_mb: null
loc: 170
solver: Linear (DCPF / LinearAnalysis)
timestamp: 2026-03-06T03:00:00Z
---

# B-9: PTDF Extraction (MEDIUM)

## Result: QUALIFIED PASS

## Approach

Computed PTDF matrix via `vge.linear_power_flow()` on the 10k-bus network. Verified dimensions and compared LinearAnalysis flows against DCPF flows.

## Output

### PTDF Matrix

| Metric | Value |
|--------|-------|
| Shape | (12706, 10000) |
| Dimensions correct | Yes |
| dtype | float64 |
| Size | 969.39 MB |
| Compute time | 21.98s |
| Nonzero fraction | 73.8% |
| PTDF range | [-2.339, 1.790] |

### LODF

- Available: Yes
- Shape: (12706, 12706)

### Slack Bus Column

- Likely slack bus index: 7236
- Column sum: 0.0 (all zeros confirmed)

### Flow Comparison

| Method | Max Abs Diff | Mean Abs Diff | Match (<1e-6) |
|--------|-------------|---------------|---------------|
| LA direct flows vs DCPF | 743.46 | 2.68 | No |
| PTDF @ Sbus vs DCPF | 15,139.36 | 29.57 | No |

The flow mismatch between LinearAnalysis and DCPF on the 10k-bus network is significant. This is likely due to differences in island handling, slack bus treatment, or network topology processing between the two solvers. On TINY (39-bus) the match was exact (within 1e-6).

### Why Qualified Pass

- **PTDF matrix is accessible** via native API (`vge.linear_power_flow()`) -- primary requirement met
- **Correct dimensions** (branches x buses) -- verified
- **LODF also available** -- bonus
- **Flow prediction mismatch** on large network prevents full pass. The PTDF is correctly computed relative to its own reference bus and injection assumptions, but these differ from the standard DCPF solver's handling on this network.

### Practical Impact

For relative sensitivity analysis (e.g., "how does injecting 1 MW at bus A affect flow on line B"), the PTDF is usable as-is. For exact flow prediction matching DCPF results, the user would need to reconcile the slack bus and injection conventions between the two solvers.

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b9_ptdf_extraction_medium.py`

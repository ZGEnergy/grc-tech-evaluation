---
test_id: B-5
tool: gridcal
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.457
peak_memory_mb: null
loc: 120
solver: Linear (DCPF)
timestamp: 2026-03-06T03:00:00Z
---

# B-5: Interoperability (MEDIUM)

## Result: PASS

## Approach

Ran DCPF on 10k-bus network and exported results to pandas DataFrames via `get_bus_df()` and `get_branch_df()`. Verified CSV roundtrip.

## Output

### DataFrame Export

| DataFrame | Shape | Columns |
|-----------|-------|---------|
| Bus | (10000, 4) | Vm, Va, P, Q |
| Branch | (12706, 7) | Pf, Qf, Pt, Qt, loading, Ploss, Qloss |

### Timing

| Step | Time |
|------|------|
| DCPF solve | 0.378s |
| DataFrame export | 5.2ms |
| CSV write | 74.0ms |

### CSV File Sizes

| File | Size |
|------|------|
| Bus CSV | 773 KB |
| Branch CSV | 1,080 KB |

### Export Characteristics

- Lines beyond solve: 4 (get_bus_df, get_branch_df, 2x to_csv)
- Standard pandas DataFrames: Yes
- Custom serialization needed: No
- CSV roundtrip verified: Yes (shapes match)

## API Quality

- `results.get_bus_df()` and `results.get_branch_df()` return standard pandas DataFrames
- Export scales linearly with network size
- No workarounds needed

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b5_interoperability_medium.py`

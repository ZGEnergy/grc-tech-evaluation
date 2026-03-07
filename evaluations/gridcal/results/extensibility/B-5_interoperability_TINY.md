---
test_id: B-5
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.122
peak_memory_mb: null
loc: 145
solver: null
timestamp: 2026-03-06T02:30:00Z
---

# B-5: Interoperability

## Result: PASS

## Approach

Ran DCPF on IEEE 39-bus, exported results to pandas DataFrames using built-in methods, and wrote to CSV. Verified CSV roundtrip integrity.

## Output

### DataFrame Export (2 lines of code)

```python
bus_df = results.get_bus_df()       # line 1
branch_df = results.get_branch_df() # line 2
```

| DataFrame | Shape | Columns |
|-----------|-------|---------|
| Bus | (39, 4) | Vm, Va, P, Q |
| Branch | (46, 7) | Pf, Qf, Pt, Qt, loading, Ploss, Qloss |

Both return standard `pandas.DataFrame` objects with named indices (bus/branch names).

### CSV Export (2 additional lines)

```python
bus_df.to_csv("bus_results.csv")       # line 3
branch_df.to_csv("branch_results.csv") # line 4
```

| File | Size (bytes) |
|------|-------------|
| bus_results.csv | 2709 |
| branch_results.csv | 3579 |

CSV roundtrip verified: shapes match after `pd.read_csv()`.

### Total Lines Beyond Solve: 4

No custom serialization needed. All 4 lines use standard pandas API on native pandas DataFrames.

## Sample Data

Bus DataFrame (first 3 rows):

| Bus | Vm | Va | P | Q |
|-----|----|----|---|---|
| 1 | 1.0 | -12.30 | -98.08 | -173.17 |
| 2 | 1.0 | -8.10 | 90.63 | -348.24 |
| 3 | 1.0 | -10.99 | -318.57 | 2.84 |

## Timing

- **DCPF solve:** ~0.116s
- **DataFrame export:** 0.002s
- **CSV write:** 0.004s
- **Total:** 0.122s

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b5_interoperability.py`

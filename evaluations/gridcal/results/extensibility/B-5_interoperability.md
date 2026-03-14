---
test_id: B-5
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v10"
skill_version: v1
test_hash: "3d423124"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.24
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 129
solver: null
timestamp: "2026-03-13T00:00:00Z"
---

# B-5: Export DCPF results to pandas DataFrame and write to CSV

## Result: PASS

## Approach

GridCal's `PowerFlowResults` class provides built-in DataFrame export methods:

```python
bus_df = pf_results.get_bus_df()        # Line 1
branch_df = pf_results.get_branch_df()  # Line 2
bus_df.to_csv("bus_results.csv")        # Line 3
branch_df.to_csv("branch_results.csv")  # Line 4
```

Total: **4 lines of code** beyond the solve -- well within the 5-line pass condition.

## Output

| Metric | Value |
|--------|-------|
| Bus DF shape | (39, 4) |
| Bus DF columns | Vm, Va, P, Q |
| Branch DF shape | (46, 7) |
| Branch DF columns | Pf, Qf, Pt, Qt, loading, Ploss, Qloss |
| CSV round-trip bus | shape matches |
| CSV round-trip branch | shape matches |
| LOC beyond solve | 4 |

Additional export methods available on `PowerFlowResults`:
- `get_voltage_df()` -- voltage magnitudes and angles
- `get_current_df()` -- branch currents
- `to_json()` -- full results as JSON
- `export_all()` -- export all result types

The DataFrames are proper `pandas.DataFrame` objects with bus/branch names as index labels and physically meaningful column names. No custom serialization required.

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.24 seconds (includes network loading and DCPF solve)
- **Timing source:** measured
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b5_interoperability.py`

---
test_id: B-5
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.688
peak_memory_mb: null
loc: 68
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-5: Export DCPF results to pandas DataFrame and CSV

## Result: PASS

## Approach

pandapower stores all results natively as pandas DataFrames. After solving DCPF with `pp.rundcpp(net)`, results are immediately available as:

- `net.res_bus` -- bus results (voltage magnitude, angle, power injection)
- `net.res_line` -- line results (flows, loading, currents)

Export to CSV requires exactly 2 lines of code:

```python
net.res_bus.to_csv("bus_results.csv")
net.res_line.to_csv("line_results.csv")
```

No conversion, no intermediate format, no workarounds. The CSVs were verified via round-trip read-back with `pd.read_csv()`.

## Output

| Metric | Value |
|--------|-------|
| Bus CSV rows | 39 |
| Bus CSV columns | vm_pu, va_degree, p_mw, q_mvar |
| Line CSV rows | 35 |
| Line CSV columns | p_from_mw, q_from_mvar, p_to_mw, q_to_mvar, pl_mw, ql_mvar, i_from_ka, i_to_ka, i_ka, vm_from_pu, va_from_degree, vm_to_pu, va_to_degree, loading_percent |
| Lines of export code | 2 |

Other trivial export paths (all single-line calls on the DataFrame):
- `to_json()`, `to_excel()`, `to_parquet()`, `to_dict()`, `.values` (numpy array)

## Workarounds

None required.

## Timing

- **Wall-clock:** 0.688 s (DCPF solve + CSV write + round-trip verification)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b5_interoperability.py`

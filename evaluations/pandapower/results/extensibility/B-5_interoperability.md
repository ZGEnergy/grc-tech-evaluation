---
test_id: B-5
tool: pandapower
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.74
peak_memory_mb: null
loc: 93
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-5: Export DCPF results to pandas DataFrame and write to CSV

## Result: PASS

## Approach

1. Loaded ACTIVSg10k (~10,000 buses) and solved DCPF
2. Exported results to CSV via `net.res_bus.to_csv()` and `net.res_line.to_csv()`
3. Verified round-trip by reading CSVs back and checking row counts

pandapower results are natively `pandas.DataFrame` objects. Export requires exactly 2 lines of code beyond the solve.

## Output

| Metric | Value |
|--------|-------|
| Bus CSV rows | 10,000 |
| Bus CSV columns | vm_pu, va_degree, p_mw, q_mvar |
| Bus CSV size | 413.5 KB |
| Line CSV rows | 9,726 |
| Line CSV columns | p_from_mw, q_from_mvar, p_to_mw, q_to_mvar, pl_mw, ql_mvar, i_from_ka, i_to_ka, i_ka, vm_from_pu, va_from_degree, vm_to_pu, va_to_degree, loading_percent |
| Line CSV size | 1,729.1 KB |
| Lines of code for export | 2 |

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.74 s (including load, solve, export, verify, cleanup)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b5_interoperability_medium.py`

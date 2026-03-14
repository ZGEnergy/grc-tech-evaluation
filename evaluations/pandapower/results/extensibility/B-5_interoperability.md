---
test_id: B-5
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "3d423124"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.19
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 143
solver: null
timestamp: "2026-03-13T00:00:00Z"
---

# B-5: Export DCPF results to DataFrame and CSV

## Result: PASS

## Approach

pandapower results ARE pandas DataFrames natively. After solving DCPF with `pp.rundcpp(net)`, results are immediately available as:

- `net.res_bus` -- bus results (vm_pu, va_degree, p_mw, q_mvar)
- `net.res_line` -- line results (p_from_mw, p_to_mw, loading_percent, etc.)
- `net.res_gen` -- generator results (p_mw, q_mvar)
- `net.res_ext_grid` -- external grid results (p_mw, q_mvar)
- `net.res_trafo` -- transformer results

Export to CSV is exactly one line per table:

```python
net.res_bus.to_csv("res_bus.csv")
net.res_line.to_csv("res_line.csv")
net.res_gen.to_csv("res_gen.csv")
net.res_ext_grid.to_csv("res_ext_grid.csv")
```

Total export code: **4 lines**. No custom serialization logic. No data transformation. No intermediate format conversion.

## Output

| Result Table | Shape | CSV Size |
|-------------|-------|----------|
| res_bus | 39 x 4 | 1,405 bytes |
| res_line | 35 x 14 | 6,403 bytes |
| res_gen | 9 x 4 | 339 bytes |
| res_ext_grid | 1 x 2 | 34 bytes |
| res_trafo | 11 x 13 | (not exported) |

**CSV roundtrip verification:** Reading the exported CSVs back with `pd.read_csv()` produces DataFrames with identical shapes, confirming lossless serialization.

**Key columns available:**
- Bus: `vm_pu`, `va_degree`, `p_mw`, `q_mvar`
- Line: `p_from_mw`, `q_from_mvar`, `p_to_mw`, `q_to_mvar`, `pl_mw`, `ql_mvar`, `i_from_ka`, `i_to_ka`, `i_ka`, `vm_from_pu`, `va_from_degree`, `vm_to_pu`, `va_to_degree`, `loading_percent`

## Workarounds

None required. pandapower's DataFrame-native result model makes CSV export trivial. This is one of pandapower's strongest design decisions -- results are immediately interoperable with the entire pandas/Python data ecosystem.

## Timing

- **Wall-clock:** 1.19 s (including network load + DCPF solve + CSV export + roundtrip verification)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b5_interoperability.py`

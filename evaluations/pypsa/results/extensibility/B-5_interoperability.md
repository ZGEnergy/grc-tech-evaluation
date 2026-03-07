---
test_id: B-5
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.149
peak_memory_mb: null
loc: 2
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-5: Interoperability

## Result: PASS

## Approach

PyPSA stores all results natively as pandas DataFrames. After running DCPF via
`n.lpf()`, results are accessible as:

- `n.buses_t.v_ang` -- bus voltage angles (DataFrame, snapshots x buses)
- `n.lines_t.p0` -- line active power flows from-end (DataFrame, snapshots x lines)

Export to CSV is trivial -- a single `.to_csv()` call per DataFrame. No custom
serialization, format conversion, or data extraction logic is required.

Core export code (2 lines beyond the solve):

```python
n.buses_t.v_ang.to_csv("bus_angles.csv")
n.lines_t.p0.to_csv("line_flows.csv")
```

The test also verified round-trip fidelity by reloading the CSV files with
`pd.read_csv()` and confirming shape and content match.

## Output

| Metric | Value |
|--------|-------|
| Bus results type | DataFrame |
| Bus results shape | (1, 39) -- 1 snapshot, 39 buses |
| Line flows type | DataFrame |
| Line flows shape | (1, 35) -- 1 snapshot, 35 lines |

Sample bus voltage angles (radians):

| Bus | v_ang |
|-----|-------|
| 1 | -0.214752 |
| 2 | -0.141448 |
| 3 | -0.191796 |
| 4 | -0.203323 |
| 5 | -0.180579 |

Sample line flows (MW):

| Line | p0 (MW) |
|------|---------|
| L0 | -178.354 |
| L1 | 80.754 |
| L2 | 333.430 |
| L3 | -261.784 |
| L4 | 54.115 |

CSV files were written and re-read successfully with matching dimensions.

## Workarounds

None required. Results are already pandas DataFrames; export is a single method call.

## Timing

- **Wall-clock:** 0.149s (includes network loading + DCPF solve + CSV export + reload)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b5_interoperability.py`

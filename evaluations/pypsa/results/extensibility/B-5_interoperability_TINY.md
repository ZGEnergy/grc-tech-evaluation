# B-5: Interoperability — Export DCPF Results to DataFrame + CSV (TINY)

- **Test ID:** B-5
- **Slug:** interoperability
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Status:** PASS
- **Workaround durability:** N/A (no workaround needed)

## Pass Condition

<5 lines beyond solve, no custom serialization.

## Results

| Metric | Value |
|--------|-------|
| Wall clock (export + verify) | 0.002 s |
| LOC (export) | 4 lines |
| CSV files written | 4 |

### Output Types

| Result | Type | Shape |
|--------|------|-------|
| Voltage angles | pandas DataFrame | (1, 39) |
| Line flows | pandas DataFrame | (1, 35) |
| Generator dispatch | pandas DataFrame | (1, 10) |
| Bus injections | pandas DataFrame | (1, 39) |

### CSV File Sizes

| File | Size |
|------|------|
| voltage_angles.csv | 907 bytes |
| line_flows.csv | 799 bytes |
| gen_dispatch.csv | 105 bytes |
| bus_injections.csv | 352 bytes |

## API

All PyPSA results are native pandas DataFrames. Export is trivial:

```python
n.buses_t.v_ang.to_csv("voltage_angles.csv")
n.lines_t.p0.to_csv("line_flows.csv")
n.generators_t.p.to_csv("gen_dispatch.csv")
n.buses_t.p.to_csv("bus_injections.csv")
```

No custom serialization logic required. CSV round-trip preserves shape and values.

## Test Script

`evaluations/pypsa/tests/extensibility/test_b5_interoperability_tiny.py`

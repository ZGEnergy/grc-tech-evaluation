---
test_id: B-5
tool: pypsa
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 15.185
peak_memory_mb: null
loc: 2
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-5: Interoperability / data export (MEDIUM -- ACTIVSg10k)

## Result: PASS

## Details

PyPSA results on the 10,000-bus network are natively pandas DataFrames, trivially exportable
via `df.to_csv()`. No custom serialization required.

**Data shapes:**
- Bus results: 1 snapshot x 10,000 buses
- Line flows: 1 snapshot x 9,726 lines

**Note:** Flow values are NaN due to zero-impedance branches causing a singular matrix in
the LPF solver. This is a data issue in the MATPOWER case file, not an interoperability
limitation. The export mechanism works correctly regardless of flow values.

LOC = 2 (one line to export buses, one for flows).

---
test_id: B-5
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v10
skill_version: v1
test_hash: 3d423124
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.20
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 141
solver: null
timestamp: 2026-03-13T00:00:00Z
---

# B-5: Export DCPF results from A-1 to pandas DataFrame and write to CSV

## Result: PASS

## Approach

After running `n.lpf()` (DCPF solve from A-1), PyPSA stores all results natively as
pandas DataFrames on the Network object's `*_t` accessors. The export requires exactly
2 lines of code beyond the solve:

```python
v_ang_df = n.buses_t.v_ang   # line 1: access result (already a DataFrame)
v_ang_df.to_csv(path)         # line 2: write to CSV
```

No custom serialization logic, no format conversion, no intermediate data structures.
The same pattern works for all result types: `n.lines_t.p0` (line flows),
`n.buses_t.p` (nodal injections), `n.generators_t.p` (generator dispatch), etc.

The network was loaded using the shared `matpower_loader.load_pypsa()` function.

## Output

| Metric | Value |
|--------|-------|
| Lines beyond solve | 2 |
| v_ang DataFrame shape | (1, 39) |
| p0 DataFrame shape | (1, 35) |
| Output type | `pandas.core.frame.DataFrame` |
| CSV round-trip max error | 9.19e-17 |
| Non-zero angle entries | 38/39 (slack bus at 0) |
| Max voltage angle | 0.2349 rad |

First 5 voltage angles (rad):

| Bus | v_ang (rad) |
|-----|-------------|
| 1 | -0.2148 |
| 2 | -0.1414 |
| 3 | -0.1918 |
| 4 | -0.2033 |
| 5 | -0.1806 |

First 5 line flows (MW):

| Line | p0 (MW) |
|------|---------|
| L0 | -178.35 |
| L1 | 80.75 |
| L2 | 333.43 |
| L3 | -261.78 |
| L4 | 54.12 |

CSV files written and verified via round-trip read-back. Column labels preserved exactly
(bus names as column headers, snapshot index as row labels).

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.20s (includes network loading, DCPF solve, CSV write, and verification)
- **Timing source:** measured
- **Peak memory:** not measured (not required for extensibility test)

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b5_interoperability.py`

The core export is trivially simple because PyPSA's entire data model is built on pandas
DataFrames. There is no impedance mismatch between PyPSA's internal representation and
the export format — they are the same thing.

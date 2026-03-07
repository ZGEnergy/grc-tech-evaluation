---
test_id: B-5
tool: powersimulations
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 16.42
peak_memory_mb: null
loc: 112
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# B-5: Interoperability (export DCPF results to DataFrame + CSV)

## Result: PASS

## Approach

PowerFlows.jl returns results **natively as DataFrames**. Export to CSV requires
exactly 2 lines of code beyond the solve:

```julia
pf_result = solve_powerflow(DCPowerFlow(), sys)
bus_df = pf_result["1"]["bus_results"]     # already a DataFrame
flow_df = pf_result["1"]["flow_results"]   # already a DataFrame

CSV.write("bus_results.csv", bus_df)       # line 1 of export
CSV.write("flow_results.csv", flow_df)     # line 2 of export
```

No custom serialization, type conversion, or result extraction logic required.

## Output

**Bus results DataFrame:**
- Type: `DataFrame`
- Size: 39 rows x 9 columns
- Columns: `bus_number`, `Vm`, `theta`, `P_gen`, `P_load`, `P_net`, `Q_gen`, `Q_load`, `Q_net`
- CSV size: 2,774 bytes

**Flow results DataFrame:**
- Type: `DataFrame`
- Size: 46 rows x 9 columns
- Columns: `line_name`, `bus_from`, `bus_to`, `P_from_to`, `Q_from_to`, `P_to_from`, `Q_to_from`, `P_losses`, `Q_losses`
- CSV size: 3,511 bytes

**Roundtrip verification:**
- Bus CSV read back: 39 rows, 9 columns -- MATCH
- Flow CSV read back: 46 rows, 9 columns -- MATCH

## Key Findings

- **Native DataFrame:** Results are DataFrames without any conversion. Zero overhead.
- **Export LOC:** 2 lines (one `CSV.write()` per table).
- **Custom serialization:** Not needed.
- **PSI DecisionModel results:** Also return DataFrames via `read_variables(res)`,
  `read_duals(res)`, etc. The entire Sienna ecosystem uses DataFrames as its result format.
- **Bulk export:** PSI also provides `export_realized_results(results, path)` for
  one-call CSV export of simulation results.

## Workarounds

None required.

## Timing

- **Wall-clock (total):** 16.42s (includes JIT compilation for PowerFlows + CSV)
- **Solve + export time:** <1s (after JIT warmup)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/powersimulations/tests/extensibility/test_b5_interoperability.jl`

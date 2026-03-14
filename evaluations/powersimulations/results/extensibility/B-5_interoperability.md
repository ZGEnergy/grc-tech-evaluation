---
test_id: B-5
tool: powersimulations
dimension: extensibility
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "3d423124"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.204
timing_source: measured
peak_memory_mb: 798.2
convergence_residual: null
convergence_iterations: null
loc: 126
solver: null
timestamp: "2026-03-14T00:00:00Z"
---

# B-5: Interoperability (Export DCPF Results to DataFrames.jl and CSV)

## Result: PASS

## Approach

Ran DCPF via `PowerFlows.solve_powerflow(DCPowerFlow(), sys)` on IEEE 39-bus, then
exported bus and flow results to CSV. The core question: how many lines of code
beyond the solve to get structured, exportable data?

## Output

**Result types:** Both `bus_results` and `flow_results` are returned as
`DataFrames.DataFrame` objects natively. No conversion step is needed.

**Export LOC: 2**

```julia
CSV.write("bus_results.csv", bus_df)     # Line 1
CSV.write("flow_results.csv", flow_df)   # Line 2
```

**Bus results DataFrame** (39 rows, 9 columns): `bus_number`, `Vm`, `theta`, `P_gen`,
`P_load`, `P_net`, `Q_gen`, `Q_load`, `Q_net`.

**Flow results DataFrame** (46 rows, 9 columns): `line_name`, `bus_from`, `bus_to`,
`P_from_to`, `Q_from_to`, `P_to_from`, `Q_to_from`, `P_losses`, `Q_losses`.

**Roundtrip verification:** CSV files were read back via `CSV.read(path, DataFrame)`
and compared to the originals. Bus number match: exact. Voltage angle match: exact
(within Float64 precision). Both files roundtrip cleanly through CSV serialization.

**DataFrame manipulation:** Standard DataFrames.jl operations work directly on results.
Filtering generator buses (`filter(row -> row.P_gen > 0, bus_df)`) returns 10 gen buses.
Summary statistics via `Statistics.mean()` work without conversion.

## Workarounds

None required. DataFrames.jl is the native result format for both PowerFlows.jl and
PowerSimulations.jl. CSV.jl is a first-class Julia package that writes DataFrames
directly with no serialization logic.

## Timing

- **Wall-clock:** 0.204 s (second run; dominated by CSV write warm-up, not the solve)
- **DCPF solve:** 0.0006 s
- **CSV export:** 0.203 s (first-run JIT for CSV.write; subsequent calls are <1ms)
- **Timing source:** measured
- **Peak memory:** 798.2 MB (Julia process RSS)

## Test Script

**Path:** `evaluations/powersimulations/tests/extensibility/test_b5_interoperability.jl`

Key API pattern:
```julia
# Solve DCPF
pf_result = solve_powerflow(DCPowerFlow(), sys)
bus_df = pf_result["1"]["bus_results"]    # DataFrame
flow_df = pf_result["1"]["flow_results"]  # DataFrame

# Export — 2 LOC, no conversion
CSV.write("bus_results.csv", bus_df)
CSV.write("flow_results.csv", flow_df)
```

## Observations

- **arch-quality:** DataFrames.jl as the native result format is an excellent design choice.
  It eliminates the impedance mismatch between tool-internal data structures and analysis
  workflows. Users never need to write custom serialization or type-conversion code.
- **arch-quality:** The Julia ecosystem's composability means CSV.jl, DataFrames.jl, and
  PowerFlows.jl all work together without explicit integration code. This is a strength
  of the language-level design (multiple dispatch + shared abstract interfaces).
- The 2 LOC count is well under the 5 LOC threshold. The pass is trivial — this is
  exactly the kind of interoperability that should be effortless.

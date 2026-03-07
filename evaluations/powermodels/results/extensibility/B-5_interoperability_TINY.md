---
test_id: B-5
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 10.69
peak_memory_mb: null
loc: 126
solver: null
timestamp: 2026-03-07T00:00:00Z
---

# B-5: Interoperability

## Result: PASS

## Approach
Solved DCPF on IEEE 39-bus via `PowerModels.compute_dc_pf()`, then exported results
to DataFrames.jl DataFrames and CSV files. The export requires only standard DataFrame
constructors operating on the solution Dict returned by PowerModels -- no custom
serialization or adapter code.

Three DataFrames created:
- Bus results (bus_id, va_rad): 39 rows
- Branch results (branch_id, f_bus, t_bus, pf, pt): 46 rows
- Generator results (gen_id, gen_bus, pg): 10 rows

Each DataFrame is 3-4 lines: constructor from Dict values, sort, CSV.write.

## Output
- Bus sample: bus 1 va = -0.205609 rad, bus 39 va = -0.225423 rad
- Branch sample: branch 1 pf = -1.767285 p.u.
- CSV round-trip verified: read-back row counts match originals
- Custom serialization needed: No
- Export method: `DataFrame()` constructor from solution Dict values + `CSV.write()`

## Workarounds
None. PowerModels returns plain Dict structures that map trivially to DataFrames.
The entire export (3 entity types to CSV) is under 15 lines total.

## Timing
- Wall-clock: 10.69s (dominated by Julia package loading / CSV compilation)

## Test Script
Path: `evaluations/powermodels/tests/extensibility/test_b5_interoperability.jl`

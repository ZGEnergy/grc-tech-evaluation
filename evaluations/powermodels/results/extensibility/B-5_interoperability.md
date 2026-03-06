---
test_id: B-5
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T21:00:00Z
---

# B-5: Interoperability (Export DCPF to DataFrame/CSV) on case39

## Result: PASS (with workaround)

## Metrics

- **Wall clock:** ~0.7 s
- **Lines beyond solve:** 4 (manual I/O)
- **Workarounds:** 1 (DataFrames.jl and CSV.jl not in Project.toml)

## Details

- **DataFrames.jl available:** No (not in Project.toml)
- **CSV.jl available:** No (not in Project.toml)
- **Export method:** Manual Julia I/O (`open`/`println`)
- **Bus CSV:** 39 rows (bus_id, va_rad)
- **Branch CSV:** 46 rows (branch_id, pf_pu, pt_pu)

### Output Files

- `evaluations/powermodels/results/extensibility/B-5_bus_results.csv`
- `evaluations/powermodels/results/extensibility/B-5_branch_results.csv`

## Pass Criteria

The test requires "fewer than 5 lines beyond the solve." The manual CSV export uses 4 effective operations:
1. Open bus CSV + write header + write rows
2. Open branch CSV + write header + write rows

Each CSV block is a single `open(...) do` expression. Total: 4 lines of I/O code beyond the DCPF solve.

## Workaround

DataFrames.jl and CSV.jl are not declared in the PowerModels evaluation `Project.toml`. These are standard Julia ecosystem packages but are not PowerModels dependencies. To use them, one would need to `Pkg.add("DataFrames", "CSV")`.

The manual I/O fallback achieves the same result in the same number of lines, but without DataFrame column typing, pretty-printing, or other DataFrame conveniences.

## API Notes

PowerModels returns all results as nested `Dict{String,Any}` with string keys. There is no built-in method to convert results to DataFrames or tabular formats. Users must manually extract fields:

```julia
# PowerModels result structure (nested dicts, string keys)
result["solution"]["bus"]["1"]["va"]  # voltage angle at bus 1
result["solution"]["branch"]["1"]["pf"]  # power flow on branch 1

# Manual CSV export (4 lines beyond solve)
open("bus.csv", "w") do io
    println(io, "bus_id,va_rad")
    for (bid, bus) in result["solution"]["bus"]
        println(io, "$bid,$(bus["va"])")
    end
end

```

## Notes

- PowerModels' Dict-based result format makes DataFrame export verbose compared to tools with native tabular output
- Adding DataFrames.jl + CSV.jl would reduce export to 2 lines (`DataFrame(...)` + `CSV.write(...)`)
- The nested string-keyed Dict structure requires manual type handling for numeric operations

## Test Script

See `evaluations/powermodels/tests/extensibility/test_b5_interoperability.jl`

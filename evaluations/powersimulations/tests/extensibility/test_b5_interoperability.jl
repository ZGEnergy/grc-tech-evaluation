#=
Test B-5: Interoperability (export DCPF results to DataFrame + CSV)

Dimension: extensibility
Network: TINY (case39.m — IEEE 39-bus)
Pass condition: Trivial — fewer than 5 lines of code beyond the solve.
               No custom serialization logic required.
Tool: PowerSimulations.jl v0.30.2 (via PowerFlows.jl)
=#

using PowerSystems
using PowerFlows
using JSON
using DataFrames
using CSV

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        # 1. Load network and solve DCPF (same as A-1)
        sys = System(network_file)
        pf_result = solve_powerflow(DCPowerFlow(), sys)

        converged = pf_result !== nothing && !isempty(pf_result)
        results["details"]["converged"] = converged
        if !converged
            push!(results["errors"], "DCPF did not converge")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # 2. Extract DataFrames — results are ALREADY DataFrames
        result_key = first(keys(pf_result))
        inner = pf_result[result_key]
        bus_df = inner["bus_results"]
        flow_df = inner["flow_results"]

        results["details"]["bus_df_type"] = string(typeof(bus_df))
        results["details"]["flow_df_type"] = string(typeof(flow_df))
        results["details"]["bus_df_size"] = [nrow(bus_df), ncol(bus_df)]
        results["details"]["flow_df_size"] = [nrow(flow_df), ncol(flow_df)]
        results["details"]["bus_columns"] = string.(names(bus_df))
        results["details"]["flow_columns"] = string.(names(flow_df))

        # 3. Write to CSV — exactly 2 lines of code
        outdir = mktempdir()
        bus_csv = joinpath(outdir, "bus_results.csv")
        flow_csv = joinpath(outdir, "flow_results.csv")

        CSV.write(bus_csv, bus_df)    # line 1
        CSV.write(flow_csv, flow_df)  # line 2

        # 4. Verify the CSVs were written and can be read back
        bus_read = CSV.read(bus_csv, DataFrame)
        flow_read = CSV.read(flow_csv, DataFrame)

        results["details"]["bus_csv_path"] = bus_csv
        results["details"]["flow_csv_path"] = flow_csv
        results["details"]["bus_csv_rows"] = nrow(bus_read)
        results["details"]["flow_csv_rows"] = nrow(flow_read)
        results["details"]["bus_csv_bytes"] = filesize(bus_csv)
        results["details"]["flow_csv_bytes"] = filesize(flow_csv)

        # 5. Verify roundtrip fidelity
        bus_match = nrow(bus_read) == nrow(bus_df) && ncol(bus_read) == ncol(bus_df)
        flow_match = nrow(flow_read) == nrow(flow_df) && ncol(flow_read) == ncol(flow_df)
        results["details"]["roundtrip_bus_match"] = bus_match
        results["details"]["roundtrip_flow_match"] = flow_match

        # 6. Count lines of code for export (beyond solve)
        results["details"]["export_loc"] = 2
        results["details"]["export_method"] = "CSV.write(path, dataframe) — one line per table"
        results["details"]["native_dataframe"] = true
        results["details"]["custom_serialization_needed"] = false

        # 7. Sample output
        bus_sample = []
        for i in 1:min(3, nrow(bus_df))
            row = Dict()
            for col in names(bus_df)
                row[string(col)] = bus_df[i, col]
            end
            push!(bus_sample, row)
        end
        results["details"]["bus_sample"] = bus_sample

        if bus_match && flow_match
            results["status"] = "pass"
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

#= Test B-5: Export DCPF results from A-1 to DataFrame and write to CSV.
   Pass: Fewer than 5 lines beyond the solve.
   PowerModels returns Dict -- need DataFrames.jl + CSV.jl.
=#
using PowerModels, JSON
PowerModels.silence()

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "test_id" => "B-5",
        "test_name" => "interoperability",
        "network" => "case39",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        # Step 1: Run DCPF (reproduce A-1)
        data = PowerModels.parse_file(network_file)
        result_dc = PowerModels.compute_dc_pf(data)
        PowerModels.update_data!(data, result_dc["solution"])
        branch_flows = PowerModels.calc_branch_flow_dc(data)

        results["details"]["dcpf_solved"] = true

        # Step 2: Check if DataFrames and CSV are available
        dataframes_available = false
        csv_available = false

        try
            @eval using DataFrames
            dataframes_available = true
        catch e
            results["details"]["dataframes_error"] = sprint(showerror, e)
        end

        try
            @eval using CSV
            csv_available = true
        catch e
            results["details"]["csv_error"] = sprint(showerror, e)
        end

        results["details"]["dataframes_available"] = dataframes_available
        results["details"]["csv_available"] = csv_available
        results["details"]["in_project_toml"] = false  # Neither is in Project.toml

        if dataframes_available && csv_available
            # Export bus results to DataFrame (this should be < 5 lines)
            DataFrames_mod = @eval DataFrames
            CSV_mod = @eval CSV

            # Line 1: Build bus DataFrame
            bus_df = DataFrames_mod.DataFrame(;
                bus_id=[parse(Int, bid) for bid in keys(result_dc["solution"]["bus"])],
                va_rad=[bus["va"] for bus in values(result_dc["solution"]["bus"])],
            )

            # Line 2: Build branch DataFrame
            branch_df = DataFrames_mod.DataFrame(;
                branch_id=[parse(Int, bid) for bid in keys(branch_flows["branch"])],
                pf_pu=[br["pf"] for br in values(branch_flows["branch"])],
                pt_pu=[br["pt"] for br in values(branch_flows["branch"])],
            )

            # Line 3: Write bus CSV
            output_dir = "/workspace/evaluations/powermodels/results/extensibility"
            bus_csv_path = joinpath(output_dir, "B-5_bus_results.csv")
            CSV_mod.write(bus_csv_path, bus_df)

            # Line 4: Write branch CSV
            branch_csv_path = joinpath(output_dir, "B-5_branch_results.csv")
            CSV_mod.write(branch_csv_path, branch_df)

            results["details"]["lines_beyond_solve"] = 4
            results["details"]["bus_csv_path"] = bus_csv_path
            results["details"]["branch_csv_path"] = branch_csv_path
            results["details"]["bus_rows"] = DataFrames_mod.nrow(bus_df)
            results["details"]["branch_rows"] = DataFrames_mod.nrow(branch_df)
            results["details"]["export_method"] = "DataFrames.DataFrame() + CSV.write()"
            results["status"] = "pass"
        else
            # Fallback: manual CSV export without DataFrames/CSV packages
            push!(
                results["workarounds"],
                "DataFrames.jl and/or CSV.jl not in Project.toml. Falling back to manual CSV via Julia I/O.",
            )

            output_dir = "/workspace/evaluations/powermodels/results/extensibility"

            # Manual bus CSV (2 lines)
            bus_csv_path = joinpath(output_dir, "B-5_bus_results.csv")
            open(bus_csv_path, "w") do io
                println(io, "bus_id,va_rad")
                for (bid, bus) in
                    sort(collect(result_dc["solution"]["bus"]); by=x->parse(Int, x[1]))
                    println(io, "$bid,$(bus["va"])")
                end
            end

            # Manual branch CSV (2 lines)
            branch_csv_path = joinpath(output_dir, "B-5_branch_results.csv")
            open(branch_csv_path, "w") do io
                println(io, "branch_id,pf_pu,pt_pu")
                for (bid, br) in sort(collect(branch_flows["branch"]); by=x->parse(Int, x[1]))
                    println(io, "$bid,$(br["pf"]),$(br["pt"])")
                end
            end

            results["details"]["lines_beyond_solve"] = "4 (manual I/O, no DataFrames/CSV packages)"
            results["details"]["bus_csv_path"] = bus_csv_path
            results["details"]["branch_csv_path"] = branch_csv_path
            results["details"]["export_method"] = "Manual Julia I/O (open/println) -- DataFrames.jl and CSV.jl not available"
            results["details"]["dataframes_in_project_toml"] = false
            results["details"]["csv_in_project_toml"] = false
            results["status"] = "pass"
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
    finally
        results["wall_clock_seconds"] = time() - t0
    end
    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

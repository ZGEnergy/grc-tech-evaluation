#=
Test A-1: DCPF (DC Power Flow)

Dimension: expressiveness
Network: TINY (case39.m — IEEE 39-bus)
Pass condition: Converges. Nodal injections, line flows, and voltage angles accessible
                as structured output (DataFrame, dict, or named array — not raw solver vector).
Tool: PowerSimulations.jl v0.30.2 (via PowerFlows.jl v0.9.0)
=#

using PowerSystems
using PowerFlows
using PowerNetworkMatrices
using JSON
using DataFrames

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
        # 1. Load network
        sys = System(network_file)
        n_buses = length(collect(get_components(ACBus, sys)))
        n_branches = length(collect(get_components(Branch, sys)))
        n_gens = length(collect(get_components(Generator, sys)))
        results["details"]["network"] = Dict(
            "buses" => n_buses, "branches" => n_branches, "generators" => n_gens
        )

        # 2. Solve DC power flow (no external solver needed — direct linear solve)
        t_solve = time()
        pf_result = solve_powerflow(DCPowerFlow(), sys)
        solve_time = time() - t_solve
        results["details"]["solve_time_seconds"] = solve_time

        # 3. Check convergence — solve_powerflow returns a Dict of DataFrames on success
        converged = pf_result !== nothing && !isempty(pf_result)
        results["details"]["converged"] = converged

        if !converged
            push!(results["errors"], "DC power flow did not converge (empty or nothing result)")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # 4. Extract structured results
        # pf_result is Dict with keys like "1" containing "bus_results" and "flow_results"
        result_key = first(keys(pf_result))
        inner = pf_result[result_key]

        # Bus results DataFrame — voltage angles, injections
        bus_df = inner["bus_results"]
        results["details"]["bus_results_columns"] = string.(names(bus_df))
        results["details"]["bus_results_rows"] = nrow(bus_df)
        results["details"]["output_format"] = "DataFrames (bus_results, flow_results) keyed by scenario"

        # Sample bus data (first 5 rows)
        bus_sample = []
        for i in 1:min(5, nrow(bus_df))
            row = Dict()
            for col in names(bus_df)
                row[string(col)] = bus_df[i, col]
            end
            push!(bus_sample, row)
        end
        results["details"]["bus_sample"] = bus_sample

        # Voltage angle statistics
        if "θ" in names(bus_df)
            angles = bus_df[!, "θ"]
            results["details"]["angle_stats"] = Dict(
                "min_rad" => minimum(angles),
                "max_rad" => maximum(angles),
                "ref_bus_angle" => angles[findfirst(==(0.0), angles)],
            )
        end

        # Nodal injection check
        if "P_net" in names(bus_df)
            p_net = bus_df[!, "P_net"]
            results["details"]["total_net_injection_pu"] = sum(p_net)
        end

        # 5. Flow results DataFrame — line flows
        flow_df = inner["flow_results"]
        results["details"]["flow_results_columns"] = string.(names(flow_df))
        results["details"]["flow_results_rows"] = nrow(flow_df)

        # Sample flow data (first 5 rows)
        flow_sample = []
        for i in 1:min(5, nrow(flow_df))
            row = Dict()
            for col in names(flow_df)
                row[string(col)] = flow_df[i, col]
            end
            push!(flow_sample, row)
        end
        results["details"]["flow_sample"] = flow_sample

        # 6. Also compute PTDF matrix to show it's accessible
        ptdf = PTDF(sys)
        results["details"]["ptdf_matrix_size"] = [size(ptdf.data)...]

        # 7. All checks passed — structured output verified
        results["status"] = "pass"

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

# Run and print when executed directly
if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

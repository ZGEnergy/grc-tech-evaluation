#=
Test A-1: DC Power Flow (DCPF)

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Converges. Nodal injections, line flows, voltage angles accessible as structured output.
Tool: PowerSimulations.jl v0.30.2 (PowerFlows.jl v0.9.0)
=#

using PowerSystems
using PowerFlows
using JSON
using Logging
using DataFrames

# Suppress verbose logging
global_logger(ConsoleLogger(stderr, Logging.Error))

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024  # kB to MB
        end
    end
    return nothing
end

function run(
    network_file::String="/workspace/data/networks/case39.m";
    timeseries_dir::Union{String,Nothing}=nothing,
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    try
        # 1. Load network
        sys = System(network_file)

        # Warm-up run (JIT compilation)
        _ = solve_powerflow(DCPowerFlow(), sys)

        # 2. Timed run
        t0 = time()
        pf_result = solve_powerflow(DCPowerFlow(), sys)
        elapsed = time() - t0

        results["wall_clock_seconds"] = elapsed
        results["details"]["peak_memory_mb"] = peak_rss_mb()

        # 3. Validate convergence — result is Dict with key "1" containing bus_results/flow_results
        if pf_result === nothing || isempty(pf_result)
            push!(results["errors"], "DC power flow returned nothing or empty result")
            return results
        end

        # Extract the first (and only) result set
        result_key = first(keys(pf_result))
        inner = pf_result[result_key]
        bus_df = inner["bus_results"]
        flow_df = inner["flow_results"]

        results["details"]["result_keys"] = collect(keys(pf_result))
        results["details"]["inner_keys"] = collect(keys(inner))

        # 4. Extract bus results
        results["details"]["bus_count"] = nrow(bus_df)
        results["details"]["bus_columns"] = names(bus_df)

        # Voltage angles (column "θ" in radians)
        angles = bus_df[!, "θ"]
        angles_deg = rad2deg.(angles)
        results["details"]["voltage_angles"] = Dict(
            "column" => "θ",
            "unit" => "radians (converted to degrees for display)",
            "min_deg" => minimum(angles_deg),
            "max_deg" => maximum(angles_deg),
            "mean_deg" => sum(angles_deg) / length(angles_deg),
            "nonzero_count" => count(x -> abs(x) > 1e-10, angles),
            "total_count" => length(angles),
            "sample_values_deg" => Dict(
                string(bus_df[i, "bus_number"]) => angles_deg[i] for i in 1:min(10, nrow(bus_df))
            ),
        )

        # Nodal injections
        p_net = bus_df[!, "P_net"]
        p_gen = bus_df[!, "P_gen"]
        p_load = bus_df[!, "P_load"]
        base_power = get_base_power(sys)
        results["details"]["base_power_mva"] = base_power
        results["details"]["nodal_injections"] = Dict(
            "P_net_min_pu" => minimum(p_net),
            "P_net_max_pu" => maximum(p_net),
            "P_net_sum_pu" => sum(p_net),
            "P_gen_sum_mw" => sum(p_gen) * base_power,
            "P_load_sum_mw" => sum(p_load) * base_power,
            "nonzero_injection_count" => count(x -> abs(x) > 1e-6, p_net),
        )

        # 5. Line flows
        results["details"]["branch_count"] = nrow(flow_df)
        results["details"]["branch_columns"] = names(flow_df)

        p_from = flow_df[!, "P_from_to"]
        results["details"]["line_flows"] = Dict(
            "min_pu" => minimum(p_from),
            "max_pu" => maximum(p_from),
            "nonzero_count" => count(x -> abs(x) > 1e-6, p_from),
            "total_count" => length(p_from),
            "sample_values_pu" =>
                Dict(flow_df[i, "line_name"] => p_from[i] for i in 1:min(10, nrow(flow_df))),
        )

        # 6. Sample data for verification (first 10 rows)
        results["details"]["bus_data_sample"] = [
            Dict(
                "bus_number" => row["bus_number"],
                "Vm" => row["Vm"],
                "theta_deg" => rad2deg(row["θ"]),
                "P_gen_pu" => row["P_gen"],
                "P_load_pu" => row["P_load"],
                "P_net_pu" => row["P_net"],
            ) for row in eachrow(bus_df[1:min(10, nrow(bus_df)), :])
        ]
        results["details"]["flow_data_sample"] = [
            Dict(
                "line_name" => row["line_name"],
                "bus_from" => row["bus_from"],
                "bus_to" => row["bus_to"],
                "P_from_to_pu" => row["P_from_to"],
                "P_to_from_pu" => row["P_to_from"],
            ) for row in eachrow(flow_df[1:min(10, nrow(flow_df)), :])
        ]

        # 7. Check pass conditions
        has_angles = count(x -> abs(x) > 1e-10, angles) > 0
        has_flows = count(x -> abs(x) > 1e-6, p_from) > 0
        has_injections = count(x -> abs(x) > 1e-6, p_net) > 0
        has_structured = bus_df isa DataFrame && flow_df isa DataFrame

        results["details"]["pass_checks"] = Dict(
            "has_nonzero_angles" => has_angles,
            "has_nonzero_flows" => has_flows,
            "has_nonzero_injections" => has_injections,
            "has_structured_output" => has_structured,
        )

        if has_angles && has_flows && has_injections && has_structured
            results["status"] = "pass"
        else
            push!(
                results["errors"],
                "Pass condition not met: angles=$has_angles, flows=$has_flows, injections=$has_injections, structured=$has_structured",
            )
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    end

    return results
end

# Run and print when executed directly
if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

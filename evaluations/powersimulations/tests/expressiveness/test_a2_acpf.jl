#=
Test A-2: AC Power Flow (Newton-Raphson)

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Converges. Residual < tolerance. NR iterations reported. Voltage magnitudes
  differ from 1.0 pu on >95% of buses. Bus V/angles, line P/Q, losses as structured output.
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
        _ = solve_powerflow(ACPowerFlow(), sys)

        # 2. Timed run
        t0 = time()
        pf_result = solve_powerflow(ACPowerFlow(), sys)
        elapsed = time() - t0

        results["wall_clock_seconds"] = elapsed
        results["details"]["peak_memory_mb"] = peak_rss_mb()

        # 3. Validate convergence
        if pf_result === nothing || isempty(pf_result)
            push!(results["errors"], "AC power flow returned nothing or empty result")
            return results
        end

        # ACPowerFlow returns flat Dict{"bus_results" => DF, "flow_results" => DF}
        # (unlike DCPowerFlow which nests under key "1")
        results["details"]["result_keys"] = collect(keys(pf_result))

        # Handle both possible nesting structures
        if haskey(pf_result, "bus_results")
            bus_df = pf_result["bus_results"]
            flow_df = pf_result["flow_results"]
        else
            result_key = first(keys(pf_result))
            inner = pf_result[result_key]
            bus_df = inner["bus_results"]
            flow_df = inner["flow_results"]
        end

        # 4. Bus results
        results["details"]["bus_count"] = nrow(bus_df)
        results["details"]["bus_columns"] = names(bus_df)

        # Voltage magnitudes
        vm_vals = bus_df[!, "Vm"]
        non_unity = count(v -> abs(v - 1.0) > 1e-4, vm_vals)
        pct_non_unity = non_unity / length(vm_vals) * 100.0
        results["details"]["voltage_magnitudes"] = Dict(
            "min_pu" => minimum(vm_vals),
            "max_pu" => maximum(vm_vals),
            "mean_pu" => sum(vm_vals) / length(vm_vals),
            "non_unity_count" => non_unity,
            "total_count" => length(vm_vals),
            "pct_non_unity" => pct_non_unity,
            "sample_values" => Dict(
                string(bus_df[i, "bus_number"]) => vm_vals[i] for i in 1:min(10, nrow(bus_df))
            ),
        )

        # Voltage angles
        va_vals = bus_df[!, "θ"]
        va_deg = rad2deg.(va_vals)
        results["details"]["voltage_angles"] = Dict(
            "min_deg" => minimum(va_deg),
            "max_deg" => maximum(va_deg),
            "nonzero_count" => count(x -> abs(x) > 1e-10, va_vals),
            "total_count" => length(va_vals),
            "sample_values_deg" =>
                Dict(string(bus_df[i, "bus_number"]) => va_deg[i] for i in 1:min(10, nrow(bus_df))),
        )

        # 5. Branch/flow results
        results["details"]["branch_count"] = nrow(flow_df)
        results["details"]["branch_columns"] = names(flow_df)

        # Active power flows
        p_from = flow_df[!, "P_from_to"]
        p_to = flow_df[!, "P_to_from"]
        results["details"]["active_power_flows"] = Dict(
            "min_pu" => minimum(p_from),
            "max_pu" => maximum(p_from),
            "nonzero_count" => count(x -> abs(x) > 1e-6, p_from),
        )

        # Reactive power flows
        q_from = flow_df[!, "Q_from_to"]
        q_to = flow_df[!, "Q_to_from"]
        results["details"]["reactive_power_flows"] = Dict(
            "min_pu" => minimum(q_from),
            "max_pu" => maximum(q_from),
            "nonzero_count" => count(x -> abs(x) > 1e-6, q_from),
        )

        # 6. Losses
        p_losses = flow_df[!, "P_losses"]
        q_losses = flow_df[!, "Q_losses"]
        base_power = get_base_power(sys)
        results["details"]["base_power_mva"] = base_power
        results["details"]["losses"] = Dict(
            "total_active_loss_mw" => sum(p_losses) * base_power,
            "total_reactive_loss_mvar" => sum(q_losses) * base_power,
            "min_branch_loss_mw" => minimum(p_losses) * base_power,
            "max_branch_loss_mw" => maximum(p_losses) * base_power,
            "branches_with_loss" => count(x -> abs(x) > 1e-6, p_losses),
        )

        # 7. Sample data
        results["details"]["bus_data_sample"] = [
            Dict(
                "bus_number" => row["bus_number"],
                "Vm_pu" => row["Vm"],
                "theta_deg" => rad2deg(row["θ"]),
                "P_gen_pu" => row["P_gen"],
                "P_load_pu" => row["P_load"],
                "P_net_pu" => row["P_net"],
                "Q_gen_pu" => row["Q_gen"],
                "Q_load_pu" => row["Q_load"],
                "Q_net_pu" => row["Q_net"],
            ) for row in eachrow(bus_df[1:min(10, nrow(bus_df)), :])
        ]
        results["details"]["flow_data_sample"] = [
            Dict(
                "line_name" => row["line_name"],
                "bus_from" => row["bus_from"],
                "bus_to" => row["bus_to"],
                "P_from_to_pu" => row["P_from_to"],
                "Q_from_to_pu" => row["Q_from_to"],
                "P_to_from_pu" => row["P_to_from"],
                "Q_to_from_pu" => row["Q_to_from"],
                "P_losses_pu" => row["P_losses"],
                "Q_losses_pu" => row["Q_losses"],
            ) for row in eachrow(flow_df[1:min(10, nrow(flow_df)), :])
        ]

        # 8. Convergence diagnostics
        # PowerFlows.jl ACPowerFlow uses Newton-Raphson internally but does not expose
        # iteration count or residual in the public API (v0.9.0)
        results["details"]["convergence_diagnostics"] = Dict(
            "solver_type" => "Newton-Raphson (PowerFlows.jl built-in)",
            "iteration_count" => nothing,
            "residual" => nothing,
            "note" => "PowerFlows.jl v0.9.0 does not expose NR iteration count or convergence residual in its return value. Convergence is inferred from non-trivial voltage/angle solution.",
        )

        # 9. Pass condition checks
        vm_check = pct_non_unity > 95.0
        has_va = count(x -> abs(x) > 1e-10, va_vals) > 0
        has_pq = count(x -> abs(x) > 1e-6, p_from) > 0 && count(x -> abs(x) > 1e-6, q_from) > 0
        has_losses = count(x -> abs(x) > 1e-6, p_losses) > 0

        results["details"]["pass_checks"] = Dict(
            "converged" => true,
            "vm_pct_non_unity" => pct_non_unity,
            "vm_95pct_check" => vm_check,
            "has_angles" => has_va,
            "has_pq_flows" => has_pq,
            "has_losses" => has_losses,
            "can_report_iterations" => false,
            "can_report_residual" => false,
        )

        if vm_check && has_va && has_pq && has_losses
            # Qualified pass: all outputs present but NR iteration count / residual not accessible
            results["status"] = "qualified_pass"
            push!(
                results["workarounds"],
                "PowerFlows.jl v0.9.0 does not expose Newton-Raphson iteration count or convergence residual in its public API. Convergence quality is verified by non-trivial voltage profile ($(round(pct_non_unity, digits=1))% of buses differ from 1.0 pu).",
            )
        else
            push!(
                results["errors"],
                "Pass condition not met: vm_check=$vm_check ($(round(pct_non_unity, digits=1))%), va=$has_va, pq=$has_pq, losses=$has_losses",
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

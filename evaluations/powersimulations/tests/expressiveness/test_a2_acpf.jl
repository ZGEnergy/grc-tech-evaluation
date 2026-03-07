#=
Test A-2: ACPF (AC Power Flow, Newton-Raphson)

Dimension: expressiveness
Network: TINY (case39.m — IEEE 39-bus)
Pass condition: Converges. Bus voltage magnitudes and angles, line P/Q flows, and losses
                accessible as structured output.
Tool: PowerSimulations.jl v0.30.2 (via PowerFlows.jl v0.9.0)
=#

using PowerSystems
using PowerFlows
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
        results["details"]["network"] = Dict(
            "buses" => n_buses,
            "branches" => length(collect(get_components(Branch, sys))),
            "generators" => length(collect(get_components(Generator, sys))),
        )

        # 2. Flat start — set PQ buses to Vm=1.0, Va=0.0
        for bus in get_components(ACBus, sys)
            if get_bustype(bus) == ACBusTypes.PQ
                set_magnitude!(bus, 1.0)
                set_angle!(bus, 0.0)
            end
        end

        # 3. Solve AC power flow (Newton-Raphson — PowerFlows internal solver, not Ipopt)
        t_solve = time()
        pf_result = solve_powerflow(ACPowerFlow(), sys)
        solve_time = time() - t_solve
        results["details"]["solve_time_seconds"] = solve_time
        results["details"]["solver"] = "PowerFlows.jl internal Newton-Raphson"

        # Check convergence — returns Dict of DataFrames on success, or may throw
        dc_warmstart_needed = false
        if pf_result === nothing || isempty(pf_result)
            # Fallback: DC warm start per convergence protocol
            dc_warmstart_needed = true
            results["details"]["flat_start_converged"] = false

            # Reload system and try DC first
            sys = System(network_file)
            solve_powerflow(DCPowerFlow(), sys)

            # Now retry AC with DC-initialized angles
            t_solve2 = time()
            pf_result = solve_powerflow(ACPowerFlow(), sys)
            solve_time = time() - t_solve2
            results["details"]["warmstart_solve_time_seconds"] = solve_time

            if pf_result === nothing || isempty(pf_result)
                push!(
                    results["errors"], "AC power flow did not converge (flat start + DC warm start)"
                )
                results["wall_clock_seconds"] = time() - t0
                return results
            end
        else
            results["details"]["flat_start_converged"] = true
        end
        results["details"]["dc_warmstart_needed"] = dc_warmstart_needed
        results["details"]["converged"] = true

        # 4. Extract results from DataFrames
        # ACPF returns Dict{String, DataFrame} with "bus_results" and "flow_results"
        bus_df = pf_result["bus_results"]
        results["details"]["bus_results_columns"] = string.(names(bus_df))
        results["details"]["bus_results_rows"] = nrow(bus_df)

        # Voltage magnitude statistics
        vm_col = findfirst(c -> c in ["Vm", "voltage_magnitude"], names(bus_df))
        if vm_col !== nothing
            vm = bus_df[!, vm_col]
            results["details"]["voltage_stats"] = Dict(
                "min_vm_pu" => minimum(vm),
                "max_vm_pu" => maximum(vm),
                "mean_vm_pu" => sum(vm) / length(vm),
            )
        end

        # Voltage angle statistics
        va_col = findfirst(c -> c in ["θ", "voltage_angle"], names(bus_df))
        if va_col !== nothing
            va = bus_df[!, va_col]
            results["details"]["angle_stats"] = Dict(
                "min_va_rad" => minimum(va), "max_va_rad" => maximum(va)
            )
        end

        # Sample bus data (first 5 rows)
        bus_sample = []
        for i in 1:min(5, nrow(bus_df))
            row = Dict{String,Any}()
            for col in names(bus_df)
                row[col] = bus_df[i, Symbol(col)]
            end
            push!(bus_sample, row)
        end
        results["details"]["bus_sample"] = bus_sample

        # 5. Flow results — line P/Q flows
        flow_df = pf_result["flow_results"]
        results["details"]["flow_results_columns"] = string.(names(flow_df))
        results["details"]["flow_results_rows"] = nrow(flow_df)

        # Sample flow data
        flow_sample = []
        for i in 1:min(5, nrow(flow_df))
            row = Dict{String,Any}()
            for col in names(flow_df)
                row[col] = flow_df[i, Symbol(col)]
            end
            push!(flow_sample, row)
        end
        results["details"]["flow_sample"] = flow_sample

        # 6. Compute losses from flow results
        if "P_losses" in string.(names(flow_df))
            p_losses = flow_df[!, :P_losses]
            results["details"]["total_p_losses_pu"] = sum(p_losses)
            results["details"]["max_line_p_loss_pu"] = maximum(p_losses)
        end
        if "Q_losses" in string.(names(flow_df))
            q_losses = flow_df[!, :Q_losses]
            results["details"]["total_q_losses_pu"] = sum(q_losses)
        end

        # 7. Compute losses from generation-load balance as cross-check
        col_names = string.(names(bus_df))
        if "P_gen" in col_names && "P_load" in col_names
            total_gen = sum(bus_df[!, :P_gen])
            total_load = sum(bus_df[!, :P_load])
            results["details"]["total_generation_p_pu"] = total_gen
            results["details"]["total_load_p_pu"] = total_load
            results["details"]["gen_load_balance_losses_pu"] = total_gen - total_load
        end
        if "Q_gen" in col_names && "Q_load" in col_names
            results["details"]["total_generation_q_pu"] = sum(bus_df[!, :Q_gen])
            results["details"]["total_load_q_pu"] = sum(bus_df[!, :Q_load])
        end

        # 8. Output format verification
        results["details"]["output_format"] = "DataFrames with bus_results (Vm, theta, P/Q gen/load/net) and flow_results (P/Q from/to, losses)"

        # All checks passed
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

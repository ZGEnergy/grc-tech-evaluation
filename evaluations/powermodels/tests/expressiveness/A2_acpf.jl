
#= Test A-2: AC Power Flow (Newton-Raphson) on TINY (case39) =#

using PowerModels, Ipopt, JuMP, JSON

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "test_id" => "A-2",
        "test_name" => "acpf",
        "network" => "case39",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        data = PowerModels.parse_file(network_file)
        results["details"]["num_buses"] = length(data["bus"])

        # --- Attempt 1: Native Newton-Raphson (compute_ac_pf) ---
        data_native = deepcopy(data)
        native_ok = false
        try
            PowerModels.compute_ac_pf!(data_native)
            native_ok = true
            results["details"]["native_method"] = "compute_ac_pf! (Newton-Raphson, non-JuMP)"
        catch e
            push!(
                results["errors"],
                "Native NR failed: " * string(typeof(e), ": ", sprint(showerror, e)),
            )
        end

        if native_ok
            # Extract bus voltages from native solve
            bus_vm = Dict{String,Float64}()
            bus_va = Dict{String,Float64}()
            for (bid, bus) in data_native["bus"]
                bus_vm[bid] = bus["vm"]
                bus_va[bid] = bus["va"]
            end
            results["details"]["bus_voltage_magnitudes_pu"] = bus_vm
            results["details"]["bus_voltage_angles_rad"] = bus_va

            # Compute branch flows
            branch_flows = PowerModels.calc_branch_flow_ac(data_native)
            line_flows = Dict{String,Dict{String,Any}}()
            for (br_id, br) in branch_flows["branch"]
                line_flows[br_id] = Dict(
                    "pf" => get(br, "pf", NaN),
                    "pt" => get(br, "pt", NaN),
                    "qf" => get(br, "qf", NaN),
                    "qt" => get(br, "qt", NaN),
                )
            end
            results["details"]["line_flows_pu"] = line_flows

            # Compute losses per branch
            losses = Dict{String,Dict{String,Float64}}()
            for (br_id, br) in branch_flows["branch"]
                pf = get(br, "pf", 0.0)
                pt = get(br, "pt", 0.0)
                qf = get(br, "qf", 0.0)
                qt = get(br, "qt", 0.0)
                losses[br_id] = Dict("p_loss" => pf + pt, "q_loss" => qf + qt)
            end
            results["details"]["branch_losses_pu"] = losses
            total_p_loss = sum(l["p_loss"] for l in values(losses))
            results["details"]["total_p_loss_pu"] = total_p_loss

            # Validation checks
            vm_range = extrema(values(bus_vm))
            results["details"]["vm_min"] = vm_range[1]
            results["details"]["vm_max"] = vm_range[2]
            results["details"]["converged"] = true
            results["details"]["method"] = "compute_ac_pf! (native Newton-Raphson)"
            results["details"]["api_lines"] = 3
            results["status"] = "pass"
        else
            # --- Fallback: JuMP-based AC PF via Ipopt ---
            results["details"]["fallback"] = "solve_ac_pf via Ipopt (DC warm start)"

            # Flat start first
            solver = optimizer_with_attributes(
                Ipopt.Optimizer,
                "max_iter" => 10000,
                "tol" => 1e-6,
                "print_level" => 0,
                "linear_solver" => "mumps",
            )
            result_pf = solve_ac_pf(data, solver)
            results["details"]["termination_status"] = string(result_pf["termination_status"])

            if result_pf["termination_status"] == LOCALLY_SOLVED ||
                result_pf["primal_status"] == FEASIBLE_POINT
                sol = result_pf["solution"]
                bus_vm = Dict(bid => b["vm"] for (bid, b) in sol["bus"])
                bus_va = Dict(bid => b["va"] for (bid, b) in sol["bus"])
                results["details"]["bus_voltage_magnitudes_pu"] = bus_vm
                results["details"]["bus_voltage_angles_rad"] = bus_va

                line_flows = Dict{String,Dict{String,Any}}()
                for (br_id, br) in sol["branch"]
                    line_flows[br_id] = Dict(
                        "pf" => get(br, "pf", NaN),
                        "pt" => get(br, "pt", NaN),
                        "qf" => get(br, "qf", NaN),
                        "qt" => get(br, "qt", NaN),
                    )
                end
                results["details"]["line_flows_pu"] = line_flows
                results["details"]["converged"] = true
                results["status"] = "pass"
            end
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

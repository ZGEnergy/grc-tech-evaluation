#=
Test A-4: AC Feasibility Check on DC OPF dispatch for TINY (IEEE 39-bus)
Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Achievable within the same model context (no export/reimport).
               Voltage violations and thermal limit violations identifiable.
Tool: PowerModels.jl v0.21.5
Solver: Ipopt (for AC PF), HiGHS (for DC OPF)

Approach: Solve DC OPF to get dispatch, fix gen Pg values in data dict,
run compute_ac_pf on the modified data, then check for violations.
=#

using PowerModels, JuMP, HiGHS, Ipopt, JSON

function run(
    network_file::String=joinpath(@__DIR__, "..", "..", "..", "..", "data", "networks", "case39.m")
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    # Warm-up runs
    try
        _data = PowerModels.parse_file(network_file)
        PowerModels.solve_dc_opf(_data, HiGHS.Optimizer)
        _data2 = PowerModels.parse_file(network_file)
        PowerModels.compute_ac_pf(_data2)
    catch
        ;
    end

    t0 = time()
    try
        # ---- Step 1: Solve DC OPF (same as A-3) ----
        data = PowerModels.parse_file(network_file)

        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_branches"] = length(data["branch"])
        results["details"]["num_generators"] = length(data["gen"])

        optimizer = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => false,
        )

        opf_result = PowerModels.solve_dc_opf(data, optimizer)

        term_status = string(opf_result["termination_status"])
        results["details"]["dcopf_termination"] = term_status
        results["details"]["dcopf_objective"] = opf_result["objective"]

        if !(term_status in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"])
            push!(results["errors"], "DC OPF did not converge: $term_status")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        dc_sol = opf_result["solution"]

        # Extract DC OPF dispatch
        dc_dispatch = Dict{String,Float64}()
        for (id, gen) in dc_sol["gen"]
            dc_dispatch[id] = gen["pg"]
        end
        results["details"]["dc_dispatch"] = dc_dispatch

        # ---- Step 2: Fix gen dispatch in data dict and run AC PF ----
        # Work on the SAME data dict -- no export/reimport
        # Set generator active power to DC OPF dispatch values
        for (id, pg_val) in dc_dispatch
            data["gen"][id]["pg"] = pg_val
        end

        # Attempt 1: Flat start (default for compute_ac_pf)
        results["details"]["convergence_attempts"] = []

        ac_result = PowerModels.compute_ac_pf(data)
        ac_converged = ac_result["termination_status"]
        push!(
            results["details"]["convergence_attempts"],
            Dict("attempt" => "flat_start", "converged" => ac_converged),
        )

        if !ac_converged
            # Attempt 2: Warm start from DC angles
            # Use DC solution angles as starting point
            for (id, bus) in dc_sol["bus"]
                if haskey(bus, "va")
                    data["bus"][id]["va"] = bus["va"]
                end
                # Keep vm at 1.0 (flat start for voltage magnitude)
                data["bus"][id]["vm"] = 1.0
            end

            ac_result = PowerModels.compute_ac_pf(data)
            ac_converged = ac_result["termination_status"]
            push!(
                results["details"]["convergence_attempts"],
                Dict("attempt" => "dc_angle_warm_start", "converged" => ac_converged),
            )
        end

        if !ac_converged
            # Attempt 3: Use Ipopt-based solve_ac_pf instead
            ipopt_opt = JuMP.optimizer_with_attributes(
                Ipopt.Optimizer,
                "max_iter" => 10000,
                "tol" => 1e-6,
                "acceptable_tol" => 1e-4,
                "print_level" => 0,
            )
            ac_result = PowerModels.solve_ac_pf(data, ipopt_opt)
            ac_converged_str = string(ac_result["termination_status"])
            ac_converged =
                ac_converged_str in ["LOCALLY_SOLVED", "OPTIMAL", "ALMOST_LOCALLY_SOLVED"]
            push!(
                results["details"]["convergence_attempts"],
                Dict("attempt" => "ipopt_ac_pf", "converged" => ac_converged),
            )
        end

        results["details"]["ac_converged"] = ac_converged

        if !ac_converged
            push!(results["errors"], "AC PF did not converge after all attempts")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        ac_sol = ac_result["solution"]

        # ---- Step 3: Merge solution and compute flows ----
        PowerModels.update_data!(data, ac_sol)
        branch_flows = PowerModels.calc_branch_flow_ac(data)

        # ---- Step 4: Check for voltage violations ----
        voltage_violations = Dict{String,Dict{String,Any}}()
        for (id, bus) in ac_sol["bus"]
            vm = bus["vm"]
            vmin = data["bus"][id]["vmin"]
            vmax = data["bus"][id]["vmax"]
            if vm < vmin || vm > vmax
                voltage_violations[id] = Dict(
                    "vm" => round(vm; digits=6),
                    "vmin" => vmin,
                    "vmax" => vmax,
                    "violation_pu" => round(vm < vmin ? vmin - vm : vm - vmax; digits=6),
                    "type" => vm < vmin ? "undervoltage" : "overvoltage",
                )
            end
        end
        results["details"]["voltage_violations"] = voltage_violations
        results["details"]["num_voltage_violations"] = length(voltage_violations)

        # Voltage magnitude summary
        vm_vals = [bus["vm"] for (_, bus) in ac_sol["bus"]]
        results["details"]["vm_min"] = round(minimum(vm_vals); digits=6)
        results["details"]["vm_max"] = round(maximum(vm_vals); digits=6)
        results["details"]["vm_mean"] = round(sum(vm_vals) / length(vm_vals); digits=6)

        # ---- Step 5: Check for thermal limit violations ----
        thermal_violations = Dict{String,Dict{String,Any}}()
        for (id, br) in branch_flows["branch"]
            rate_a = data["branch"][id]["rate_a"]
            if rate_a > 0 && rate_a < 1e10
                pf = abs(br["pf"])
                qf = haskey(br, "qf") ? abs(br["qf"]) : 0.0
                # Apparent power flow (from end)
                sf = sqrt(pf^2 + qf^2)
                if sf > rate_a
                    thermal_violations[id] = Dict(
                        "apparent_flow_pu" => round(sf; digits=6),
                        "rate_a" => rate_a,
                        "overload_pct" => round((sf / rate_a - 1.0) * 100; digits=2),
                        "pf" => round(br["pf"]; digits=6),
                        "qf" => round(get(br, "qf", 0.0); digits=6),
                    )
                end
            end
        end
        results["details"]["thermal_violations"] = thermal_violations
        results["details"]["num_thermal_violations"] = length(thermal_violations)

        # ---- Step 6: Compute total losses ----
        total_p_loss = 0.0
        total_q_loss = 0.0
        for (_, br) in branch_flows["branch"]
            total_p_loss += br["pf"] + br["pt"]
            total_q_loss += get(br, "qf", 0.0) + get(br, "qt", 0.0)
        end
        results["details"]["total_active_loss_pu"] = round(total_p_loss; digits=6)
        results["details"]["total_reactive_loss_pu"] = round(total_q_loss; digits=6)

        # ---- Step 7: Compare DC vs AC dispatch ----
        ac_dispatch = Dict{String,Float64}()
        for (id, gen) in ac_sol["gen"]
            ac_dispatch[id] = round(gen["pg"]; digits=6)
        end
        results["details"]["ac_dispatch"] = ac_dispatch

        # Dispatch difference (DC fixed gen Pg should be maintained)
        dispatch_diffs = Dict{String,Float64}()
        for (id, dc_pg) in dc_dispatch
            ac_pg = get(ac_dispatch, id, 0.0)
            dispatch_diffs[id] = round(ac_pg - dc_pg; digits=6)
        end
        results["details"]["dispatch_diff_dc_vs_ac"] = dispatch_diffs

        results["details"]["same_model_context"] = true
        results["details"]["approach"] =
            "DC OPF solved, gen Pg values fixed in same data dict, " *
            "compute_ac_pf run on modified dict. No file export/reimport. " *
            "Violations identified by comparing solution against data limits."

        results["status"] = "pass"

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        push!(results["errors"], sprint(showerror, e, catch_backtrace()))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

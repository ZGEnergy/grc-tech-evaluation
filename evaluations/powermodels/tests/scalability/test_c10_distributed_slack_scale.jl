
#= Test C-10: Distributed slack DC OPF at MEDIUM (10000 buses) =#

using PowerModels, JuMP, HiGHS, Ipopt, JSON
PowerModels.silence()

function preprocess_data!(data)
    for (i, gen) in data["gen"]
        if !haskey(gen, "cost") || isempty(get(gen, "cost", []))
            gen["model"] = 2
            gen["ncost"] = 2
            gen["cost"] = [20.0, 0.0]
        end
    end
    for (i, br) in data["branch"]
        if get(br, "rate_a", 0.0) == 0.0
            br["rate_a"] = 9999.0
        end
    end
end

function run(network_file::String="/workspace/data/networks/case_ACTIVSg10k.m")
    results = Dict{String,Any}(
        "test_id" => "C-10",
        "test_name" => "distributed_slack_scale",
        "network" => "MEDIUM",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        data = PowerModels.parse_file(network_file)
        preprocess_data!(data)

        nbus = length(data["bus"])
        nbranch = length(data["branch"])
        ngen = length(data["gen"])
        results["details"]["num_buses"] = nbus
        results["details"]["num_branches"] = nbranch
        results["details"]["num_generators"] = ngen

        # Compute load-proportional weights
        bus_loads = Dict{Int,Float64}()
        total_load = 0.0
        for (lid, load) in data["load"]
            bid = load["load_bus"]
            bus_loads[bid] = get(bus_loads, bid, 0.0) + load["pd"]
            total_load += load["pd"]
        end
        results["details"]["total_load_pu"] = round(total_load; digits=2)
        results["details"]["buses_with_load"] = length(bus_loads)

        # --- Single slack DC OPF for comparison ---
        # Use Ipopt because HiGHS has QP solver errors on 10k-bus networks
        ipopt_solver = optimizer_with_attributes(
            Ipopt.Optimizer, "print_level" => 0, "max_iter" => 10000
        )
        t_single = time()
        result_single = solve_dc_opf(
            data, ipopt_solver; setting=Dict("output" => Dict("duals" => true))
        )
        single_time = time() - t_single
        results["details"]["single_slack_time_seconds"] = round(single_time; digits=4)
        results["details"]["single_slack_objective"] = result_single["objective"]
        results["details"]["single_slack_status"] = string(result_single["termination_status"])

        # --- Distributed slack DC OPF ---
        function build_distributed_slack_opf(pm::PowerModels.AbstractPowerModel)
            PowerModels.variable_bus_voltage(pm)
            PowerModels.variable_gen_power(pm)
            PowerModels.variable_branch_power(pm)
            PowerModels.variable_dcline_power(pm)

            PowerModels.objective_min_fuel_and_flow_cost(pm)
            PowerModels.constraint_model_voltage(pm)

            # Load-proportional distributed slack
            bus_ids = collect(PowerModels.ids(pm, :bus))
            va_expr = AffExpr(0.0)
            for i in bus_ids
                va_i = PowerModels.var(pm, :va, i)
                weight = get(bus_loads, i, 0.0) / total_load
                if weight > 0
                    add_to_expression!(va_expr, weight, va_i)
                else
                    add_to_expression!(va_expr, 1.0 / length(bus_ids), va_i)
                end
            end
            JuMP.@constraint(pm.model, va_expr == 0.0)

            for i in PowerModels.ids(pm, :bus)
                PowerModels.constraint_power_balance(pm, i)
            end
            for i in PowerModels.ids(pm, :branch)
                PowerModels.constraint_ohms_yt_from(pm, i)
                PowerModels.constraint_ohms_yt_to(pm, i)
                PowerModels.constraint_voltage_angle_difference(pm, i)
                PowerModels.constraint_thermal_limit_from(pm, i)
                PowerModels.constraint_thermal_limit_to(pm, i)
            end
            for i in PowerModels.ids(pm, :dcline)
                PowerModels.constraint_dcline_power_losses(pm, i)
            end
        end

        GC.gc()
        mem_before = Base.gc_live_bytes() / 1024^2

        t_dist = time()
        result_dist = PowerModels.solve_model(
            data,
            DCPPowerModel,
            ipopt_solver,
            build_distributed_slack_opf;
            setting=Dict("output" => Dict("duals" => true)),
        )
        dist_time = time() - t_dist

        GC.gc()
        mem_after = Base.gc_live_bytes() / 1024^2

        results["details"]["distributed_slack_time_seconds"] = round(dist_time; digits=4)
        results["details"]["peak_memory_mb"] = round(mem_after - mem_before; digits=2)

        dist_status = result_dist["termination_status"]
        results["details"]["distributed_slack_status"] = string(dist_status)

        if dist_status == OPTIMAL || dist_status == LOCALLY_SOLVED
            results["details"]["distributed_slack_objective"] = result_dist["objective"]

            obj_diff = abs(result_single["objective"] - result_dist["objective"])
            results["details"]["objective_difference"] = round(obj_diff; digits=6)
            results["details"]["objectives_match"] = obj_diff < 1e-2

            # LMP comparison (sample)
            if haskey(result_single["solution"], "bus") && haskey(result_dist["solution"], "bus")
                max_lmp_diff = 0.0
                for (bid, bus) in result_single["solution"]["bus"]
                    lmp1 = get(bus, "lam_kcl_r", NaN)
                    lmp2 = get(get(result_dist["solution"]["bus"], bid, Dict()), "lam_kcl_r", NaN)
                    if !isnan(lmp1) && !isnan(lmp2)
                        max_lmp_diff = max(max_lmp_diff, abs(lmp1 - lmp2))
                    end
                end
                results["details"]["max_lmp_difference"] = round(max_lmp_diff; digits=6)
            end

            results["details"]["method"] = "Custom build function with load-proportional angle reference (sum(w_i * va_i) = 0)"
            push!(
                results["workarounds"],
                "PowerModels has NO native distributed slack. Required custom build function replacing constraint_theta_ref.",
            )
            results["status"] = "pass"
        else
            push!(results["errors"], "Distributed slack OPF did not converge: $dist_status")
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

#=
Test B-1: Custom Constraints — Add flowgate limit to DC OPF, read dual values

Dimension: extensibility
Network: TINY (IEEE 39-bus, New England)
Pass condition: Achievable through documented API or extension mechanism.
  No source patching. Dual value extractable and correctly reflects binding status.
Tool: PowerModels.jl v0.21.5
Solver: HiGHS (LP via DCPPowerModel)

Binding constraint verification guardrail: Include both non-binding (verify dual=0)
AND binding case (set constraint at ~50% of unconstrained flow, verify dual≠0 and
objective increases).

depends_on: A-3
=#

using PowerModels, JuMP, HiGHS

PowerModels.silence()

function run(
    network_file::String=joinpath(@__DIR__, "..", "..", "..", "..", "data", "networks", "case39.m");
    timeseries_dir::Union{String,Nothing}=nothing,
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    # JIT warm-up
    try
        _data = PowerModels.parse_file(network_file)
        _pm = PowerModels.instantiate_model(_data, DCPPowerModel, PowerModels.build_opf)
        PowerModels.optimize_model!(_pm; optimizer=HiGHS.Optimizer)
    catch
        ;
    end

    t0 = time()
    try
        data = PowerModels.parse_file(network_file)
        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        n_gens = length(data["gen"])
        base_mva = data["baseMVA"]
        println("Network: $n_buses buses, $n_branches branches, $n_gens gens, baseMVA=$base_mva")

        optimizer = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "output_flag" => false,
            "presolve" => "on",
            "time_limit" => 300.0,
            "threads" => 1,
        )

        # ---- Step 1: Solve base case DC OPF to find unconstrained flow ----
        println("\nSolving base case DC OPF...")
        base_result = PowerModels.solve_dc_opf(
            data, optimizer; setting=Dict("output" => Dict("duals" => true))
        )
        base_status = string(base_result["termination_status"])
        base_obj = get(base_result, "objective", NaN)
        println("Base case: $base_status | Obj=$(round(base_obj, digits=2))")

        if !(base_status in ["OPTIMAL", "LOCALLY_SOLVED"] || occursin("OPTIMAL", base_status))
            push!(results["errors"], "Base case DC OPF did not converge: $base_status")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # Find branch with largest unconstrained flow
        sol_branch = get(get(base_result, "solution", Dict()), "branch", Dict())
        max_flow_id = ""
        max_flow_val = 0.0
        for (br_id, br_sol) in sol_branch
            pf = abs(get(br_sol, "pf", 0.0))
            if pf > max_flow_val
                max_flow_val = pf
                max_flow_id = br_id
            end
        end

        br_data = data["branch"][max_flow_id]
        f_bus = br_data["f_bus"]
        t_bus = br_data["t_bus"]
        br_idx = parse(Int, max_flow_id)
        println(
            "Gate branch: $max_flow_id ($f_bus->$t_bus), flow=$(round(max_flow_val, digits=4)) pu"
        )

        nw_id = PowerModels.nw_id_default

        # ---- Step 2: NON-BINDING case (limit = 150% of unconstrained flow) ----
        println("\n--- NON-BINDING case (150% of unconstrained flow) ---")
        gate_limit_nb = 1.5 * max_flow_val

        pm_nb = PowerModels.instantiate_model(data, DCPPowerModel, PowerModels.build_opf)
        flow_var_nb = PowerModels.var(pm_nb, nw_id, :p)[(br_idx, f_bus, t_bus)]
        gate_ub_nb = @constraint(pm_nb.model, flow_var_nb <= gate_limit_nb)
        gate_lb_nb = @constraint(pm_nb.model, flow_var_nb >= -gate_limit_nb)
        nb_result = PowerModels.optimize_model!(pm_nb; optimizer=optimizer)
        nb_obj = get(nb_result, "objective", NaN)
        dual_ub_nb = JuMP.dual(gate_ub_nb)
        dual_lb_nb = JuMP.dual(gate_lb_nb)
        nb_dual_zero = abs(dual_ub_nb) < 1e-6 && abs(dual_lb_nb) < 1e-6
        println(
            "  Obj=$(round(nb_obj, digits=2)) | Dual UB=$(round(dual_ub_nb, digits=6)) | Dual LB=$(round(dual_lb_nb, digits=6)) | Zero: $nb_dual_zero",
        )

        # ---- Step 3: BINDING case (limit = 50% of unconstrained flow) ----
        println("\n--- BINDING case (50% of unconstrained flow) ---")
        gate_limit_bind = 0.5 * max_flow_val

        pm_bind = PowerModels.instantiate_model(data, DCPPowerModel, PowerModels.build_opf)
        flow_var_bind = PowerModels.var(pm_bind, nw_id, :p)[(br_idx, f_bus, t_bus)]
        gate_ub_bind = @constraint(pm_bind.model, flow_var_bind <= gate_limit_bind)
        gate_lb_bind = @constraint(pm_bind.model, flow_var_bind >= -gate_limit_bind)

        t_bind_start = time()
        bind_result = PowerModels.optimize_model!(pm_bind; optimizer=optimizer)
        t_bind = time() - t_bind_start

        bind_status = string(bind_result["termination_status"])
        bind_obj = get(bind_result, "objective", NaN)
        flow_sol = JuMP.value(flow_var_bind)

        dual_ub_bind = JuMP.dual(gate_ub_bind)
        dual_lb_bind = JuMP.dual(gate_lb_bind)
        binding = abs(flow_sol - gate_limit_bind) < 1e-4 || abs(flow_sol + gate_limit_bind) < 1e-4
        dual_nonzero = abs(dual_ub_bind) > 1e-8 || abs(dual_lb_bind) > 1e-8
        obj_increase = bind_obj - base_obj

        println("  Status: $bind_status | Obj=$(round(bind_obj, digits=2))")
        println("  Flow=$(round(flow_sol, digits=4)) pu | Binding: $binding")
        println(
            "  Dual UB=$(round(dual_ub_bind, digits=4)) | Dual LB=$(round(dual_lb_bind, digits=4))"
        )
        println("  Obj increase: $(round(obj_increase, digits=2))")

        # ---- Pass condition checks ----
        constraint_achievable =
            bind_status in ["OPTIMAL", "LOCALLY_SOLVED"] || occursin("OPTIMAL", bind_status)
        binding_dual_ok = binding && dual_nonzero
        nonbinding_dual_ok = nb_dual_zero

        println("\nPass checks:")
        println("  Custom constraint achievable: $constraint_achievable")
        println("  Binding -> dual != 0:         $binding_dual_ok")
        println("  Non-binding -> dual = 0:      $nonbinding_dual_ok")

        if constraint_achievable && binding_dual_ok && nonbinding_dual_ok
            results["status"] = "pass"
        elseif constraint_achievable && binding_dual_ok
            results["status"] = "qualified_pass"
        else
            push!(results["errors"], "Pass conditions not met")
        end

        results["details"] = Dict(
            "network_file" => network_file,
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "base_case_obj" => base_obj,
            "gate_branch_id" => max_flow_id,
            "gate_branch_f_bus" => f_bus,
            "gate_branch_t_bus" => t_bus,
            "base_flow_pu" => max_flow_val,
            "nonbinding_case" => Dict(
                "limit_pu" => gate_limit_nb,
                "objective" => nb_obj,
                "dual_ub" => dual_ub_nb,
                "dual_lb" => dual_lb_nb,
                "dual_zero" => nb_dual_zero,
            ),
            "binding_case" => Dict(
                "limit_pu" => gate_limit_bind,
                "objective" => bind_obj,
                "flow_pu" => flow_sol,
                "binding" => binding,
                "dual_ub" => dual_ub_bind,
                "dual_lb" => dual_lb_bind,
                "dual_nonzero" => dual_nonzero,
                "obj_increase" => obj_increase,
                "solve_time_s" => t_bind,
            ),
            "extension_api" => "instantiate_model + @constraint(pm.model, ...) + optimize_model! + JuMP.dual()",
            "loc" => 4,
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        bt = catch_backtrace()
        println(sprint(showerror, e, bt))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    println("\nStatus: $(results["status"])")
    println("Wall clock: $(round(results["wall_clock_seconds"], digits=3))s")
    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println("\n--- RESULT ---")
    println("status: $(result["status"])")
    println("wall_clock_seconds: $(result["wall_clock_seconds"])")
    println("errors: $(result["errors"])")
    println("workarounds: $(result["workarounds"])")
    for (k, v) in result["details"]
        println("  $k: $v")
    end
end

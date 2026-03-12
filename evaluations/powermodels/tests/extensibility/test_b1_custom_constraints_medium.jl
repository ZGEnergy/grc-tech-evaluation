#=
Test B-1: Custom Constraints — MEDIUM grade assessment
Dimension: extensibility
Network: MEDIUM (ACTIVSg 10000-bus, case_ACTIVSg10k.m)
Pass condition: Custom constraint achievable. Dual value extractable and correctly
  reflects binding status.
Tool: PowerModels.jl v0.21.5
Solver: HiGHS (LP via DCPPowerModel)

Approach (same as TINY, scaled to MEDIUM):
  1. Solve base case DC OPF to identify highest-flow branch
  2. instantiate_model(data, DCPPowerModel, build_opf)
  3. Access p variable via var(pm, nw_id, :p)[(branch_idx, f_bus, t_bus)]
  4. Add custom gate limit: @constraint(pm.model, flow_var <= 0.8 * base_flow)
  5. optimize_model! then JuMP.dual(gate_con)
  6. Also test non-binding case (gate = 200% of base flow) to confirm dual = 0

Preprocessing per MEDIUM protocol:
  - Zero-reactance fix: br_x=0 -> 0.0001
  - Zero/Inf RATE_A fix: rate_a=0 or Inf -> 9999.0 pu
  - Linearize quadratic costs -> LP (required for HiGHS at 10k-bus scale)
=#

using PowerModels, JuMP, HiGHS, JSON

PowerModels.silence()

function apply_medium_preprocessing!(data::Dict)
    base_mva = data["baseMVA"]
    n_x_fixed = 0;
    n_rate_fixed = 0
    for (_, branch) in data["branch"]
        if branch["br_x"] == 0.0
            branch["br_x"] = 0.0001;
            n_x_fixed += 1
        end
        ra = get(branch, "rate_a", 0.0)
        if ra == 0.0 || isinf(ra)
            branch["rate_a"] = 9999.0 / base_mva;
            n_rate_fixed += 1
        end
    end
    return (n_x_fixed, n_rate_fixed)
end

function linearize_costs!(data::Dict)
    n = 0
    for (_, gen) in data["gen"]
        if get(gen, "model", 2) == 2 && get(gen, "ncost", 0) >= 3
            c = gen["cost"]
            if abs(c[1]) > 1e-10
                gen["cost"] = [c[2], c[3]];
                gen["ncost"] = 2;
                n += 1
            end
        end
    end
    return n
end

function run(
    network_file::String=joinpath(
        @__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg10k.m"
    ),
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    # JIT warm-up on case39
    try
        tiny_file = joinpath(dirname(network_file), "case39.m")
        _data = PowerModels.parse_file(tiny_file)
        _pm = PowerModels.instantiate_model(_data, DCPPowerModel, PowerModels.build_opf)
        PowerModels.optimize_model!(_pm; optimizer=HiGHS.Optimizer)
    catch
        ;
    end

    t0 = time()
    try
        println("Loading network: $network_file")
        data = PowerModels.parse_file(network_file)

        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        n_gens = length(data["gen"])
        base_mva = data["baseMVA"]
        println("Network: $n_buses buses, $n_branches branches, $n_gens gens, baseMVA=$base_mva")

        n_x_fixed, n_rate_fixed = apply_medium_preprocessing!(data)
        println("Preprocessing: $n_x_fixed x-fixed, $n_rate_fixed rate-fixed")

        n_lin = linearize_costs!(data)
        println("Cost linearization: $n_lin generators")

        optimizer = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "output_flag" => false,
            "presolve" => "on",
            "time_limit" => 300.0,
            "threads" => 1,
        )

        # ---- Step 1: Solve base case DC OPF ----
        println("\nSolving base case DC OPF...")
        t_base_start = time()
        base_result = PowerModels.solve_dc_opf(
            data, optimizer; setting=Dict("output" => Dict("duals" => true))
        )
        t_base = time() - t_base_start
        base_obj = get(base_result, "objective", NaN)
        base_status = string(base_result["termination_status"])
        println(
            "Base case: $base_status | Obj=$(round(base_obj,digits=2)) \$/h | $(round(t_base,digits=2))s",
        )

        if !(base_status in ["OPTIMAL", "LOCALLY_SOLVED"] || occursin("OPTIMAL", base_status))
            push!(results["errors"], "Base case DC OPF did not converge: $base_status")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # Extract base case branch flows
        base_flows = Dict{String,Float64}()
        sol_branch = get(get(base_result, "solution", Dict()), "branch", Dict())
        for (br_id, br_sol) in sol_branch
            base_flows[br_id] = abs(get(br_sol, "pf", 0.0))
        end

        # Find branch with largest absolute flow
        max_flow_id = ""
        max_flow_val = 0.0
        for (br_id, pf) in base_flows
            if pf > max_flow_val
                max_flow_val = pf;
                max_flow_id = br_id
            end
        end
        gate_branch_id = max_flow_id
        gate_limit = 0.8 * max_flow_val   # 80% of base flow -> should bind

        br_data = data["branch"][gate_branch_id]
        f_bus = br_data["f_bus"]
        t_bus = br_data["t_bus"]
        br_idx = parse(Int, gate_branch_id)

        println("Gate branch: $gate_branch_id ($f_bus->$t_bus)")
        println("  base_flow=$(round(max_flow_val*base_mva,digits=2)) MW")
        println("  gate_limit=$(round(gate_limit*base_mva,digits=2)) MW (80% of base flow)")

        # ---- Step 2: BINDING case ----
        println("\n--- BINDING case (gate = 80% base flow) ---")
        pm_bind = PowerModels.instantiate_model(data, DCPPowerModel, PowerModels.build_opf)

        nw_id = PowerModels.nw_id_default
        p_vars = PowerModels.var(pm_bind, nw_id, :p)
        flow_var = p_vars[(br_idx, f_bus, t_bus)]

        gate_con_ub = @constraint(pm_bind.model, flow_var <= gate_limit)
        gate_con_lb = @constraint(pm_bind.model, flow_var >= -gate_limit)

        t_bind_start = time()
        bind_result = PowerModels.optimize_model!(pm_bind; optimizer=optimizer)
        t_bind = time() - t_bind_start

        bind_status = string(bind_result["termination_status"])
        bind_obj = get(bind_result, "objective", NaN)
        println(
            "  Status: $bind_status | Obj=$(round(bind_obj,digits=2)) \$/h | $(round(t_bind,digits=2))s",
        )

        bind_converged =
            bind_status in ["OPTIMAL", "LOCALLY_SOLVED"] || occursin("OPTIMAL", bind_status)

        dual_ub = JuMP.dual(gate_con_ub)
        dual_lb = JuMP.dual(gate_con_lb)

        flow_sol_pu = JuMP.value(flow_var)
        upper_binding = abs(flow_sol_pu - gate_limit) < 1e-4
        lower_binding = abs(flow_sol_pu + gate_limit) < 1e-4
        binding = upper_binding || lower_binding
        dual_nonzero = abs(dual_ub) > 1e-8 || abs(dual_lb) > 1e-8
        obj_increase = bind_obj - base_obj

        println("  Flow: $(round(flow_sol_pu*base_mva,digits=2)) MW | Binding: $binding")
        println(
            "  Dual UB: $(round(dual_ub,digits=6)) | Dual LB: $(round(dual_lb,digits=6)) | Nonzero: $dual_nonzero",
        )
        println("  Obj increase: $(round(obj_increase,digits=2)) \$/h")

        # ---- Step 3: NON-BINDING case ----
        println("\n--- NON-BINDING case (gate = 200% base flow) ---")
        gate_limit_nb = 2.0 * max_flow_val

        pm_nb = PowerModels.instantiate_model(data, DCPPowerModel, PowerModels.build_opf)
        p_vars_nb = PowerModels.var(pm_nb, nw_id, :p)
        flow_var_nb = p_vars_nb[(br_idx, f_bus, t_bus)]

        gate_con_nb_ub = @constraint(pm_nb.model, flow_var_nb <= gate_limit_nb)
        gate_con_nb_lb = @constraint(pm_nb.model, flow_var_nb >= -gate_limit_nb)

        t_nb_start = time()
        nb_result = PowerModels.optimize_model!(pm_nb; optimizer=optimizer)
        t_nb = time() - t_nb_start

        nb_status = string(nb_result["termination_status"])
        nb_obj = get(nb_result, "objective", NaN)
        println(
            "  Status: $nb_status | Obj=$(round(nb_obj,digits=2)) \$/h | $(round(t_nb,digits=2))s"
        )

        dual_nb_ub = JuMP.dual(gate_con_nb_ub)
        dual_nb_lb = JuMP.dual(gate_con_nb_lb)
        flow_nb_pu = JuMP.value(flow_var_nb)
        nb_dual_zero = abs(dual_nb_ub) < 1e-6 && abs(dual_nb_lb) < 1e-6

        println(
            "  Flow: $(round(flow_nb_pu*base_mva,digits=2)) MW | Gate: $(round(gate_limit_nb*base_mva,digits=2)) MW",
        )
        println(
            "  Dual UB: $(round(dual_nb_ub,digits=6)) | Dual LB: $(round(dual_nb_lb,digits=6)) | Zero: $nb_dual_zero",
        )

        # ---- Pass conditions ----
        constraint_achievable = bind_converged
        binding_dual_ok = binding && dual_nonzero
        nonbinding_dual_ok = nb_dual_zero

        println("\nPass checks:")
        println("  Custom constraint achievable: $constraint_achievable")
        println(
            "  Binding -> dual != 0:         $binding_dual_ok  (binding=$binding, nonzero=$dual_nonzero)",
        )
        println("  Non-binding -> dual = 0:      $nonbinding_dual_ok")

        if constraint_achievable && binding_dual_ok && nonbinding_dual_ok
            results["status"] = "pass"
        elseif constraint_achievable && binding_dual_ok
            results["status"] = "qualified_pass"
            push!(
                results["workarounds"],
                "Non-binding dual not verified as zero (dual_nb_ub=$(round(dual_nb_ub,digits=8)))",
            )
        elseif constraint_achievable
            results["status"] = "qualified_pass"
            push!(
                results["workarounds"],
                "Custom constraint achievable but binding/dual status unclear: binding=$binding, dual_nonzero=$dual_nonzero",
            )
        else
            push!(results["errors"], "Custom constraint not achievable: converged=$bind_converged")
        end

        results["details"] = Dict(
            "network_file" => network_file,
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "n_x_fixed" => n_x_fixed,
            "n_rate_fixed" => n_rate_fixed,
            "n_costs_linearized" => n_lin,
            "base_case_obj" => base_obj,
            "base_case_time_s" => t_base,
            "gate_branch_id" => gate_branch_id,
            "gate_branch_f_bus" => f_bus,
            "gate_branch_t_bus" => t_bus,
            "base_flow_pu" => max_flow_val,
            "base_flow_mw" => max_flow_val * base_mva,
            "gate_limit_pu" => gate_limit,
            "gate_limit_mw" => gate_limit * base_mva,
            "binding_case" => Dict(
                "status" => bind_status,
                "objective" => bind_obj,
                "solve_time_s" => t_bind,
                "flow_pu" => flow_sol_pu,
                "flow_mw" => flow_sol_pu * base_mva,
                "binding" => binding,
                "dual_ub" => dual_ub,
                "dual_lb" => dual_lb,
                "dual_nonzero" => dual_nonzero,
                "obj_increase" => obj_increase,
            ),
            "nonbinding_case" => Dict(
                "status" => nb_status,
                "objective" => nb_obj,
                "solve_time_s" => t_nb,
                "flow_pu" => flow_nb_pu,
                "gate_limit_pu" => gate_limit_nb,
                "dual_ub" => dual_nb_ub,
                "dual_lb" => dual_nb_lb,
                "dual_zero" => nb_dual_zero,
            ),
            "extension_api" => "instantiate_model(data, DCPPowerModel, build_opf) -> var(pm, nw_id, :p)[(br_idx, f_bus, t_bus)] -> @constraint(pm.model, ...) -> optimize_model! -> JuMP.dual()",
            "solver" => "HiGHS (LP via DCPPowerModel, costs linearized QP->LP)",
            "loc" => 125,
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        println("ERROR in B-1 MEDIUM: $(typeof(e)): $e")
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
    println("\n--- RESULT SUMMARY ---")
    println("status:             $(result["status"])")
    println("wall_clock_seconds: $(result["wall_clock_seconds"])")
    println("errors:             $(result["errors"])")
    println("workarounds:        $(result["workarounds"])")
    open("/tmp/b1_custom_constraints_medium_result.json", "w") do f
        JSON.print(f, result, 2)
    end
    println("Result written to /tmp/b1_custom_constraints_medium_result.json")
end

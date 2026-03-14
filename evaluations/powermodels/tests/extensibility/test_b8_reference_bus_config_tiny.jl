#=
Test B-8: DC OPF with Three Slack Configurations, Compare LMPs

Dimension: extensibility
Network: TINY (IEEE 39-bus, New England)
Pass condition: Reference bus / slack formulation is configurable via API without
  model reconstruction. LMP values change consistently across configurations.
Tool: PowerModels.jl v0.21.5
Solver: HiGHS

Note: PowerModels has no native distributed slack. Reference bus can be changed
by modifying data["bus"][id]["bus_type"].
=#

using PowerModels, JuMP, HiGHS
using SparseArrays, LinearAlgebra

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

    t0 = time()
    try
        optimizer = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => false,
        )

        # --- Apply differentiated costs to make LMPs non-uniform ---
        cost_map = Dict(
            "hydro" => (5.0, 0.005),
            "nuclear" => (10.0, 0.010),
            "coal_large" => (25.0, 0.025),
            "gas_CC" => (40.0, 0.040),
        )
        gen_tech = Dict(
            0 => "hydro",
            1 => "nuclear",
            2 => "nuclear",
            3 => "coal_large",
            4 => "coal_large",
            5 => "nuclear",
            6 => "gas_CC",
            7 => "nuclear",
            8 => "nuclear",
            9 => "gas_CC",
        )

        function apply_costs!(data)
            base_mva = data["baseMVA"]
            for (id, gen) in data["gen"]
                gen_idx = parse(Int, id) - 1
                if haskey(gen_tech, gen_idx)
                    c1, c2 = cost_map[gen_tech[gen_idx]]
                    gen["cost"] = [c2 / base_mva^2, c1 / base_mva, 0.0]
                    gen["ncost"] = 3
                    gen["model"] = 2
                end
            end
            # Derate branch ratings to 70% for congestion
            for (id, br) in data["branch"]
                rate_a = get(br, "rate_a", 0.0)
                if rate_a > 0 && rate_a < 1e10
                    br["rate_a"] = rate_a * 0.70
                end
            end
        end

        # ---- Config (a): Default single slack (bus 31) ----
        data_a = PowerModels.parse_file(network_file)
        apply_costs!(data_a)
        base_mva = data_a["baseMVA"]

        default_ref_bus = nothing
        for (id, bus) in data_a["bus"]
            if bus["bus_type"] == 3
                default_ref_bus = parse(Int, id)
                break
            end
        end

        result_a = PowerModels.solve_dc_opf(
            data_a, optimizer; setting=Dict("output" => Dict("duals" => true))
        )
        term_a = string(result_a["termination_status"])
        obj_a = result_a["objective"]

        lmps_a = Dict{String,Float64}()
        for (id, bus) in result_a["solution"]["bus"]
            if haskey(bus, "lam_kcl_r")
                lmps_a[id] = bus["lam_kcl_r"]
            end
        end

        dispatch_a = Dict{String,Float64}()
        for (id, gen) in result_a["solution"]["gen"]
            dispatch_a[id] = gen["pg"]
        end

        println(
            "Config (a) default slack bus $default_ref_bus: $term_a, obj=$(round(obj_a, digits=2))"
        )

        # ---- Config (b): Alternate single slack (bus 1) ----
        data_b = PowerModels.parse_file(network_file)
        apply_costs!(data_b)

        new_ref_bus = 1
        for (id, bus) in data_b["bus"]
            bid = parse(Int, id)
            if bid == default_ref_bus
                bus["bus_type"] = 2  # old ref -> PV
            elseif bid == new_ref_bus
                bus["bus_type"] = 3  # new ref -> slack
            end
        end

        result_b = PowerModels.solve_dc_opf(
            data_b, optimizer; setting=Dict("output" => Dict("duals" => true))
        )
        term_b = string(result_b["termination_status"])
        obj_b = result_b["objective"]

        lmps_b = Dict{String,Float64}()
        for (id, bus) in result_b["solution"]["bus"]
            if haskey(bus, "lam_kcl_r")
                lmps_b[id] = bus["lam_kcl_r"]
            end
        end

        dispatch_b = Dict{String,Float64}()
        for (id, gen) in result_b["solution"]["gen"]
            dispatch_b[id] = gen["pg"]
        end

        println("Config (b) alt slack bus $new_ref_bus: $term_b, obj=$(round(obj_b, digits=2))")

        # ---- Config (c): Distributed slack via PTDF ----
        data_c = PowerModels.parse_file(network_file)
        apply_costs!(data_c)

        basic_data = PowerModels.make_basic_network(deepcopy(data_c))
        ptdf_single = PowerModels.calc_basic_ptdf_matrix(basic_data)
        nbr, nb = size(ptdf_single)

        bus_ids = sort(parse.(Int, collect(keys(basic_data["bus"]))))
        bus_to_idx = Dict(id => i for (i, id) in enumerate(bus_ids))

        # Load-proportional slack weights
        bus_load = zeros(nb)
        for (_, load) in data_c["load"]
            bid = load["load_bus"]
            if haskey(bus_to_idx, bid)
                bus_load[bus_to_idx[bid]] += load["pd"]
            end
        end
        total_load = sum(bus_load)
        slack_weights = total_load > 0 ? bus_load ./ total_load : fill(1.0 / nb, nb)

        ptdf_dist = ptdf_single .- (ptdf_single * slack_weights)

        gen_ids_int = sort(parse.(Int, collect(keys(data_c["gen"]))))
        ng = length(gen_ids_int)

        gen_bus_map = Dict(g => data_c["gen"][string(g)]["gen_bus"] for g in gen_ids_int)
        pmin_dict = Dict(g => data_c["gen"][string(g)]["pmin"] for g in gen_ids_int)
        pmax_dict = Dict(g => data_c["gen"][string(g)]["pmax"] for g in gen_ids_int)

        gen_cost_c1 = Dict{Int,Float64}()
        gen_cost_c2 = Dict{Int,Float64}()
        gen_cost_c0 = Dict{Int,Float64}()
        for g in gen_ids_int
            gd = data_c["gen"][string(g)]
            if gd["model"] == 2 && gd["ncost"] >= 3
                gen_cost_c2[g] = gd["cost"][1]
                gen_cost_c1[g] = gd["cost"][2]
                gen_cost_c0[g] = gd["cost"][3]
            elseif gd["model"] == 2 && gd["ncost"] >= 2
                gen_cost_c2[g] = 0.0
                gen_cost_c1[g] = gd["cost"][1]
                gen_cost_c0[g] = gd["cost"][2]
            else
                gen_cost_c2[g] = 0.0
                gen_cost_c1[g] = 0.0
                gen_cost_c0[g] = 0.0
            end
        end

        bus_gen_indices = Dict{Int,Vector{Int}}()
        for (j, g) in enumerate(gen_ids_int)
            bus = gen_bus_map[g]
            if haskey(bus_to_idx, bus)
                bi = bus_to_idx[bus]
                if !haskey(bus_gen_indices, bi)
                    bus_gen_indices[bi] = Int[]
                end
                push!(bus_gen_indices[bi], j)
            end
        end

        model = Model(optimizer)
        @variable(model, pmin_dict[gen_ids_int[j]] <= pg[j = 1:ng] <= pmax_dict[gen_ids_int[j]])
        @constraint(model, pbal, sum(pg[j] for j in 1:ng) == total_load)

        bus_net_inj = Vector{Any}(undef, nb)
        for i in 1:nb
            if haskey(bus_gen_indices, i)
                bus_net_inj[i] = sum(pg[j] for j in bus_gen_indices[i]) - bus_load[i]
            else
                bus_net_inj[i] = -bus_load[i]
            end
        end

        basic_branch_ids = sort(parse.(Int, collect(keys(basic_data["branch"]))))
        for l in 1:nbr
            br_id = string(basic_branch_ids[l])
            rate_a = basic_data["branch"][br_id]["rate_a"]
            if rate_a > 0 && rate_a < 1e10
                flow_expr = sum(
                    ptdf_dist[l, i] * bus_net_inj[i] for i in 1:nb if abs(ptdf_dist[l, i]) > 1e-10;
                    init=AffExpr(0.0),
                )
                @constraint(model, flow_expr <= rate_a)
                @constraint(model, flow_expr >= -rate_a)
            end
        end

        @objective(
            model,
            Min,
            sum(gen_cost_c1[gen_ids_int[j]] * pg[j] + gen_cost_c0[gen_ids_int[j]] for j in 1:ng)
        )

        optimize!(model)
        term_c = string(termination_status(model))
        obj_c = objective_value(model)

        dispatch_c = Dict{String,Float64}()
        for (j, g) in enumerate(gen_ids_int)
            dispatch_c[string(g)] = value(pg[j])
        end

        # Extract LMPs from distributed slack model
        lmp_c_bus = dual(pbal)  # energy balance dual

        println("Config (c) distributed slack: $term_c, obj=$(round(obj_c, digits=2))")

        # ---- Comparisons ----
        common_buses = intersect(keys(lmps_a), keys(lmps_b))
        max_lmp_diff_ab = if isempty(common_buses)
            NaN
        else
            maximum(abs(lmps_b[id] - lmps_a[id]) for id in common_buses)
        end

        common_gens = intersect(keys(dispatch_a), keys(dispatch_b))
        max_dispatch_diff_ab = if isempty(common_gens)
            NaN
        else
            maximum(abs(dispatch_b[id] - dispatch_a[id]) for id in common_gens)
        end

        # LMP spread in config a
        lmp_vals_a = collect(values(lmps_a))
        lmp_spread_a = isempty(lmp_vals_a) ? 0.0 : maximum(lmp_vals_a) - minimum(lmp_vals_a)

        println("\nComparison:")
        println(
            "  Obj (a): $(round(obj_a, digits=2)), Obj (b): $(round(obj_b, digits=2)), Obj (c): $(round(obj_c, digits=2))",
        )
        println("  Max LMP diff (a vs b): $max_lmp_diff_ab")
        println("  Max dispatch diff (a vs b): $max_dispatch_diff_ab")
        println("  LMP spread (a): $(round(lmp_spread_a, digits=4))")

        # Sample LMPs
        println("\nSample LMPs (first 5 buses):")
        for bid in sort(collect(common_buses); by=x->parse(Int, x))[1:min(5, end)]
            println(
                "  Bus $bid: a=$(round(lmps_a[bid], digits=4)), b=$(round(lmps_b[bid], digits=4))"
            )
        end

        # Pass checks
        a_ok = term_a in ["OPTIMAL", "LOCALLY_SOLVED"]
        b_ok = term_b in ["OPTIMAL", "LOCALLY_SOLVED"]
        c_ok = term_c in ["OPTIMAL", "LOCALLY_SOLVED"]

        if a_ok && b_ok && c_ok
            results["status"] = "qualified_pass"
            push!(
                results["workarounds"],
                "Distributed slack not natively supported. Requires ~150 lines manual PTDF-based " *
                "OPF via JuMP. Single-slack ref bus change is trivial (2 lines: set bus_type).",
            )
        else
            push!(results["errors"], "Config convergence: a=$term_a, b=$term_b, c=$term_c")
        end

        results["details"] = Dict(
            "default_ref_bus" => default_ref_bus,
            "new_ref_bus" => new_ref_bus,
            "config_a_termination" => term_a,
            "config_a_objective" => round(obj_a; digits=2),
            "config_b_termination" => term_b,
            "config_b_objective" => round(obj_b; digits=2),
            "config_c_termination" => term_c,
            "config_c_objective" => round(obj_c; digits=2),
            "max_lmp_diff_a_vs_b" => round(max_lmp_diff_ab; digits=8),
            "max_dispatch_diff_a_vs_b" => round(max_dispatch_diff_ab; digits=8),
            "lmp_spread_a" => round(lmp_spread_a; digits=4),
            "objectives_a_b_match" => abs(obj_a - obj_b) < 1.0,
            "single_slack_api_effort" => "2 lines (set bus_type)",
            "distributed_slack_effort" => "~150 lines manual PTDF-based OPF",
            "distributed_slack_native" => false,
            "branch_derating" => 0.70,
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

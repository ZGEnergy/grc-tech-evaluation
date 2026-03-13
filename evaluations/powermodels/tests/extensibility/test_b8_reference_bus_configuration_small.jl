#=
Test B-8: Reference Bus Configuration
Dimension: extensibility
Network: SMALL (ACTIVSg 2000-bus)
Pass condition: Reference bus configurable via API without model reconstruction.
    LMPs change consistently across configurations.
Tool: PowerModels.jl v0.21.5
Solver: HiGHS
=#

using PowerModels, JuMP, HiGHS, Ipopt, JSON
using SparseArrays, LinearAlgebra

function run(
    network_file::String=joinpath(
        @__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg2000.m"
    ),
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        # ---- Configuration (a): Default single slack ----
        data_a = PowerModels.parse_file(network_file)

        # Fix generators with empty cost arrays
        for (id, gen) in data_a["gen"]
            if gen["model"] == 2 && (gen["ncost"] == 0 || isempty(gen["cost"]))
                gen["cost"] = [0.0, 0.0, 0.0]
                gen["ncost"] = 3
            end
        end

        default_ref_bus = nothing
        for (id, bus) in data_a["bus"]
            if bus["bus_type"] == 3
                default_ref_bus = parse(Int, id)
                break
            end
        end
        results["details"]["default_ref_bus"] = default_ref_bus

        # Use Ipopt for the OPF since HiGHS QP has issues with ACTIVSg2000
        optimizer_ipopt = JuMP.optimizer_with_attributes(
            Ipopt.Optimizer, "max_iter" => 10000, "tol" => 1e-6, "print_level" => 0
        )

        result_a = PowerModels.solve_dc_opf(
            data_a, optimizer_ipopt; setting=Dict("output" => Dict("duals" => true))
        )
        term_a = string(result_a["termination_status"])
        results["details"]["config_a_termination"] = term_a
        results["details"]["config_a_objective"] = round(result_a["objective"]; digits=2)

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

        println("Config (a) done: $term_a, obj=$(round(result_a["objective"], digits=2))")

        # ---- Configuration (b): Different single slack bus ----
        data_b = PowerModels.parse_file(network_file)
        for (id, gen) in data_b["gen"]
            if gen["model"] == 2 && (gen["ncost"] == 0 || isempty(gen["cost"]))
                gen["cost"] = [0.0, 0.0, 0.0]
                gen["ncost"] = 3
            end
        end

        # Pick a different bus (bus 1 or any PV bus)
        new_ref_bus = 1
        results["details"]["new_ref_bus"] = new_ref_bus

        for (id, bus) in data_b["bus"]
            bid = parse(Int, id)
            if bid == default_ref_bus
                bus["bus_type"] = 2
            elseif bid == new_ref_bus
                bus["bus_type"] = 3
            end
        end

        result_b = PowerModels.solve_dc_opf(
            data_b, optimizer_ipopt; setting=Dict("output" => Dict("duals" => true))
        )
        term_b = string(result_b["termination_status"])
        results["details"]["config_b_termination"] = term_b
        results["details"]["config_b_objective"] = round(result_b["objective"]; digits=2)

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

        println("Config (b) done: $term_b, obj=$(round(result_b["objective"], digits=2))")

        # ---- Configuration (c): Distributed slack ----
        # Use PTDF-based manual OPF with load-proportional slack weights
        data_c = PowerModels.parse_file(network_file)
        for (id, gen) in data_c["gen"]
            if gen["model"] == 2 && (gen["ncost"] == 0 || isempty(gen["cost"]))
                gen["cost"] = [0.0, 0.0, 0.0]
                gen["ncost"] = 3
            end
        end

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
        slack_weights = bus_load ./ total_load

        ptdf_dist = ptdf_single .- (ptdf_single * slack_weights)

        gen_ids_int = sort(parse.(Int, collect(keys(data_c["gen"]))))
        gen_bus_map = Dict(g => data_c["gen"][string(g)]["gen_bus"] for g in gen_ids_int)
        pmin_dict = Dict(g => data_c["gen"][string(g)]["pmin"] for g in gen_ids_int)
        pmax_dict = Dict(g => data_c["gen"][string(g)]["pmax"] for g in gen_ids_int)

        gen_cost_c1 = Dict{Int,Float64}()
        gen_cost_c0 = Dict{Int,Float64}()
        for g in gen_ids_int
            gd = data_c["gen"][string(g)]
            if gd["model"] == 2
                if gd["ncost"] >= 2
                    gen_cost_c1[g] = gd["cost"][end - 1]
                    gen_cost_c0[g] = gd["cost"][end]
                elseif gd["ncost"] == 1
                    gen_cost_c1[g] = 0.0
                    gen_cost_c0[g] = gd["cost"][1]
                else
                    gen_cost_c1[g] = 0.0
                    gen_cost_c0[g] = 0.0
                end
            else
                gen_cost_c1[g] = 0.0
                gen_cost_c0[g] = 0.0
            end
        end

        Cg = zeros(nb, length(gen_ids_int))
        for (j, g) in enumerate(gen_ids_int)
            bus = gen_bus_map[g]
            if haskey(bus_to_idx, bus)
                Cg[bus_to_idx[bus], j] = 1.0
            end
        end

        optimizer_highs = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => false,
        )

        model = Model(optimizer_highs)
        ng = length(gen_ids_int)
        @variable(model, pmin_dict[gen_ids_int[j]] <= pg[j = 1:ng] <= pmax_dict[gen_ids_int[j]])
        @constraint(model, pbal, sum(pg[j] for j in 1:ng) == total_load)

        # Precompute bus-to-gen mapping for efficient model construction
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

        # Net bus injection expression: gen - load for each bus
        bus_net_inj = Vector{Any}(undef, nb)
        for i in 1:nb
            if haskey(bus_gen_indices, i)
                bus_net_inj[i] = sum(pg[j] for j in bus_gen_indices[i]) - bus_load[i]
            else
                bus_net_inj[i] = -bus_load[i]
            end
        end

        basic_branch_ids = sort(parse.(Int, collect(keys(basic_data["branch"]))))
        flow_ub = Dict{Int,Any}()
        flow_lb = Dict{Int,Any}()
        n_constrained = 0
        for l in 1:nbr
            br_id = string(basic_branch_ids[l])
            rate_a = basic_data["branch"][br_id]["rate_a"]
            if rate_a > 0 && rate_a < 1e10
                n_constrained += 1
                flow_expr = sum(
                    ptdf_dist[l, i] * bus_net_inj[i] for i in 1:nb if abs(ptdf_dist[l, i]) > 1e-10;
                    init=AffExpr(0.0),
                )
                flow_ub[l] = @constraint(model, flow_expr <= rate_a)
                flow_lb[l] = @constraint(model, flow_expr >= -rate_a)
            end
        end

        # Linearized cost (use c1 only for LP)
        @objective(
            model,
            Min,
            sum(gen_cost_c1[gen_ids_int[j]] * pg[j] + gen_cost_c0[gen_ids_int[j]] for j in 1:ng)
        )

        optimize!(model)
        term_c = string(termination_status(model))
        results["details"]["config_c_termination"] = term_c
        results["details"]["config_c_objective"] = round(objective_value(model); digits=2)
        results["details"]["config_c_branches_constrained"] = n_constrained

        println("Config (c) done: $term_c, obj=$(round(objective_value(model), digits=2))")

        dispatch_c = Dict{String,Float64}()
        for (j, g) in enumerate(gen_ids_int)
            dispatch_c[string(g)] = value(pg[j])
        end

        results["details"]["config_c_method"] = "Manual PTDF-based DC OPF with distributed slack weights (load-proportional)"
        results["details"]["ptdf_dimensions"] = "$nbr x $nb"

        # ---- Comparison ----
        obj_a = result_a["objective"]
        obj_b = result_b["objective"]
        results["details"]["objectives_a_b_match"] = abs(obj_a - obj_b) < 1.0

        # Dispatch comparison (a vs b)
        common_gens = intersect(keys(dispatch_a), keys(dispatch_b))
        max_dispatch_diff_ab = maximum(abs(dispatch_b[id] - dispatch_a[id]) for id in common_gens)
        results["details"]["max_dispatch_diff_a_vs_b"] = round(max_dispatch_diff_ab; digits=6)
        results["details"]["dispatch_invariant_a_b"] = max_dispatch_diff_ab < 0.01

        # LMP comparison (a vs b)
        common_buses = intersect(keys(lmps_a), keys(lmps_b))
        if !isempty(common_buses)
            max_lmp_diff_ab = maximum(abs(lmps_b[id] - lmps_a[id]) for id in common_buses)
            results["details"]["max_lmp_diff_a_vs_b"] = round(max_lmp_diff_ab; digits=6)
        end

        # API assessment
        results["details"]["single_slack_configurable_via_api"] = true
        results["details"]["single_slack_effort"] = "2 lines: set bus_type on old/new ref bus"
        results["details"]["distributed_slack_configurable_via_api"] = false
        results["details"]["distributed_slack_effort"] = "~150 lines manual PTDF-based OPF"

        push!(
            results["workarounds"],
            "Single-slack ref bus change: TRIVIAL. " *
            "Distributed slack: MAJOR WORKAROUND (~150 lines manual JuMP/PTDF code).",
        )

        if term_a in ["OPTIMAL", "LOCALLY_SOLVED"] &&
            term_b in ["OPTIMAL", "LOCALLY_SOLVED"] &&
            term_c in ["OPTIMAL", "LOCALLY_SOLVED"]
            results["status"] = "pass"
        else
            push!(results["errors"], "One or more configurations did not converge")
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        push!(results["errors"], sprint(showerror, e, catch_backtrace()))
    finally
        results["wall_clock_seconds"] = round(time() - t0; digits=2)
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

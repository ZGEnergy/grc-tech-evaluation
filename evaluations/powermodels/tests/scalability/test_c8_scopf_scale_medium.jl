#=
Test C-8: SCOPF Scale — MEDIUM (ACTIVSg 10000-bus)
Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus)
Pass condition: Wall-clock time, peak memory, number of iterations (if screening),
    number of binding contingencies recorded.

Parameters:
  medium_contingency_count: 50
  iterative_screening_permitted: true
  time_budget: 600s

Implementation: Iterative Benders/cutting-plane DC SCOPF
  1. Solve base-case DC OPF (LP with HiGHS)
  2. Check N-1 contingency flows via B-theta DCPF (efficient: modify branch status only)
  3. If violations found, add those contingency flow constraint blocks to JuMP model
  4. Re-solve and repeat until no new violations (or budget exhausted)

Preprocessing: zero-RATE_A fix, linearized costs
Note: Island pre-screening done efficiently by toggling br_status in existing dict (no deepcopy).
=#

using PowerModels, JuMP, HiGHS, JSON
using LinearAlgebra
using Base.Sys: maxrss

PowerModels.silence()

function apply_medium_preprocessing!(data::Dict)
    n_rate = 0
    n_cost = 0
    for (_, branch) in data["branch"]
        if get(branch, "rate_a", 0.0) == 0.0 || isinf(get(branch, "rate_a", 0.0))
            branch["rate_a"] = 9999.0
            n_rate += 1
        end
    end
    for (_, gen) in data["gen"]
        if get(gen, "model", 2) == 2 && length(get(gen, "cost", [])) > 2 && gen["cost"][1] != 0.0
            gen["cost"] = [gen["cost"][2], gen["cost"][3]]
            gen["ncost"] = 2
            n_cost += 1
        end
    end
    return n_rate, n_cost
end

# Check connectivity by toggling br_status in-place (no deepcopy) — much faster
function check_islanding_inplace!(data::Dict, br_id::Int)::Bool
    br_key = string(br_id)
    orig_status = data["branch"][br_key]["br_status"]
    data["branch"][br_key]["br_status"] = 0
    components = PowerModels.calc_connected_components(data)
    data["branch"][br_key]["br_status"] = orig_status  # restore
    return length(components) > 1
end

function run(
    network_file::String=joinpath(
        @__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg10k.m"
    ),
)
    TIME_BUDGET = 600.0

    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    mem0 = maxrss()

    try
        # ---- Load and preprocess ----
        println("Loading MEDIUM network...")
        data = PowerModels.parse_file(network_file)
        n_rate, n_cost = apply_medium_preprocessing!(data)
        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        n_gens = length(data["gen"])
        println("Network: $n_buses buses, $n_branches branches, $n_gens generators")
        println("Preprocessing: $n_rate rate_a fixed, $n_cost costs linearized")

        results["details"]["num_buses"] = n_buses
        results["details"]["num_branches"] = n_branches
        results["details"]["num_generators"] = n_gens

        # Warm-up
        println("Warm-up solve...")
        _d = PowerModels.parse_file(
            joinpath(@__DIR__, "..", "..", "..", "..", "data", "networks", "case39.m")
        )
        for (_, gen) in _d["gen"]
            if gen["model"] == 2 && length(get(gen, "cost", [])) >= 3 && gen["cost"][1] != 0.0
                gen["cost"] = [gen["cost"][2], gen["cost"][3]]
                gen["ncost"] = 2
            end
        end
        _opt0 = optimizer_with_attributes(
            HiGHS.Optimizer, "output_flag" => false, "time_limit" => 60.0
        )
        PowerModels.solve_dc_opf(_d, _opt0)
        println("  Warm-up done.")

        baseMVA = data["baseMVA"]

        # Extract network topology
        gen_ids = sort(parse.(Int, collect(keys(data["gen"]))))
        bus_ids = sort(parse.(Int, collect(keys(data["bus"]))))
        branch_ids_all = sort(parse.(Int, collect(keys(data["branch"]))))

        # Find reference bus
        ref_bus = nothing
        for (id, bus) in data["bus"]
            if bus["bus_type"] == 3
                ref_bus = parse(Int, id)
                break
            end
        end
        println("Reference bus: $ref_bus")
        results["details"]["reference_bus"] = ref_bus

        # Generator parameters
        gen_bus = Dict(g => data["gen"][string(g)]["gen_bus"] for g in gen_ids)
        pmin_val = Dict(g => data["gen"][string(g)]["pmin"] for g in gen_ids)
        pmax_val = Dict(g => data["gen"][string(g)]["pmax"] for g in gen_ids)

        gen_cost_c1 = Dict{Int,Float64}()
        gen_cost_c0 = Dict{Int,Float64}()
        for g in gen_ids
            gd = data["gen"][string(g)]
            if gd["model"] == 2 && !isempty(gd["cost"])
                nc = gd["ncost"]
                if nc >= 2
                    gen_cost_c1[g] = gd["cost"][nc - 1]
                    gen_cost_c0[g] = gd["cost"][nc]
                else
                    gen_cost_c1[g] = 0.0
                    gen_cost_c0[g] = nc == 1 ? gd["cost"][1] : 0.0
                end
            else
                gen_cost_c1[g] = 0.0
                gen_cost_c0[g] = 0.0
            end
        end

        # Bus loads
        base_bus_load = Dict(b => 0.0 for b in bus_ids)
        for (_, load) in data["load"]
            bid = load["load_bus"]
            base_bus_load[bid] = get(base_bus_load, bid, 0.0) + load["pd"]
        end

        # Active branches
        active_branches = []
        for br_id in branch_ids_all
            br = data["branch"][string(br_id)]
            br["br_status"] == 0 && continue
            x = get(br, "br_x", 0.0)
            abs(x) < 1e-10 && continue
            rate = get(br, "rate_a", 9999.0)
            push!(active_branches, (id=br_id, f=br["f_bus"], t=br["t_bus"], b=1.0/x, rate=rate))
        end
        nab = length(active_branches)
        println("Active branches: $nab")

        bus_adj = Dict(b => Tuple{Int,Bool}[] for b in bus_ids)
        for (idx, ab) in enumerate(active_branches)
            push!(bus_adj[ab.f], (idx, true))
            push!(bus_adj[ab.t], (idx, false))
        end

        gens_at_bus = Dict(b => Int[] for b in bus_ids)
        for g in gen_ids
            b = gen_bus[g]
            haskey(gens_at_bus, b) && push!(gens_at_bus[b], g)
        end

        ab_id_to_idx = Dict(ab.id => idx for (idx, ab) in enumerate(active_branches))

        # HiGHS optimizer (fixed time_limit — don't reset on live model)
        highs_opt = optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => TIME_BUDGET,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => false,
        )

        # ---- Solve base-case DC OPF ----
        println("Solving base-case DC OPF (MEDIUM)...")
        t_base = time()
        base_result = PowerModels.solve_dc_opf(deepcopy(data), highs_opt)
        base_time = time() - t_base
        base_term = string(base_result["termination_status"])
        base_obj = get(base_result, "objective", NaN)
        println(
            "  Base OPF: $base_term, obj=$(round(base_obj, digits=2)), $(round(base_time, digits=2))s",
        )
        results["details"]["base_dcopf_termination"] = base_term
        results["details"]["base_dcopf_objective"] = round(base_obj; digits=2)
        results["details"]["base_dcopf_time_s"] = round(base_time; digits=2)

        if !(base_term in ["OPTIMAL", "LOCALLY_SOLVED"])
            push!(results["errors"], "Base DC OPF failed: $base_term")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # Select 50 most-loaded branches
        branch_loading = Dict{Int,Float64}()
        for ab in active_branches
            if ab.rate > 0 &&
                ab.rate < 1e6 &&
                haskey(base_result["solution"]["branch"], string(ab.id))
                pf = abs(get(base_result["solution"]["branch"][string(ab.id)], "pf", 0.0))
                branch_loading[ab.id] = pf / ab.rate
            end
        end
        sorted_loading = sort(collect(branch_loading); by=x -> x[2], rev=true)

        n_contingency_target = 50
        println(
            "Pre-screening contingencies (target: $n_contingency_target, in-place island check)..."
        )
        t_screen = time()
        contingencies = Int[]
        islanding_count = 0

        for (br_id, _) in sorted_loading
            length(contingencies) >= n_contingency_target && break
            if check_islanding_inplace!(data, br_id)
                islanding_count += 1
            else
                push!(contingencies, br_id)
            end
        end
        screen_time = time() - t_screen
        C = length(contingencies)
        println(
            "  Selected $C contingencies ($islanding_count islanding excluded) in $(round(screen_time, digits=2))s",
        )
        results["details"]["num_contingencies"] = C
        results["details"]["islanding_excluded"] = islanding_count
        results["details"]["screening_time_s"] = round(screen_time; digits=2)

        push!(
            results["workarounds"],
            "No native SCOPF in PowerModels.jl. Iterative preventive DC SCOPF via JuMP: " *
            "solve base-case LP OPF, check N-1 contingency flows via DCPF, " *
            "add violated contingency constraint blocks to model, repeat. " *
            "Island pre-screening uses in-place br_status toggle (no deepcopy) for speed.",
        )

        # ---- Build initial JuMP model (base case only) ----
        println("Building base-case JuMP model...")
        t_build = time()
        model = Model(highs_opt)

        @variable(model, pmin_val[g] <= pg[g in gen_ids] <= pmax_val[g])
        @variable(model, theta_base[b in bus_ids])
        fix(theta_base[ref_bus], 0.0; force=true)

        for b in bus_ids
            load_b = base_bus_load[b]
            flow_out = AffExpr(0.0)
            for (br_idx, is_from) in bus_adj[b]
                ab = active_branches[br_idx]
                if is_from
                    add_to_expression!(flow_out, ab.b, theta_base[ab.f])
                    add_to_expression!(flow_out, -ab.b, theta_base[ab.t])
                else
                    add_to_expression!(flow_out, -ab.b, theta_base[ab.f])
                    add_to_expression!(flow_out, ab.b, theta_base[ab.t])
                end
            end
            gen_sum = isempty(gens_at_bus[b]) ? AffExpr(0.0) : sum(pg[g] for g in gens_at_bus[b])
            @constraint(model, gen_sum - load_b == flow_out)
        end
        for (idx, ab) in enumerate(active_branches)
            if ab.rate > 0 && ab.rate < 1e6
                @constraint(model, ab.b * (theta_base[ab.f] - theta_base[ab.t]) <= ab.rate)
                @constraint(model, ab.b * (theta_base[ab.f] - theta_base[ab.t]) >= -ab.rate)
            end
        end
        @objective(model, Min, sum(gen_cost_c1[g] * pg[g] + gen_cost_c0[g] for g in gen_ids))
        build_time = time() - t_build
        println(
            "  Model built in $(round(build_time, digits=2))s: $(num_variables(model)) variables"
        )
        results["details"]["model_variables_initial"] = num_variables(model)

        # Track contingency blocks added
        theta_cont = Dict{Int,Any}()  # contingency br_id => angle vars

        benders_iterations = 0
        binding_contingencies = Set{Int}()
        scopf_obj = NaN
        scopf_term = "NOT_STARTED"
        converged_benders = false
        max_benders_iter = 15
        iter_history = Dict{Int,Any}()

        t_scopf_start = time()

        for iter in 1:max_benders_iter
            time_elapsed = time() - t0
            if time_elapsed > TIME_BUDGET - 10
                println(
                    "  Budget approaching ($(round(time_elapsed, digits=0))s elapsed) — stopping at iter $iter",
                )
                break
            end
            benders_iterations = iter

            # Solve current model
            t_iter = time()
            optimize!(model)
            iter_time = time() - t_iter

            term = string(termination_status(model))
            println("  Iter $iter: $term in $(round(iter_time, digits=2))s")

            if !(term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"])
                push!(results["errors"], "SCOPF solve failed at iter $iter: $term")
                scopf_term = term
                break
            end

            scopf_term = term
            scopf_obj = objective_value(model)
            pg_vals = Dict(g => value(pg[g]) for g in gen_ids)

            iter_history[iter] = Dict(
                "termination" => term,
                "objective" => round(scopf_obj; digits=2),
                "solve_time_s" => round(iter_time; digits=2),
            )

            # Check for N-1 violations using in-place DCPF
            n_violations_total = 0
            new_cont_added = 0

            for c_br_id in contingencies
                c_idx = get(ab_id_to_idx, c_br_id, 0)

                # Set dispatch in data, toggle branch status, run DCPF, restore
                for g in gen_ids
                    data["gen"][string(g)]["pg"] = pg_vals[g]
                end
                orig_status = data["branch"][string(c_br_id)]["br_status"]
                data["branch"][string(c_br_id)]["br_status"] = 0

                # Skip if islanding
                components = PowerModels.calc_connected_components(data)
                if length(components) > 1
                    data["branch"][string(c_br_id)]["br_status"] = orig_status
                    continue
                end

                pf_c = PowerModels.compute_dc_pf(data)
                data["branch"][string(c_br_id)]["br_status"] = orig_status  # restore immediately

                pf_c["termination_status"] != true && continue

                data_copy = deepcopy(data)
                data_copy["branch"][string(c_br_id)]["br_status"] = 0
                PowerModels.update_data!(data_copy, pf_c["solution"])
                flows_c = PowerModels.calc_branch_flow_dc(data_copy)

                violated = false
                for (idx2, ab2) in enumerate(active_branches)
                    idx2 == c_idx && continue
                    ab2.rate > 0 && ab2.rate < 1e6 || continue
                    pf_val = get(get(flows_c["branch"], string(ab2.id), Dict()), "pf", 0.0)
                    if abs(pf_val) > ab2.rate + 1e-4
                        violated = true
                        n_violations_total += 1
                        push!(binding_contingencies, c_br_id)
                    end
                end

                # Add full contingency block if violated and not yet in model
                if violated && !haskey(theta_cont, c_br_id)
                    new_cont_added += 1
                    theta_c = @variable(model, [b in bus_ids], base_name="tc$(c_br_id)")
                    fix(theta_c[ref_bus], 0.0; force=true)
                    theta_cont[c_br_id] = theta_c

                    for b in bus_ids
                        load_b = base_bus_load[b]
                        flow_out_c = AffExpr(0.0)
                        for (br_idx, is_from) in bus_adj[b]
                            br_idx == c_idx && continue
                            ab = active_branches[br_idx]
                            if is_from
                                add_to_expression!(flow_out_c, ab.b, theta_c[ab.f])
                                add_to_expression!(flow_out_c, -ab.b, theta_c[ab.t])
                            else
                                add_to_expression!(flow_out_c, -ab.b, theta_c[ab.f])
                                add_to_expression!(flow_out_c, ab.b, theta_c[ab.t])
                            end
                        end
                        gen_sum = if isempty(gens_at_bus[b])
                            AffExpr(0.0)
                        else
                            sum(pg[g] for g in gens_at_bus[b])
                        end
                        @constraint(model, gen_sum - load_b == flow_out_c)
                    end
                    for (idx2, ab2) in enumerate(active_branches)
                        idx2 == c_idx && continue
                        if ab2.rate > 0 && ab2.rate < 1e6
                            @constraint(
                                model, ab2.b * (theta_c[ab2.f] - theta_c[ab2.t]) <= ab2.rate
                            )
                            @constraint(
                                model, ab2.b * (theta_c[ab2.f] - theta_c[ab2.t]) >= -ab2.rate
                            )
                        end
                    end
                end
            end

            println(
                "  Iter $iter: $n_violations_total violations, $new_cont_added new contingency blocks added, obj=$(round(scopf_obj, digits=2))",
            )
            iter_history[iter]["n_violations"] = n_violations_total
            iter_history[iter]["new_blocks_added"] = new_cont_added

            if n_violations_total == 0
                converged_benders = true
                println("  Benders converged — no new violations!")
                break
            end
        end

        scopf_time = time() - t_scopf_start

        println("\n=== C-8 SCOPF SUMMARY ===")
        println("Benders iterations: $benders_iterations")
        println("Binding contingencies: $(length(binding_contingencies))")
        println("SCOPF objective: $(round(scopf_obj, digits=2))")
        println("Total SCOPF time: $(round(scopf_time, digits=2))s")
        println("Benders converged: $converged_benders")

        results["details"]["scopf_termination"] = scopf_term
        results["details"]["scopf_objective"] =
            isnan(scopf_obj) ? nothing : round(scopf_obj; digits=2)
        results["details"]["scopf_time_s"] = round(scopf_time; digits=2)
        results["details"]["benders_iterations"] = benders_iterations
        results["details"]["benders_converged"] = converged_benders
        results["details"]["binding_contingency_count"] = length(binding_contingencies)
        results["details"]["binding_contingency_ids"] = collect(binding_contingencies)
        results["details"]["iteration_history"] = iter_history
        results["details"]["approach"] = "Iterative Benders: base-case LP OPF + contingency constraint blocks added per violation"
        results["details"]["solver"] = "HiGHS (LP, linearized costs)"

        mem_peak_mb = maxrss() / (1024^2)
        results["details"]["peak_rss_mb"] = round(mem_peak_mb; digits=1)

        if scopf_term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"]
            results["status"] = "pass"
        else
            push!(results["errors"], "SCOPF final status: $scopf_term")
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

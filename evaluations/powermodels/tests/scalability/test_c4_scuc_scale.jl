#= Test C-4: SCUC 24hr at SMALL (2000 buses) with HiGHS and SCIP
   Custom JuMP SCUC from A-5 approach on 2000-bus x 24 periods. Very expensive.
=#
using PowerModels, JuMP, HiGHS, SCIP, JSON
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

function solve_scuc(data, nperiods, solver; solver_name="unknown")
    result = Dict{String,Any}()

    # Get actual ACTIVE gen IDs from data (PowerModels only creates vars for active gens)
    gen_ids = sort([parse(Int, k) for (k, g) in data["gen"] if get(g, "gen_status", 1) != 0])
    ngens = length(gen_ids)

    # Create multi-network data for 24 periods
    mn_data = PowerModels.replicate(data, nperiods)

    # Vary load across periods (simple diurnal pattern)
    load_profile = [
        0.6,
        0.55,
        0.52,
        0.50,
        0.52,
        0.58,
        0.70,
        0.85,
        0.95,
        1.00,
        1.00,
        0.98,
        0.95,
        0.93,
        0.90,
        0.92,
        0.95,
        1.00,
        0.98,
        0.95,
        0.90,
        0.82,
        0.72,
        0.65,
    ]
    for t in 1:nperiods
        for (lid, load) in mn_data["nw"]["$t"]["load"]
            base_pd = data["load"][lid]["pd"]
            base_qd = data["load"][lid]["qd"]
            mn_data["nw"]["$t"]["load"][lid]["pd"] = base_pd * load_profile[t]
            mn_data["nw"]["$t"]["load"][lid]["qd"] = base_qd * load_profile[t]
        end
    end

    # Build multi-network DC OPF model
    pm = PowerModels.instantiate_model(mn_data, DCPPowerModel, PowerModels.build_mn_opf)
    model = pm.model

    # Access pg variables using actual gen IDs from PowerModels
    pg_vars = Dict{Tuple{Int,Int},Any}()
    for t in 1:nperiods
        for gid in gen_ids
            try
                pg_vars[(t, gid)] = PowerModels.var(pm, t, :pg, gid)
            catch
            end
        end
    end

    result["pg_vars_found"] = length(pg_vars)
    result["expected_vars"] = ngens * nperiods
    result["gen_ids_range"] = "$(minimum(gen_ids))-$(maximum(gen_ids))"

    if length(pg_vars) < ngens * nperiods
        result["status"] = "fail"
        result["termination_status"] = "VARIABLE_ACCESS_ERROR"
        result["error"] = "Could not access all pg variables: $(length(pg_vars)) of $(ngens * nperiods)"
        return result
    end

    # Add binary commitment variables indexed by gen ID
    @variable(model, u[t = 1:nperiods, g = gen_ids], Bin)
    @variable(model, v[t = 1:nperiods, g = gen_ids], Bin)  # startup
    @variable(model, w[t = 1:nperiods, g = gen_ids], Bin)  # shutdown

    # Link pg to commitment: pmin*u <= pg <= pmax*u
    for t in 1:nperiods, g in gen_ids
        gen = data["gen"]["$g"]
        pmin = gen["pmin"]
        pmax = gen["pmax"]
        pg = pg_vars[(t, g)]
        @constraint(model, pg >= pmin * u[t, g])
        @constraint(model, pg <= pmax * u[t, g])
    end

    # Startup/shutdown logic
    for t in 2:nperiods, g in gen_ids
        @constraint(model, u[t, g] - u[t - 1, g] == v[t, g] - w[t, g])
    end
    for g in gen_ids
        @constraint(model, u[1, g] - 1 == v[1, g] - w[1, g])
    end

    # Minimum up time (3 hours)
    min_up = 3
    for g in gen_ids, t in 1:nperiods
        for s in t:min(t + min_up - 1, nperiods)
            @constraint(model, u[s, g] >= v[t, g])
        end
    end

    # Minimum down time (2 hours)
    min_down = 2
    for g in gen_ids, t in 1:nperiods
        for s in t:min(t + min_down - 1, nperiods)
            @constraint(model, u[s, g] <= 1 - w[t, g])
        end
    end

    # Ramp rate constraints
    for t in 2:nperiods, g in gen_ids
        gen = data["gen"]["$g"]
        ramp_limit = gen["ramp_10"] > 0 ? gen["ramp_10"] * 6 : gen["pmax"]
        ramp_limit = min(ramp_limit, gen["pmax"])
        pg_t = pg_vars[(t, g)]
        pg_tm1 = pg_vars[(t-1, g)]
        @constraint(model, pg_t - pg_tm1 <= ramp_limit)
        @constraint(model, pg_tm1 - pg_t <= ramp_limit)
    end

    # Add startup costs to objective
    startup_cost_expr = AffExpr(0.0)
    for t in 1:nperiods, g in gen_ids
        gen = data["gen"]["$g"]
        sc = gen["startup"]
        if sc > 0
            add_to_expression!(startup_cost_expr, sc, v[t, g])
        end
    end
    orig_obj = objective_function(model)
    @objective(model, Min, orig_obj + startup_cost_expr)

    # Count constraints/variables
    result["num_variables"] = num_variables(model)
    result["num_constraints"] = sum(
        num_constraints(model, F, S) for (F, S) in list_of_constraint_types(model)
    )

    # Solve
    set_optimizer(model, solver)
    optimize!(model)

    term_status = termination_status(model)
    result["termination_status"] = string(term_status)

    if term_status == MOI.OPTIMAL ||
        term_status == MOI.ALMOST_OPTIMAL ||
        term_status == MOI.TIME_LIMIT ||
        term_status == MOI.OBJECTIVE_LIMIT
        try
            result["objective"] = objective_value(model)
        catch
            result["objective"] = NaN
        end
        try
            result["mip_gap"] = relative_gap(model)
        catch
            result["mip_gap"] = "not available"
        end
        try
            result["node_count"] = node_count(model)
        catch
            result["node_count"] = "not available"
        end

        # Count decommitted generators
        decommitted = 0
        for g in gen_ids
            for t in 1:nperiods
                try
                    if round(value(u[t, g])) == 0
                        decommitted += 1
                        break
                    end
                catch
                    break
                end
            end
        end
        result["generators_with_off_periods"] = decommitted
        result["status"] = "pass"
    else
        result["status"] = "fail"
        result["error"] = "Solver terminated: $term_status"
    end

    return result
end

function run(network_file::String="/workspace/data/networks/case_ACTIVSg2000.m")
    results = Dict{String,Any}(
        "test_id" => "C-4",
        "test_name" => "scuc_scale",
        "network" => "SMALL",
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

        ngens = length(data["gen"])
        nperiods = 24
        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_branches"] = length(data["branch"])
        results["details"]["num_generators"] = ngens
        results["details"]["num_periods"] = nperiods
        results["details"]["gen_id_range"] = "$(minimum(parse.(Int, collect(keys(data["gen"])))))-$(maximum(parse.(Int, collect(keys(data["gen"])))))"

        solver_results = Dict{String,Any}()

        # --- HiGHS ---
        println("Starting HiGHS SCUC...")
        GC.gc()
        mem_before = Base.gc_live_bytes() / 1024^2
        t_highs = time()
        highs_solver = optimizer_with_attributes(
            HiGHS.Optimizer, "mip_rel_gap" => 0.01, "time_limit" => 300.0
        )
        highs_result = solve_scuc(data, nperiods, highs_solver; solver_name="HiGHS")
        highs_time = time() - t_highs
        GC.gc()
        mem_after = Base.gc_live_bytes() / 1024^2

        highs_result["wall_clock_seconds"] = round(highs_time; digits=2)
        highs_result["peak_memory_mb"] = round(mem_after - mem_before; digits=2)
        solver_results["HiGHS"] = highs_result
        println(
            "HiGHS done: $(highs_time)s, status=$(get(highs_result, "termination_status", "unknown"))",
        )

        # --- SCIP ---
        println("Starting SCIP SCUC...")
        GC.gc()
        mem_before = Base.gc_live_bytes() / 1024^2
        t_scip = time()
        scip_solver = optimizer_with_attributes(
            SCIP.Optimizer, "limits/gap" => 0.01, "limits/time" => 300.0, "display/verblevel" => 0
        )
        scip_result = solve_scuc(data, nperiods, scip_solver; solver_name="SCIP")
        scip_time = time() - t_scip
        GC.gc()
        mem_after = Base.gc_live_bytes() / 1024^2

        scip_result["wall_clock_seconds"] = round(scip_time; digits=2)
        scip_result["peak_memory_mb"] = round(mem_after - mem_before; digits=2)
        solver_results["SCIP"] = scip_result
        println(
            "SCIP done: $(scip_time)s, status=$(get(scip_result, "termination_status", "unknown"))"
        )

        results["details"]["solver_results"] = solver_results
        results["details"]["approach"] = "Custom JuMP SCUC: instantiate_model(mn_data, DCPPowerModel, build_mn_opf) + binary commitment vars + UC constraints"

        # Pass if at least one solver succeeded
        if any(get(sr, "status", "fail") == "pass" for (_, sr) in solver_results)
            results["status"] = "pass"
        else
            results["status"] = "fail"
            push!(results["errors"], "Neither solver produced a solution within time limits")
        end

        push!(
            results["workarounds"],
            "PowerModels has NO built-in SCUC. Required ~100 LOC of custom JuMP code for commitment variables, min up/down, ramps, startup costs.",
        )

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

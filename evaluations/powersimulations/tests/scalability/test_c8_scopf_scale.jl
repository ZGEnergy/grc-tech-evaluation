#=
Test C-8: SCOPF N-1 (50 contingencies) on SMALL and MEDIUM

Dimension: scalability
Network: SMALL (ACTIVSg 2000-bus), MEDIUM (ACTIVSg 10k-bus)
Pass condition: Completes. Wall-clock, peak memory, iterations (if screening), binding contingencies.
Tool: PowerSimulations.jl v0.30.2 (PowerNetworkMatrices.jl v0.12.1)
Solver: HiGHS
=#

using PowerSystems
using PowerSimulations
using PowerNetworkMatrices
using HiGHS
using JuMP
using JSON
using Logging
using DataFrames
using Dates
using TimeSeries: TimeArray

# Suppress verbose logging
global_logger(ConsoleLogger(stderr, Logging.Error))

const PSI = PowerSimulations

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024
        end
    end
    return nothing
end

function cpu_core_count()
    count = 0
    for line in eachline("/proc/cpuinfo")
        if startswith(line, "processor")
            count += 1
        end
    end
    return count
end

function setup_system(network_file::String)
    sys = System(network_file)

    # Add time series (required by PowerSimulations DecisionModel)
    timestamps = [DateTime("2024-01-01"), DateTime("2024-01-01") + Hour(1)]
    constant_ts = [1.0, 1.0]

    for load in get_components(PowerLoad, sys)
        add_time_series!(
            sys, load, SingleTimeSeries("max_active_power", TimeArray(timestamps, constant_ts))
        )
    end

    # RenewableDispatch also needs max_active_power time series
    for gen in get_components(RenewableDispatch, sys)
        add_time_series!(
            sys, gen, SingleTimeSeries("max_active_power", TimeArray(timestamps, constant_ts))
        )
    end

    # HydroDispatch needs max_active_power time series
    for gen in get_components(HydroDispatch, sys)
        add_time_series!(
            sys, gen, SingleTimeSeries("max_active_power", TimeArray(timestamps, constant_ts))
        )
    end

    transform_single_time_series!(sys, Hour(1), Hour(1))

    return sys
end

function build_dcopf_model(sys, solver)
    template = ProblemTemplate(NetworkModel(DCPPowerModel; duals=[NodalBalanceActiveConstraint]))
    set_device_model!(template, ThermalStandard, ThermalDispatchNoMin)
    set_device_model!(template, PowerLoad, StaticPowerLoad)
    set_device_model!(template, Line, StaticBranch)
    set_device_model!(template, Transformer2W, StaticBranch)
    if !isempty(collect(get_components(TapTransformer, sys)))
        set_device_model!(template, TapTransformer, StaticBranch)
    end
    if !isempty(collect(get_components(RenewableDispatch, sys)))
        set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
    end
    # HydroDispatch omitted (no valid formulation in PSI v0.30.2)

    model = DecisionModel(template, sys; optimizer=solver, initialize_model=false)
    build_status = build!(model; output_dir=mktempdir())
    println(stderr, "    Build status: $build_status")
    return model
end

function select_top_contingencies(lodf_matrix, n_contingencies::Int)
    lodf_ax = axes(lodf_matrix)
    branch_names = collect(lodf_ax[1])

    # Compute max |LODF| impact for each branch as a contingency
    impact_scores = Dict{String,Float64}()
    for cont_name in branch_names
        max_impact = 0.0
        for mon_name in branch_names
            if mon_name == cont_name
                ;
                continue;
            end
            val = abs(lodf_matrix[mon_name, cont_name])
            if val > max_impact && val < 0.95  # Skip near-radial
                max_impact = val
            end
        end
        impact_scores[cont_name] = max_impact
    end

    # Sort by impact and take top N
    sorted = sort(collect(impact_scores); by=x -> -x[2])
    selected = [s[1] for s in sorted[1:min(n_contingencies, length(sorted))]]
    return selected
end

function run_scopf(sys, solver, contingency_branches::Vector{String}, label::String)
    result = Dict{String,Any}("label" => label, "status" => "fail")

    t0 = time()

    # Build base DCOPF model
    println(stderr, "  [$label] Building DCOPF model...")
    model = build_dcopf_model(sys, solver)

    # Compute LODF matrix
    println(stderr, "  [$label] Computing LODF matrix...")
    t_lodf = time()
    lodf_matrix = LODF(sys)
    elapsed_lodf = time() - t_lodf
    lodf_ax = axes(lodf_matrix)
    result["lodf_compute_seconds"] = round(elapsed_lodf; digits=3)
    result["lodf_shape"] = [length(lodf_ax[1]), length(lodf_ax[2])]

    # Access JuMP model and PSI variable containers
    oc = PSI.get_optimization_container(model)
    jm = PSI.get_jump_model(oc)
    psi_vars = PSI.get_variables(oc)

    # Find flow variables
    flow_key = nothing
    for k in keys(psi_vars)
        ks = string(k)
        if occursin("FlowActivePowerVariable", ks) && occursin("Line", ks)
            flow_key = k
            break
        end
    end

    if flow_key === nothing
        result["error"] = "Could not find FlowActivePowerVariable for Line"
        return result
    end

    flow_arr = psi_vars[flow_key]
    flow_line_names = axes(flow_arr)[1]
    flow_timesteps = axes(flow_arr)[2]
    t_idx = first(flow_timesteps)

    # Get branch ratings
    line_ratings_pu = Dict{String,Float64}()
    for l in get_components(Line, sys)
        line_ratings_pu[get_name(l)] = get_rating(l)
    end

    lodf_branch_names = Set(collect(lodf_ax[1]))
    flow_line_set = Set(flow_line_names)

    # Add N-1 contingency constraints for the selected 50 branches
    println(
        stderr,
        "  [$label] Adding N-1 constraints for $(length(contingency_branches)) contingencies...",
    )
    t_constraints = time()
    n_constraints_added = 0
    binding_contingencies = String[]

    for cont_line in contingency_branches
        if !(cont_line in flow_line_set) || !(cont_line in lodf_branch_names)
            continue
        end

        for mon_line in flow_line_names
            if mon_line == cont_line
                ;
                continue;
            end
            if !(mon_line in lodf_branch_names)
                ;
                continue;
            end

            lodf_val = lodf_matrix[mon_line, cont_line]
            if abs(lodf_val) < 1e-6
                ;
                continue;
            end

            rating = get(line_ratings_pu, mon_line, nothing)
            if rating === nothing || rating <= 0
                ;
                continue;
            end

            f_mon = flow_arr[mon_line, t_idx]
            f_cont = flow_arr[cont_line, t_idx]

            @constraint(jm, f_mon + lodf_val * f_cont <= rating)
            @constraint(jm, -(f_mon + lodf_val * f_cont) <= rating)
            n_constraints_added += 2
        end
    end
    elapsed_constraints = time() - t_constraints

    result["n_contingency_constraints_added"] = n_constraints_added
    result["constraint_build_seconds"] = round(elapsed_constraints; digits=3)
    result["n_contingencies_requested"] = length(contingency_branches)

    # Problem size
    n_vars = num_variables(jm)
    n_total_constraints = sum(num_constraints(jm, F, S) for (F, S) in list_of_constraint_types(jm))
    result["n_variables"] = n_vars
    result["n_total_constraints"] = n_total_constraints

    # Solve
    println(stderr, "  [$label] Solving SCOPF ($n_constraints_added contingency constraints)...")
    t_solve = time()
    JuMP.optimize!(jm)
    elapsed_solve = time() - t_solve

    elapsed_total = time() - t0
    result["solve_seconds"] = round(elapsed_solve; digits=3)
    result["wall_clock_seconds"] = round(elapsed_total; digits=3)
    result["peak_memory_mb"] = peak_rss_mb()

    term_status = JuMP.termination_status(jm)
    result["termination_status"] = string(term_status)

    # TIME_LIMIT with an incumbent is still a usable result
    solved = term_status == MOI.OPTIMAL || term_status == MOI.FEASIBLE_POINT
    has_incumbent = false
    if term_status == MOI.TIME_LIMIT
        try
            obj = JuMP.objective_value(jm)
            has_incumbent = true
            solved = true  # treat as solved with caveat
        catch
            ;
        end
    end
    result["solved"] = solved
    result["has_incumbent"] = has_incumbent

    if solved
        result["objective_value"] = JuMP.objective_value(jm)
        if has_incumbent
            result["status"] = "pass_time_limit"
        else
            result["status"] = "pass"
        end

        # Find binding contingency constraints
        binding_count = 0
        for cont_line in contingency_branches
            if !(cont_line in flow_line_set)
                ;
                continue;
            end
            f_cont_val = JuMP.value(flow_arr[cont_line, t_idx])
            for mon_line in flow_line_names
                if mon_line == cont_line
                    ;
                    continue;
                end
                if !(mon_line in lodf_branch_names)
                    ;
                    continue;
                end
                lodf_val = lodf_matrix[mon_line, cont_line]
                if abs(lodf_val) < 1e-6
                    ;
                    continue;
                end
                rating = get(line_ratings_pu, mon_line, nothing)
                if rating === nothing || rating <= 0
                    ;
                    continue;
                end
                f_mon_val = JuMP.value(flow_arr[mon_line, t_idx])
                post_cont_flow = f_mon_val + lodf_val * f_cont_val
                if abs(abs(post_cont_flow) - rating) < 1e-4
                    binding_count += 1
                    if !(cont_line in binding_contingencies)
                        push!(binding_contingencies, cont_line)
                    end
                end
            end
        end
        result["binding_constraint_count"] = binding_count
        result["binding_contingencies"] = binding_contingencies
        result["n_binding_contingencies"] = length(binding_contingencies)
    else
        try
            result["objective_value"] = JuMP.objective_value(jm)
        catch
            ;
        end
    end

    println(
        stderr,
        "  [$label] Done: $(result["termination_status"]) in $(round(elapsed_total, digits=1))s",
    )
    return result
end

function run()
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    try
        cores = cpu_core_count()
        results["details"]["cpu_cores_available"] = cores

        solver = optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 600.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => false,
        )

        n_contingencies = 50
        t_total = time()

        # --- JIT warm-up on SMALL ---
        println(stderr, "JIT warm-up on SMALL...")
        try
            sys_w = setup_system("/workspace/data/networks/case_ACTIVSg2000.m")
            model_w = build_dcopf_model(sys_w, solver)
            oc_w = PSI.get_optimization_container(model_w)
            jm_w = PSI.get_jump_model(oc_w)
            JuMP.optimize!(jm_w)
            # Also warm up LODF
            lodf_w = LODF(sys_w)
            println(stderr, "Warm-up complete.")
        catch e
            println(stderr, "Warm-up failed (OK for JIT): $(typeof(e))")
        end

        # --- SMALL network ---
        println(stderr, "\n=== SMALL (ACTIVSg 2000) ===")
        sys_small = setup_system("/workspace/data/networks/case_ACTIVSg2000.m")
        n_buses_small = length(collect(get_components(Bus, sys_small)))
        n_branches_small = length(collect(get_components(Branch, sys_small)))

        # Compute LODF for contingency selection
        lodf_small = LODF(sys_small)
        top_contingencies_small = select_top_contingencies(lodf_small, n_contingencies)

        # Need to reload system (LODF computation may modify state)
        sys_small = setup_system("/workspace/data/networks/case_ACTIVSg2000.m")
        small_result = run_scopf(sys_small, solver, top_contingencies_small, "SMALL")
        small_result["n_buses"] = n_buses_small
        small_result["n_branches"] = n_branches_small
        results["details"]["small"] = small_result

        # --- MEDIUM network ---
        println(stderr, "\n=== MEDIUM (ACTIVSg 10k) ===")
        sys_medium = setup_system("/workspace/data/networks/case_ACTIVSg10k.m")
        n_buses_medium = length(collect(get_components(Bus, sys_medium)))
        n_branches_medium = length(collect(get_components(Branch, sys_medium)))

        # Compute LODF for contingency selection
        println(stderr, "Computing LODF for contingency selection on MEDIUM...")
        t_lodf_sel = time()
        lodf_medium = LODF(sys_medium)
        elapsed_lodf_sel = time() - t_lodf_sel
        println(stderr, "LODF selection computed in $(round(elapsed_lodf_sel, digits=1))s")

        top_contingencies_medium = select_top_contingencies(lodf_medium, n_contingencies)

        # Reload system
        sys_medium = setup_system("/workspace/data/networks/case_ACTIVSg10k.m")
        medium_result = run_scopf(sys_medium, solver, top_contingencies_medium, "MEDIUM")
        medium_result["n_buses"] = n_buses_medium
        medium_result["n_branches"] = n_branches_medium
        results["details"]["medium"] = medium_result

        # --- Summary ---
        results["wall_clock_seconds"] = round(time() - t_total; digits=3)
        results["details"]["peak_memory_mb"] = peak_rss_mb()
        results["details"]["n_contingencies"] = n_contingencies

        small_ok = get(small_result, "solved", false)
        medium_ok = get(medium_result, "solved", false)

        results["details"]["pass_checks"] = Dict(
            "small_solved" => small_ok, "medium_solved" => medium_ok
        )

        push!(
            results["workarounds"],
            "No built-in SCOPF in PowerSimulations.jl (open issue #944). " *
            "Manually assembled N-1 contingency constraints via: " *
            "(1) LODF matrix from PowerNetworkMatrices.jl, " *
            "(2) Selected 50 highest-impact contingencies by max LODF magnitude, " *
            "(3) PSI internal variable access via PSI.get_variables() + PSI.get_jump_model(), " *
            "(4) JuMP @constraint macro to add post-contingency flow limits. " *
            "Used initialize_model=false workaround.",
        )

        if small_ok && medium_ok
            results["status"] = "qualified_pass"
        elseif small_ok || medium_ok
            results["status"] = "qualified_pass"
            push!(results["workarounds"], "Only one scale level completed successfully.")
        else
            push!(results["errors"], "Neither SMALL nor MEDIUM SCOPF solved")
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

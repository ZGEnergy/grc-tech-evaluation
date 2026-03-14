#=
Test C-4: SCUC 24hr on SMALL with HiGHS and SCIP

Dimension: scalability
Network: SMALL (ACTIVSg 2000-bus, 544 generators)
Pass condition: Completes. Wall-clock per solver, MIP gap at termination, peak memory.
Tool: PowerSimulations.jl v0.30.2
=#

using PowerSystems
using PowerSimulations
using HiGHS
using SCIP
using JuMP
using JSON
using Logging
using Dates
using TimeSeries: TimeArray

# Suppress verbose logging
global_logger(ConsoleLogger(stderr, Logging.Error))

const PSI = PowerSimulations

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024  # kB to MB
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

# Hourly load profile factors (24 hours, typical daily shape)
# Valley at ~0.65 around HR4, peak at ~1.0 around HR18
const HOURLY_FACTORS = [
    0.72,
    0.68,
    0.66,
    0.65,
    0.67,
    0.70,   # HR1-6  (night valley)
    0.75,
    0.82,
    0.88,
    0.92,
    0.95,
    0.96,   # HR7-12 (morning ramp)
    0.97,
    0.98,
    0.99,
    1.00,
    1.00,
    1.00,   # HR13-18 (afternoon peak)
    0.98,
    0.95,
    0.90,
    0.85,
    0.80,
    0.75,   # HR19-24 (evening decline)
]

function setup_scuc_system(network_file::String)
    sys = System(network_file)
    base_power = get_base_power(sys)

    # Classify generators by marginal cost quartiles for cost differentiation
    # Collect all thermal generators with their costs
    gen_costs = Tuple{ThermalStandard,Float64}[]
    for gen in get_components(ThermalStandard, sys)
        cost = get_operation_cost(gen)
        # Extract marginal cost from cost curve
        mc = 0.0
        if cost !== nothing
            vc = get_variable(cost)
            if vc !== nothing
                cc = get_function_data(get_value_curve(vc))
                if cc isa LinearFunctionData
                    mc = get_proportional_term(cc)
                elseif cc isa QuadraticFunctionData
                    mc = get_proportional_term(cc)
                end
            end
        end
        push!(gen_costs, (gen, mc))
    end

    # Sort by marginal cost to find quartiles
    sort!(gen_costs; by=x -> x[2])
    n_gens = length(gen_costs)
    q1 = n_gens ÷ 4
    q2 = n_gens ÷ 2
    q3 = 3 * n_gens ÷ 4

    # Apply differentiated costs by quartile
    for (i, (gen, _mc)) in enumerate(gen_costs)
        if i <= q1
            # Baseload (cheapest) — $10/MWh, low startup, high min-up
            c1 = 10.0
            startup = 5000.0
            no_load = 50.0
            min_up = 8.0
            min_down = 6.0
            pmin_frac = 0.5
        elseif i <= q2
            # Intermediate-low — $20/MWh
            c1 = 20.0
            startup = 3000.0
            no_load = 30.0
            min_up = 4.0
            min_down = 4.0
            pmin_frac = 0.4
        elseif i <= q3
            # Intermediate-high — $35/MWh
            c1 = 35.0
            startup = 2000.0
            no_load = 20.0
            min_up = 2.0
            min_down = 2.0
            pmin_frac = 0.3
        else
            # Peakers (most expensive) — $55/MWh, low startup, flexible
            c1 = 55.0
            startup = 1000.0
            no_load = 10.0
            min_up = 1.0
            min_down = 1.0
            pmin_frac = 0.2
        end

        # Set costs (linear only — HiGHS can't do MIQP)
        set_operation_cost!(
            gen, ThermalGenerationCost(
                CostCurve(LinearCurve(c1)),
                no_load,
                startup,
                0.0,  # shutdown cost
            )
        )

        # Set Pmin for UC
        pmax = get_active_power_limits(gen).max
        pmin = pmin_frac * pmax
        if pmin > 0.0 && pmax > pmin
            set_active_power_limits!(gen, (min=pmin, max=pmax))
        end

        # Set ramp limits (pu/min — allow ~50% of capacity per hour = ~0.83%/min)
        ramp_pu = 0.5 * pmax / 60.0
        if ramp_pu > 0.0
            set_ramp_limits!(gen, (up=ramp_pu, down=ramp_pu))
        end

        # Set time limits
        set_time_limits!(gen, (up=min_up, down=min_down))

        # Fix initial conditions
        set_status!(gen, true)
        set_time_at_status!(gen, 999.0)

        # Ensure initial power within limits
        current_p = get_active_power(gen)
        if current_p > pmax
            set_active_power!(gen, pmax * 0.8)
        elseif current_p < pmin
            set_active_power!(gen, (pmin + pmax) / 2.0)
        end
    end

    # Create 24-hour time series for all components that PSI requires them for
    start_time = DateTime("2024-01-01")
    timestamps = [start_time + Hour(h-1) for h in 1:25]  # 25 points for 24 intervals
    multipliers = vcat(HOURLY_FACTORS, [HOURLY_FACTORS[end]])  # 25 points
    constant_ts = ones(25)

    for load in get_components(PowerLoad, sys)
        add_time_series!(
            sys, load, SingleTimeSeries("max_active_power", TimeArray(timestamps, multipliers))
        )
    end

    # RenewableDispatch needs max_active_power time series
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

    transform_single_time_series!(sys, Hour(24), Hour(1))

    return sys, n_gens
end

function build_and_solve_scuc(sys, solver)
    template = ProblemTemplate(NetworkModel(DCPPowerModel; duals=[NodalBalanceActiveConstraint]))
    set_device_model!(template, ThermalStandard, ThermalStandardUnitCommitment)
    set_device_model!(template, PowerLoad, StaticPowerLoad)
    set_device_model!(template, Line, StaticBranch)
    set_device_model!(template, Transformer2W, StaticBranch)
    # TapTransformer not present in ACTIVSg2000, add only if present
    if !isempty(collect(get_components(TapTransformer, sys)))
        set_device_model!(template, TapTransformer, StaticBranch)
    end

    # Handle RenewableDispatch if present (ACTIVSg2000 has 109 renewable gens)
    if !isempty(collect(get_components(RenewableDispatch, sys)))
        set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
    end
    # HydroDispatch: PSI v0.30.2 doesn't export hydro formulations.
    # Omitting from template — PSI will ignore unmodeled device types in the DC network model.

    model = DecisionModel(template, sys; optimizer=solver, initialize_model=false)
    build!(model; output_dir=mktempdir())

    # Use JuMP.optimize! directly (PSI solve! requires initialization which fails with HiGHS)
    oc = PSI.get_optimization_container(model)
    jm = PSI.get_jump_model(oc)
    JuMP.optimize!(jm)

    return model
end

function extract_solver_results(model)
    oc = PSI.get_optimization_container(model)
    jm = PSI.get_jump_model(oc)

    term_status = termination_status(jm)
    obj_val = nothing
    mip_gap = nothing
    try
        obj_val = objective_value(jm)
    catch
        ;
    end
    try
        mip_gap = relative_gap(jm)
    catch
        ;
    end

    # Count variables
    n_vars = num_variables(jm)
    n_binary = count(is_binary, all_variables(jm))
    n_constraints = sum(num_constraints(jm, F, S) for (F, S) in list_of_constraint_types(jm))

    # Extract commitment schedule for cycling analysis
    psi_vars = PSI.get_variables(oc)
    on_key = nothing
    for k in keys(psi_vars)
        if occursin("OnVariable", string(k)) && occursin("ThermalStandard", string(k))
            on_key = k
            break
        end
    end

    num_cycling = 0
    if on_key !== nothing
        on_arr = psi_vars[on_key]
        gen_names = sort(axes(on_arr)[1])
        timesteps = axes(on_arr)[2]
        for gname in gen_names
            schedule = [Int(round(JuMP.value(on_arr[gname, t]))) for t in timesteps]
            transitions = sum(abs.(diff(schedule)))
            if transitions >= 1
                num_cycling += 1
            end
        end
    end

    return Dict(
        "termination_status" => string(term_status),
        "objective_value" => obj_val,
        "mip_gap" => mip_gap !== nothing ? round(mip_gap; digits=6) : nothing,
        "n_variables" => n_vars,
        "n_binary_variables" => n_binary,
        "n_constraints" => n_constraints,
        "num_cycling_generators" => num_cycling,
        "solved" => (term_status == MOI.OPTIMAL || term_status == MOI.FEASIBLE_POINT),
    )
end

function run(network_file::String="/workspace/data/networks/case_ACTIVSg2000.m")
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

        # --- HiGHS solver ---
        highs_solver = optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 600.0,   # 10 min for SMALL scale
            "mip_rel_gap" => 0.01,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => true,    # Enable for diagnostics
        )

        # JIT warm-up: build system once (partial — just load and configure)
        println(stderr, "Setting up system for JIT warm-up...")
        sys_warmup, n_gens_warmup = setup_scuc_system(network_file)
        println(stderr, "System loaded: $(n_gens_warmup) thermal generators")

        # Full warm-up solve (may be slow or fail, that's OK — JIT compilation happens)
        println(stderr, "JIT warm-up solve (may take a while)...")
        try
            build_and_solve_scuc(sys_warmup, highs_solver)
            println(stderr, "Warm-up complete.")
        catch e
            println(stderr, "Warm-up failed (OK for JIT): $(typeof(e))")
        end

        mem_before_highs = peak_rss_mb()

        # --- Timed HiGHS solve ---
        println(stderr, "Starting timed HiGHS solve...")
        sys_highs, n_gens = setup_scuc_system(network_file)
        base_power = get_base_power(sys_highs)

        t0_highs = time()
        model_highs = build_and_solve_scuc(sys_highs, highs_solver)
        elapsed_highs = time() - t0_highs

        mem_after_highs = peak_rss_mb()

        highs_results = extract_solver_results(model_highs)
        highs_results["wall_clock_seconds"] = round(elapsed_highs; digits=3)
        highs_results["peak_memory_mb"] = mem_after_highs

        results["details"]["highs"] = highs_results
        results["details"]["n_thermal_generators"] = n_gens
        results["details"]["base_power_mva"] = base_power

        println(
            stderr,
            "HiGHS done: $(highs_results["termination_status"]) in $(round(elapsed_highs, digits=1))s",
        )

        # --- SCIP solver ---
        println(stderr, "Starting timed SCIP solve...")
        scip_solver = optimizer_with_attributes(
            SCIP.Optimizer,
            "limits/time" => 600.0,
            "limits/gap" => 0.01,
            "display/verblevel" => 0,
            "lp/threads" => 1,
        )

        sys_scip, _ = setup_scuc_system(network_file)

        t0_scip = time()
        model_scip = build_and_solve_scuc(sys_scip, scip_solver)
        elapsed_scip = time() - t0_scip

        mem_after_scip = peak_rss_mb()

        scip_results = extract_solver_results(model_scip)
        scip_results["wall_clock_seconds"] = round(elapsed_scip; digits=3)
        scip_results["peak_memory_mb"] = mem_after_scip

        results["details"]["scip"] = scip_results

        println(
            stderr,
            "SCIP done: $(scip_results["termination_status"]) in $(round(elapsed_scip, digits=1))s",
        )

        # --- Summary ---
        results["details"]["wall_clock_per_solver"] = Dict(
            "highs_seconds" => round(elapsed_highs; digits=3),
            "scip_seconds" => round(elapsed_scip; digits=3),
        )
        results["wall_clock_seconds"] = round(elapsed_highs + elapsed_scip; digits=3)
        results["details"]["peak_memory_mb"] = mem_after_scip  # peak over whole run

        # Pass condition: at least one solver completes
        highs_solved = highs_results["solved"]
        scip_solved = scip_results["solved"]

        results["details"]["pass_checks"] = Dict(
            "highs_solved" => highs_solved,
            "scip_solved" => scip_solved,
            "either_solved" => highs_solved || scip_solved,
        )

        push!(
            results["workarounds"],
            "Used initialize_model=false and JuMP.optimize!() directly (same workaround as A-5). " *
            "PSI initialization model fails with both HiGHS and SCIP on SMALL-scale SCUC.",
        )

        if highs_solved || scip_solved
            results["status"] = "qualified_pass"
        else
            push!(
                results["errors"],
                "Neither HiGHS nor SCIP produced a feasible solution within time limit",
            )
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

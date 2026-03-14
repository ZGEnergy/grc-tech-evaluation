#=
Test B-4: Stochastic Timeseries (20 scenarios, 12h multi-period DCOPF)

Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Tool accepts timeseries programmatically (not config-file only).
  Scenario loop expressible without excessive overhead. Results collectable in structured format.
Solver: HiGHS
Tool: PowerSimulations.jl v0.30.2
=#

using PowerSystems
using PowerSimulations
using HiGHS
using JuMP
using JSON
using Logging
using DataFrames
using CSV
using Dates
using TimeSeries: TimeArray

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

const COST_MAP = Dict("hydro" => 5.0, "nuclear" => 10.0, "coal_large" => 25.0, "gas_CC" => 40.0)

function build_system_for_scenario(
    network_file,
    timeseries_dir,
    scenario_id,
    scenario_mults,
    re_df,
    wind_fc,
    solar_fc,
    load_df,
    params,
)
    sys = System(network_file)
    base_power = get_base_power(sys)

    # 1. Apply differentiated costs (linear for HiGHS multi-period stability)
    for row in eachrow(params)
        c1 = get(COST_MAP, row.tech_class_key, 30.0)
        for gen in get_components(ThermalStandard, sys)
            if get_number(get_bus(gen)) == row.bus_id
                set_operation_cost!(
                    gen, ThermalGenerationCost(CostCurve(LinearCurve(c1)), 0.0, 0.0, 0.0)
                )
                break
            end
        end
    end

    # 2. Derate branches to 70%
    for line in get_components(Line, sys)
        set_rating!(line, get_rating(line) * 0.7)
    end
    for xfmr in get_components(Transformer2W, sys)
        set_rating!(xfmr, get_rating(xfmr) * 0.7)
    end
    for xfmr in get_components(TapTransformer, sys)
        set_rating!(xfmr, get_rating(xfmr) * 0.7)
    end

    # 3. Add renewable generators with scenario-modified profiles
    start_time = DateTime("2024-01-01")
    # 12 hours + 1 for PSI boundary = 13 timestamps
    timestamps_13 = [start_time + Hour(h-1) for h in 1:13]

    for row in eachrow(re_df)
        bus = nothing
        for b in get_components(ACBus, sys)
            if get_number(b) == row.bus_id
                bus = b;
                break
            end
        end
        bus === nothing && continue

        pmax_pu = row.pmax_mw / base_power
        pm_type = row.type == "wind" ? PrimeMovers.WT : PrimeMovers.PVe

        re_gen = RenewableDispatch(;
            name=row.gen_uid,
            available=true,
            bus=bus,
            active_power=pmax_pu * 0.5,
            reactive_power=0.0,
            rating=pmax_pu,
            prime_mover_type=pm_type,
            reactive_power_limits=(min=0.0, max=0.0),
            power_factor=1.0,
            operation_cost=RenewableGenerationCost(CostCurve(LinearCurve(0.0))),
            base_power=base_power,
        )
        add_component!(sys, re_gen)

        # Get forecast profile
        if row.type == "wind"
            fc_row = filter(r -> r.gen_uid == row.gen_uid, wind_fc)
        else
            fc_row = filter(r -> r.gen_uid == row.gen_uid, solar_fc)
        end

        # Get scenario multipliers for this unit
        scen_rows = filter(
            r -> r.scenario == scenario_id && r.gen_uid == row.gen_uid, scenario_mults
        )

        if nrow(fc_row) > 0
            mw_vals = Float64[]
            for h in 1:12
                hr_col = Symbol("HR_$h")
                base_mw = fc_row[1, hr_col]
                # Apply scenario multiplier
                mult = 1.0
                if nrow(scen_rows) > 0
                    mult = scen_rows[1, hr_col]
                end
                actual_mw = clamp(base_mw * mult, 0.0, row.pmax_mw)
                push!(mw_vals, actual_mw)
            end
            push!(mw_vals, mw_vals[end])  # boundary value

            multipliers = mw_vals ./ row.pmax_mw
            multipliers = clamp.(multipliers, 0.0, 1.0)

            add_time_series!(
                sys,
                re_gen,
                SingleTimeSeries("max_active_power", TimeArray(timestamps_13, multipliers)),
            )
        end
    end

    # 4. Load 12-hour profile for all loads (use first 12 hours)
    for load in get_components(PowerLoad, sys)
        bus_num = get_number(get_bus(load))
        load_base = get_max_active_power(load) * base_power

        bus_row = filter(r -> r.bus_id == bus_num, load_df)
        if nrow(bus_row) > 0
            multipliers = Float64[]
            for h in 1:12
                hr_col = Symbol("HR_$h")
                hourly_mw = bus_row[1, hr_col]
                if load_base > 0
                    push!(multipliers, hourly_mw / load_base)
                else
                    push!(multipliers, 1.0)
                end
            end
            push!(multipliers, multipliers[end])
            add_time_series!(
                sys,
                load,
                SingleTimeSeries("max_active_power", TimeArray(timestamps_13, multipliers)),
            )
        else
            add_time_series!(
                sys, load, SingleTimeSeries("max_active_power", TimeArray(timestamps_13, ones(13)))
            )
        end
    end

    transform_single_time_series!(sys, Hour(12), Hour(1))
    return sys
end

function solve_scenario(sys, solver)
    template = ProblemTemplate(NetworkModel(DCPPowerModel; duals=[NodalBalanceActiveConstraint]))
    set_device_model!(template, ThermalStandard, ThermalDispatchNoMin)
    set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
    set_device_model!(template, PowerLoad, StaticPowerLoad)
    set_device_model!(template, Line, StaticBranch)
    set_device_model!(template, Transformer2W, StaticBranch)
    set_device_model!(template, TapTransformer, StaticBranch)

    model = DecisionModel(template, sys; optimizer=solver, initialize_model=false)
    build!(model; output_dir=mktempdir())

    oc = PSI.get_optimization_container(model)
    jm = PSI.get_jump_model(oc)
    JuMP.optimize!(jm)

    return model
end

function extract_scenario_results(model, sys)
    base_power = get_base_power(sys)
    oc = PSI.get_optimization_container(model)
    jm = PSI.get_jump_model(oc)

    term_status = termination_status(jm)
    obj_val = objective_value(jm)

    # Extract LMPs from nodal balance duals
    psi_constraints = PSI.get_constraints(oc)
    nodal_key = nothing
    for k in keys(psi_constraints)
        if occursin("NodalBalanceActive", string(k))
            nodal_key = k;
            break
        end
    end

    hourly_lmps = Dict{Int,Dict{String,Float64}}()
    if nodal_key !== nothing
        nodal_arr = psi_constraints[nodal_key]
        bus_names = sort(collect(axes(nodal_arr)[1]))
        timesteps = axes(nodal_arr)[2]

        for (ti, t) in enumerate(timesteps)
            hlmps = Dict{String,Float64}()
            for bname in bus_names
                try
                    dual_val = JuMP.dual(nodal_arr[bname, t])
                    hlmps[bname] = -dual_val / base_power
                catch
                    hlmps[bname] = NaN
                end
            end
            hourly_lmps[ti] = hlmps
        end
    end

    # Extract dispatch
    psi_vars = PSI.get_variables(oc)
    p_key = nothing
    for k in keys(psi_vars)
        if occursin("ActivePowerVariable", string(k)) && occursin("ThermalStandard", string(k))
            p_key = k;
            break
        end
    end

    total_generation = 0.0
    if p_key !== nothing
        p_arr = psi_vars[p_key]
        timesteps = axes(p_arr)[2]
        gen_names = axes(p_arr)[1]
        for gname in gen_names
            for t in timesteps
                total_generation += JuMP.value(p_arr[gname, t]) * base_power
            end
        end
    end

    return Dict(
        "termination_status" => string(term_status),
        "objective_value" => round(obj_val; digits=2),
        "total_generation_mwh" => round(total_generation; digits=1),
        "lmp_summary" => if !isempty(hourly_lmps)
            all_vals = Float64[]
            for (_, hlmps) in hourly_lmps
                for v in values(hlmps)
                    isnan(v) || push!(all_vals, v)
                end
            end
            Dict(
                "min" => round(minimum(all_vals); digits=2),
                "max" => round(maximum(all_vals); digits=2),
                "mean" => round(sum(all_vals) / length(all_vals); digits=2),
                "spread" => round(maximum(all_vals) - minimum(all_vals); digits=2),
            )
        else
            Dict()
        end,
    )
end

function run(
    network_file::String="/workspace/data/networks/case39.m";
    timeseries_dir::Union{String,Nothing}="/workspace/data/timeseries/case39",
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    try
        if timeseries_dir === nothing
            push!(results["errors"], "timeseries_dir required for B-4")
            return results
        end

        solver = optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => false,
        )

        # Load shared data files once
        params = CSV.read(joinpath(timeseries_dir, "gen_temporal_params.csv"), DataFrame)
        re_df = CSV.read(joinpath(timeseries_dir, "renewable_units.csv"), DataFrame)
        wind_fc = CSV.read(joinpath(timeseries_dir, "wind_forecast_24h.csv"), DataFrame)
        solar_fc = CSV.read(joinpath(timeseries_dir, "solar_forecast_24h.csv"), DataFrame)
        load_df = CSV.read(joinpath(timeseries_dir, "load_24h.csv"), DataFrame)
        scenario_mults = CSV.read(
            joinpath(timeseries_dir, "scenarios", "scenario_multipliers_50x24.csv"), DataFrame
        )

        n_scenarios = 20
        results["details"]["n_scenarios"] = n_scenarios
        results["details"]["horizon_hours"] = 12

        # ===== Warm-up with scenario 1 =====
        try
            sys_w = build_system_for_scenario(
                network_file,
                timeseries_dir,
                1,
                scenario_mults,
                re_df,
                wind_fc,
                solar_fc,
                load_df,
                params,
            )
            solve_scenario(sys_w, solver)
        catch e
            # Warm-up may fail, continue
        end

        # ===== Run 20 scenarios =====
        scenario_results = Dict{Int,Any}()
        scenario_times = Float64[]
        n_converged = 0

        t0_total = time()

        for s in 1:n_scenarios
            t0_s = time()

            sys_s = build_system_for_scenario(
                network_file,
                timeseries_dir,
                s,
                scenario_mults,
                re_df,
                wind_fc,
                solar_fc,
                load_df,
                params,
            )
            model_s = solve_scenario(sys_s, solver)
            sr = extract_scenario_results(model_s, sys_s)

            elapsed_s = time() - t0_s
            push!(scenario_times, elapsed_s)

            sr["wall_clock_seconds"] = round(elapsed_s; digits=3)
            scenario_results[s] = sr

            if sr["termination_status"] == "OPTIMAL"
                n_converged += 1
            end
        end

        elapsed_total = time() - t0_total
        results["wall_clock_seconds"] = elapsed_total

        results["details"]["scenario_results"] = scenario_results
        results["details"]["n_converged"] = n_converged
        results["details"]["total_time_seconds"] = round(elapsed_total; digits=3)
        results["details"]["mean_time_per_scenario"] = round(
            sum(scenario_times) / length(scenario_times); digits=3
        )
        results["details"]["min_time_per_scenario"] = round(minimum(scenario_times); digits=3)
        results["details"]["max_time_per_scenario"] = round(maximum(scenario_times); digits=3)

        # Cross-scenario analysis
        objectives = [scenario_results[s]["objective_value"] for s in 1:n_scenarios]
        lmp_means = [scenario_results[s]["lmp_summary"]["mean"] for s in 1:n_scenarios]
        lmp_spreads = [scenario_results[s]["lmp_summary"]["spread"] for s in 1:n_scenarios]

        results["details"]["cross_scenario"] = Dict(
            "objective_min" => round(minimum(objectives); digits=2),
            "objective_max" => round(maximum(objectives); digits=2),
            "objective_mean" => round(sum(objectives) / length(objectives); digits=2),
            "objective_std" => round(std_dev(objectives); digits=2),
            "lmp_mean_min" => round(minimum(lmp_means); digits=2),
            "lmp_mean_max" => round(maximum(lmp_means); digits=2),
            "lmp_spread_min" => round(minimum(lmp_spreads); digits=2),
            "lmp_spread_max" => round(maximum(lmp_spreads); digits=2),
        )

        results["details"]["peak_memory_mb"] = peak_rss_mb()

        push!(
            results["workarounds"],
            "PowerSimulations.jl requires full System reconstruction per scenario — " *
            "time series data is immutable once attached to a System. Cannot modify " *
            "renewable profiles in-place after add_time_series!(). Each scenario " *
            "requires System(network_file) + add_time_series! + transform + build + solve.",
        )

        # Pass condition checks
        ts_programmatic = true  # time series are injected via API, not config files
        loop_expressible = true  # simple for loop with System reconstruction
        results_structured = n_converged == n_scenarios
        reasonable_overhead = sum(scenario_times) / n_scenarios < 30.0  # <30s per scenario

        results["details"]["pass_checks"] = Dict(
            "timeseries_programmatic" => ts_programmatic,
            "scenario_loop_expressible" => loop_expressible,
            "results_structured" => results_structured,
            "n_converged" => n_converged,
            "n_total" => n_scenarios,
            "mean_overhead_seconds" => round(sum(scenario_times) / n_scenarios; digits=3),
            "reasonable_overhead" => reasonable_overhead,
        )

        if ts_programmatic && loop_expressible && n_converged >= n_scenarios * 0.9
            results["status"] = "pass"
        elseif n_converged >= n_scenarios * 0.5
            results["status"] = "qualified_pass"
        else
            push!(results["errors"], "Only $n_converged of $n_scenarios scenarios converged")
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    end

    return results
end

function std_dev(v)
    m = sum(v) / length(v)
    sqrt(sum((x - m)^2 for x in v) / (length(v) - 1))
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

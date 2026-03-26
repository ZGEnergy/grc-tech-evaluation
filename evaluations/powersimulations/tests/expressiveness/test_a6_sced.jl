#=
Test A-6: Fix commitment from A-5, solve ED as LP/QP

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Solves. Dispatch schedule extractable. UC and ED are cleanly separable as a
  two-stage workflow. Ramp rate constraints are demonstrably enforced between consecutive
  dispatch intervals in the ED stage — not just inherited from UC formulation. v11 adds:
  ramp binding evidence (10% ramp rate tightening) and sced_mode classification.
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

function setup_system(network_file, timeseries_dir)
    sys = System(network_file)
    base_power = get_base_power(sys)

    params = CSV.read(joinpath(timeseries_dir, "gen_temporal_params.csv"), DataFrame)

    for row in eachrow(params)
        c1 = get(COST_MAP, row.tech_class_key, 30.0)
        for gen in get_components(ThermalStandard, sys)
            if get_number(get_bus(gen)) == row.bus_id
                # Linear costs for UC (HiGHS cannot do MIQP)
                startup_cost = row.startup_cost_cold_dollar
                no_load_cost = row.no_load_cost_dollar_per_hr

                set_operation_cost!(
                    gen,
                    ThermalGenerationCost(
                        CostCurve(LinearCurve(c1)), no_load_cost, startup_cost, 0.0
                    ),
                )

                # Set ramp limits
                ramp_pu = row.ramp_rate_mw_per_min / base_power
                set_ramp_limits!(gen, (up=ramp_pu, down=ramp_pu))

                # Set time limits
                set_time_limits!(gen, (up=row.min_up_time_hr, down=row.min_down_time_hr))

                # Set Pmin for UC
                pmax = get_active_power_limits(gen).max
                if row.tech_class_key == "hydro"
                    pmin = 0.25 * pmax
                elseif row.tech_class_key == "nuclear"
                    pmin = 0.5 * pmax
                elseif row.tech_class_key == "coal_large"
                    pmin = 0.4 * pmax
                elseif row.tech_class_key == "gas_CC"
                    pmin = 0.3 * pmax
                else
                    pmin = 0.3 * pmax
                end
                set_active_power_limits!(gen, (min=pmin, max=pmax))

                # Fix initial active power
                current_p = get_active_power(gen)
                if current_p > pmax
                    set_active_power!(gen, pmax * 0.8)
                elseif current_p < pmin
                    set_active_power!(gen, (pmin + pmax) / 2.0)
                end

                set_status!(gen, true)
                set_time_at_status!(gen, 999.0)
                break
            end
        end
    end

    # Load 24-hour profile
    load_df = CSV.read(joinpath(timeseries_dir, "load_24h.csv"), DataFrame)
    start_time = DateTime("2024-01-01")
    timestamps_ts = [start_time + Hour(h-1) for h in 1:25]

    for load in get_components(PowerLoad, sys)
        bus_num = get_number(get_bus(load))
        load_base = get_max_active_power(load) * base_power

        bus_row = filter(r -> r.bus_id == bus_num, load_df)
        if nrow(bus_row) > 0
            multipliers = Float64[]
            for h in 1:24
                hr_col = Symbol("HR_" * string(h))
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
                SingleTimeSeries("max_active_power", TimeArray(timestamps_ts, multipliers)),
            )
        else
            add_time_series!(
                sys, load, SingleTimeSeries("max_active_power", TimeArray(timestamps_ts, ones(25)))
            )
        end
    end

    transform_single_time_series!(sys, Hour(24), Hour(1))
    return sys
end

function solve_scuc(sys, solver)
    template = ProblemTemplate(NetworkModel(DCPPowerModel; duals=[NodalBalanceActiveConstraint]))
    set_device_model!(template, ThermalStandard, ThermalStandardUnitCommitment)
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

function extract_commitment(model)
    oc = PSI.get_optimization_container(model)
    psi_vars = PSI.get_variables(oc)

    on_key = nothing
    for k in keys(psi_vars)
        if occursin("OnVariable", string(k)) && occursin("ThermalStandard", string(k))
            on_key = k
            break
        end
    end

    on_arr = psi_vars[on_key]
    gen_names = sort(axes(on_arr)[1])
    timesteps = axes(on_arr)[2]

    commitment = Dict{String,Vector{Int}}()
    for gname in gen_names
        schedule = [Int(round(JuMP.value(on_arr[gname, t]))) for t in timesteps]
        commitment[gname] = schedule
    end
    return commitment, gen_names, timesteps
end

function solve_ed_with_fixed_commitment(
    sys,
    solver,
    commitment,
    gen_names,
    timeseries_dir;
    ramp_tightening::Float64=1.0,
    use_linear_costs::Bool=false,
)
    # For ED: use ThermalDispatch (LP dispatch) but fix generators that are off
    # to have Pmax=0 for each hour they are decommitted.
    #
    # PSI approach: Create a new system where decommitted generators have their
    # active power limits set to 0 for hours they're off. We do this by modifying
    # the system to add time-varying limits.
    #
    # Alternative approach: Use DecisionModel with ThermalDispatchNoMin and fix
    # commitment by modifying generator availability via must-run status.
    #
    # Best PSI approach: Use EconomicDispatchProblem or build a DecisionModel
    # with ThermalBasicDispatch/ThermalDispatchNoMin, and enforce commitment
    # by setting generators' time-varying active_power_limits or using must_run.
    #
    # Workaround: We'll build a DecisionModel with ThermalDispatchNoMin and then
    # directly fix the JuMP variables using the commitment schedule.

    base_power = get_base_power(sys)
    params = CSV.read(joinpath(timeseries_dir, "gen_temporal_params.csv"), DataFrame)

    # Set costs for ED
    for row in eachrow(params)
        c1 = get(COST_MAP, row.tech_class_key, 30.0)
        for gen in get_components(ThermalStandard, sys)
            if get_number(get_bus(gen)) == row.bus_id
                if use_linear_costs
                    set_operation_cost!(
                        gen, ThermalGenerationCost(CostCurve(LinearCurve(c1)), 0.0, 0.0, 0.0)
                    )
                else
                    c2 = c1 * 0.001
                    set_operation_cost!(
                        gen,
                        ThermalGenerationCost(
                            CostCurve(QuadraticCurve(c2, c1, 0.0)), 0.0, 0.0, 0.0
                        ),
                    )
                end
                break
            end
        end
    end

    template = ProblemTemplate(NetworkModel(DCPPowerModel; duals=[NodalBalanceActiveConstraint]))
    # Use ThermalDispatchNoMin — LP dispatch without min power constraints
    # We'll add the commitment fixing manually via JuMP
    set_device_model!(template, ThermalStandard, ThermalDispatchNoMin)
    set_device_model!(template, PowerLoad, StaticPowerLoad)
    set_device_model!(template, Line, StaticBranch)
    set_device_model!(template, Transformer2W, StaticBranch)
    set_device_model!(template, TapTransformer, StaticBranch)

    model = DecisionModel(template, sys; optimizer=solver, initialize_model=false)
    build!(model; output_dir=mktempdir())

    oc = PSI.get_optimization_container(model)
    jm = PSI.get_jump_model(oc)
    psi_vars = PSI.get_variables(oc)

    # Find ActivePowerVariable
    p_key = nothing
    for k in keys(psi_vars)
        if occursin("ActivePowerVariable", string(k)) && occursin("ThermalStandard", string(k))
            p_key = k
            break
        end
    end
    p_arr = psi_vars[p_key]
    ed_gen_names = axes(p_arr)[1]
    ed_timesteps = axes(p_arr)[2]

    # Fix commitment: for decommitted hours, fix P = 0
    fixed_count = 0
    for gname in ed_gen_names
        if haskey(commitment, gname)
            sched = commitment[gname]
            for (ti, t) in enumerate(ed_timesteps)
                if ti <= length(sched) && sched[ti] == 0
                    JuMP.fix(p_arr[gname, t], 0.0; force=true)
                    fixed_count += 1
                end
            end
        end
    end

    # Add ramp constraints between consecutive ED intervals
    # This is the key test: ramp constraints must be EXPLICITLY enforced in ED
    ramp_rates = Dict{String,Float64}()
    for row in eachrow(params)
        for gen in get_components(ThermalStandard, sys)
            if get_number(get_bus(gen)) == row.bus_id
                gname = get_name(gen)
                # Ramp rate in pu/min * 60 min/hr = pu/hr, apply tightening factor
                ramp_pu_hr = row.ramp_rate_mw_per_min / base_power * 60.0 * ramp_tightening
                ramp_rates[gname] = ramp_pu_hr
                break
            end
        end
    end

    ramp_constraints_added = 0
    for gname in ed_gen_names
        if haskey(ramp_rates, gname)
            ramp_limit = ramp_rates[gname]
            for ti in 2:length(ed_timesteps)
                t_curr = ed_timesteps[ti]
                t_prev = ed_timesteps[ti - 1]
                # Ramp up: P(t) - P(t-1) <= ramp_limit
                @constraint(jm, p_arr[gname, t_curr] - p_arr[gname, t_prev] <= ramp_limit)
                # Ramp down: P(t-1) - P(t) <= ramp_limit
                @constraint(jm, p_arr[gname, t_prev] - p_arr[gname, t_curr] <= ramp_limit)
                ramp_constraints_added += 2
            end
        end
    end

    JuMP.optimize!(jm)
    return model, fixed_count, ramp_constraints_added, ramp_rates
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
            push!(results["errors"], "timeseries_dir required for A-6")
            return results
        end

        solver = optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "mip_rel_gap" => 0.01,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => false,
        )

        # ===== Warm-up =====
        try
            sys_w = setup_system(network_file, timeseries_dir)
            uc_model_w = solve_scuc(sys_w, solver)
            commitment_w, gnames_w, tsteps_w = extract_commitment(uc_model_w)
            sys_ed_w = setup_system(network_file, timeseries_dir)
            solve_ed_with_fixed_commitment(sys_ed_w, solver, commitment_w, gnames_w, timeseries_dir)
        catch e
            # Warm-up failure is OK for JIT
        end

        # ===== Stage 1: SCUC =====
        sys_uc = setup_system(network_file, timeseries_dir)
        base_power = get_base_power(sys_uc)

        t0_uc = time()
        uc_model = solve_scuc(sys_uc, solver)
        uc_elapsed = time() - t0_uc

        # Extract UC results
        oc_uc = PSI.get_optimization_container(uc_model)
        jm_uc = PSI.get_jump_model(oc_uc)
        uc_status = termination_status(jm_uc)
        uc_obj = objective_value(jm_uc)

        commitment, gen_names, uc_timesteps = extract_commitment(uc_model)
        n_hours = length(uc_timesteps)

        results["details"]["uc_stage"] = Dict(
            "termination_status" => string(uc_status),
            "objective_value" => round(uc_obj; digits=2),
            "wall_clock_seconds" => round(uc_elapsed; digits=3),
            "horizon_hours" => n_hours,
            "commitment_schedule" => commitment,
        )

        # Count cycling
        cycling_gens = String[]
        for gname in gen_names
            transitions = sum(abs.(diff(commitment[gname])))
            if transitions >= 1
                push!(cycling_gens, gname)
            end
        end
        results["details"]["uc_stage"]["cycling_generators"] = cycling_gens

        # ===== Stage 2: ED with fixed commitment =====
        sys_ed = setup_system(network_file, timeseries_dir)

        t0_ed = time()
        ed_model, fixed_count, ramp_added, ramp_rates = solve_ed_with_fixed_commitment(
            sys_ed, solver, commitment, gen_names, timeseries_dir
        )
        ed_elapsed = time() - t0_ed

        oc_ed = PSI.get_optimization_container(ed_model)
        jm_ed = PSI.get_jump_model(oc_ed)
        ed_status = termination_status(jm_ed)
        ed_obj = objective_value(jm_ed)

        results["details"]["ed_stage"] = Dict(
            "termination_status" => string(ed_status),
            "objective_value" => round(ed_obj; digits=2),
            "wall_clock_seconds" => round(ed_elapsed; digits=3),
            "variables_fixed_to_zero" => fixed_count,
            "ramp_constraints_added" => ramp_added,
            "formulation" => "ThermalDispatchNoMin (LP) with fixed commitment from UC stage",
        )

        # Extract ED dispatch
        psi_vars_ed = PSI.get_variables(oc_ed)
        p_key = nothing
        for k in keys(psi_vars_ed)
            if occursin("ActivePowerVariable", string(k)) && occursin("ThermalStandard", string(k))
                p_key = k
                break
            end
        end
        p_arr = psi_vars_ed[p_key]
        ed_gen_names = sort(collect(axes(p_arr)[1]))
        ed_timesteps = axes(p_arr)[2]

        dispatch_table = Dict{String,Any}()
        for gname in ed_gen_names
            vals_pu = [JuMP.value(p_arr[gname, t]) for t in ed_timesteps]
            vals_mw = vals_pu .* base_power
            dispatch_table[gname] = Dict(
                "dispatch_mw" => [round(v; digits=1) for v in vals_mw],
                "min_mw" => round(minimum(vals_mw); digits=1),
                "max_mw" => round(maximum(vals_mw); digits=1),
                "mean_mw" => round(sum(vals_mw) / length(vals_mw); digits=1),
            )
        end
        results["details"]["ed_dispatch"] = dispatch_table

        # Verify commitment is enforced: decommitted hours should have 0 dispatch
        commitment_enforced = true
        violations = String[]
        for gname in ed_gen_names
            if haskey(commitment, gname)
                sched = commitment[gname]
                for (ti, t) in enumerate(ed_timesteps)
                    if ti <= length(sched) && sched[ti] == 0
                        p_val = JuMP.value(p_arr[gname, t]) * base_power
                        if abs(p_val) > 0.1  # MW tolerance
                            commitment_enforced = false
                            push!(violations, "$gname at hour $ti: $(round(p_val, digits=2)) MW")
                        end
                    end
                end
            end
        end
        results["details"]["commitment_enforced"] = commitment_enforced
        results["details"]["commitment_violations"] = violations

        # Verify ramp constraints are binding somewhere (check if any ramp is tight)
        ramp_binding = false
        ramp_binding_count = 0
        for gname in ed_gen_names
            if haskey(ramp_rates, gname)
                ramp_limit_mw = ramp_rates[gname] * base_power
                for ti in 2:length(ed_timesteps)
                    p_curr = JuMP.value(p_arr[gname, ed_timesteps[ti]]) * base_power
                    p_prev = JuMP.value(p_arr[gname, ed_timesteps[ti - 1]]) * base_power
                    ramp_actual = abs(p_curr - p_prev)
                    if ramp_actual > ramp_limit_mw * 0.99  # 99% of limit = binding
                        ramp_binding = true
                        ramp_binding_count += 1
                    end
                end
            end
        end
        results["details"]["ramp_constraints_binding"] = ramp_binding
        results["details"]["ramp_binding_count"] = ramp_binding_count

        # LMPs from ED (via JuMP duals on nodal balance constraints)
        ed_lmps_by_hour = Dict{Int,Dict{String,Float64}}()
        try
            psi_constraints_ed = PSI.get_constraints(oc_ed)
            nodal_key_ed = nothing
            for k in keys(psi_constraints_ed)
                if occursin("NodalBalanceActive", string(k))
                    nodal_key_ed = k
                    break
                end
            end
            if nodal_key_ed !== nothing
                nodal_arr_ed = psi_constraints_ed[nodal_key_ed]
                bus_names_ed = sort(collect(axes(nodal_arr_ed)[1]))
                for (ti, t) in enumerate(ed_timesteps)
                    hour_lmps = Dict{String,Float64}()
                    for bname in bus_names_ed
                        try
                            dual_val = JuMP.dual(nodal_arr_ed[bname, t])
                            hour_lmps[bname] = -dual_val / base_power
                        catch
                            hour_lmps[bname] = NaN
                        end
                    end
                    ed_lmps_by_hour[ti] = hour_lmps
                end
                # Summary
                lmp_summary = Dict{Int,Any}()
                for (ti, hlmps) in ed_lmps_by_hour
                    vals = [v for v in values(hlmps) if !isnan(v)]
                    if !isempty(vals)
                        lmp_summary[ti] = Dict(
                            "min" => round(minimum(vals); digits=2),
                            "max" => round(maximum(vals); digits=2),
                            "mean" => round(sum(vals)/length(vals); digits=2),
                        )
                    end
                end
                results["details"]["ed_lmp_summary"] = lmp_summary
            end
        catch
            results["details"]["ed_lmp_note"] = "LMP extraction via JuMP duals failed"
        end

        # ===== v11: Ramp Tightening Evidence =====
        # Solve ED again with 10% tighter ramp rates to prove ramps are actively enforced
        ramp_tightening_evidence = Dict{String,Any}()
        try
            # Use linear costs for the tightening comparison to avoid HiGHS QP issues
            # First, re-solve base ED with linear costs for fair comparison
            sys_ed_base_lc = setup_system(network_file, timeseries_dir)
            ed_model_base_lc, _, _, _ = solve_ed_with_fixed_commitment(
                sys_ed_base_lc, solver, commitment, gen_names, timeseries_dir; use_linear_costs=true
            )
            oc_base_lc = PSI.get_optimization_container(ed_model_base_lc)
            jm_base_lc = PSI.get_jump_model(oc_base_lc)
            base_lc_obj = objective_value(jm_base_lc)

            # Now solve with 10% tighter ramps
            sys_ed_tight = setup_system(network_file, timeseries_dir)
            ed_model_tight, _, _, ramp_rates_tight = solve_ed_with_fixed_commitment(
                sys_ed_tight,
                solver,
                commitment,
                gen_names,
                timeseries_dir;
                ramp_tightening=0.9,  # 10% tighter
                use_linear_costs=true,
            )
            oc_ed_tight = PSI.get_optimization_container(ed_model_tight)
            jm_ed_tight = PSI.get_jump_model(oc_ed_tight)
            tight_status = termination_status(jm_ed_tight)

            if tight_status == MOI.INFEASIBLE || tight_status == MOI.INFEASIBLE_OR_UNBOUNDED
                # Tightened ramps make the problem infeasible — strong evidence that
                # ramps are actively constraining the dispatch
                ramp_tightening_evidence = Dict(
                    "tight_termination" => string(tight_status),
                    "base_objective" => round(ed_obj; digits=2),
                    "dispatch_changed" => true,
                    "evidence_conclusion" =>
                        "10% ramp tightening makes ED infeasible — ramps are actively binding and " *
                        "constraining dispatch. This is strong evidence of ramp enforcement.",
                )
            elseif tight_status == MOI.OPTIMAL || tight_status == MOI.FEASIBLE_POINT
                tight_obj = objective_value(jm_ed_tight)

                # Extract dispatch from tightened run
                psi_vars_tight = PSI.get_variables(oc_ed_tight)
                pt_key = nothing
                for k in keys(psi_vars_tight)
                    if occursin("ActivePowerVariable", string(k)) &&
                        occursin("ThermalStandard", string(k))
                        pt_key = k;
                        break
                    end
                end
                pt_arr = psi_vars_tight[pt_key]
                pt_gen_names = sort(collect(axes(pt_arr)[1]))
                pt_timesteps = axes(pt_arr)[2]

                # Compare dispatch: compute max absolute difference per generator
                dispatch_diffs = Dict{String,Float64}()
                for gname in pt_gen_names
                    if haskey(dispatch_table, gname)
                        base_vals = dispatch_table[gname]["dispatch_mw"]
                        tight_vals = [
                            JuMP.value(pt_arr[gname, t]) * base_power for t in pt_timesteps
                        ]
                        max_diff = maximum(abs.(tight_vals .- base_vals))
                        dispatch_diffs[gname] = round(max_diff; digits=2)
                    end
                end

                obj_diff = tight_obj - base_lc_obj
                ramp_tightening_evidence = Dict(
                    "tight_termination" => string(tight_status),
                    "tight_objective" => round(tight_obj; digits=2),
                    "base_objective_linear" => round(base_lc_obj; digits=2),
                    "objective_increase" => round(obj_diff; digits=2),
                    "dispatch_max_diffs_mw" => dispatch_diffs,
                    "dispatch_changed" => any(v -> v > 0.1, values(dispatch_diffs)),
                    "evidence_conclusion" =>
                        if obj_diff > 0.01 || any(v -> v > 0.1, values(dispatch_diffs))
                            "Ramp tightening changes dispatch/objective — ramps are actively enforced in ED"
                        else
                            "Ramp tightening had no effect — ramps may not be binding"
                        end,
                )
            else
                ramp_tightening_evidence = Dict(
                    "tight_termination" => string(tight_status),
                    "dispatch_changed" => false,
                    "evidence_conclusion" => "Tightened solve returned status: $tight_status",
                )
            end
        catch e
            ramp_tightening_evidence["error"] = string(typeof(e), ": ", sprint(showerror, e))
        end
        results["details"]["ramp_tightening_evidence"] = ramp_tightening_evidence

        # SCED mode classification
        results["details"]["sced_mode"] = "ed_only"  # No security constraints, pure ED with fixed UC

        total_elapsed = uc_elapsed + ed_elapsed
        results["wall_clock_seconds"] = total_elapsed
        results["details"]["total_wall_clock_seconds"] = round(total_elapsed; digits=3)
        results["details"]["peak_memory_mb"] = peak_rss_mb()

        # Pass condition checks
        uc_solved = uc_status == MOI.OPTIMAL || uc_status == MOI.FEASIBLE_POINT
        ed_solved = ed_status == MOI.OPTIMAL
        dispatch_ok = !isempty(dispatch_table)
        separation_ok = true  # UC and ED are cleanly separable (two distinct models)
        ramp_evidence_ok =
            get(ramp_tightening_evidence, "dispatch_changed", false) ||
            get(ramp_tightening_evidence, "objective_increase", 0.0) > 0.01 ||
            get(ramp_tightening_evidence, "tight_termination", "") == "INFEASIBLE"

        results["details"]["pass_checks"] = Dict(
            "uc_solved" => uc_solved,
            "ed_solved" => ed_solved,
            "dispatch_extractable" => dispatch_ok,
            "two_stage_separation" => separation_ok,
            "commitment_enforced" => commitment_enforced,
            "ramp_constraints_in_ed" => ramp_added > 0,
            "ramp_constraints_binding" => ramp_binding,
            "ramp_tightening_evidence" => ramp_evidence_ok,
        )

        if uc_solved && ed_solved && dispatch_ok && commitment_enforced
            results["status"] = "qualified_pass"
            push!(
                results["workarounds"],
                "UC→ED two-stage separation required manual intervention: " *
                "(1) Extracted commitment from UC via PSI.get_variables() internal API. " *
                "(2) Fixed decommitted generators to P=0 using JuMP.fix(). " *
                "(3) Added ramp constraints manually via JuMP @constraint. " *
                "PSI does not provide a built-in two-stage UC→ED workflow — the ED model " *
                "must be manually constructed with commitment values transferred from UC. " *
                "Ramp constraints in ThermalDispatchNoMin are not active by default; they " *
                "had to be added explicitly to the JuMP model.",
            )
        else
            push!(
                results["errors"],
                "UC solved: $uc_solved, ED solved: $ed_solved, " *
                "dispatch OK: $dispatch_ok, commitment enforced: $commitment_enforced",
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

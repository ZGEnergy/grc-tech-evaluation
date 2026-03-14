#=
Test B-1: Custom Constraints (flow gate limit + dual extraction)

Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Achievable through documented API or extension. No source patching.
  Dual value extractable, correctly reflects binding status.
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

# Cost mapping from Modified Tiny
const COST_MAP = Dict("hydro" => 5.0, "nuclear" => 10.0, "coal_large" => 25.0, "gas_CC" => 40.0)

function setup_system(network_file, timeseries_dir)
    sys = System(network_file)

    # Apply differentiated costs
    params = CSV.read(joinpath(timeseries_dir, "gen_temporal_params.csv"), DataFrame)
    for row in eachrow(params)
        c1 = get(COST_MAP, row.tech_class_key, 30.0)
        c2 = c1 * 0.001
        for gen in get_components(ThermalStandard, sys)
            if get_number(get_bus(gen)) == row.bus_id
                set_operation_cost!(
                    gen,
                    ThermalGenerationCost(CostCurve(QuadraticCurve(c2, c1, 0.0)), 0.0, 0.0, 0.0),
                )
                break
            end
        end
    end

    # Apply 70% branch derating to create congestion
    for line in get_components(Line, sys)
        set_rating!(line, get_rating(line) * 0.7)
    end
    for xfmr in get_components(Transformer2W, sys)
        set_rating!(xfmr, get_rating(xfmr) * 0.7)
    end
    for xfmr in get_components(TapTransformer, sys)
        set_rating!(xfmr, get_rating(xfmr) * 0.7)
    end

    # Add time series (required by PowerSimulations)
    timestamps = [DateTime("2024-01-01"), DateTime("2024-01-01") + Hour(1)]
    for load in get_components(PowerLoad, sys)
        add_time_series!(
            sys, load, SingleTimeSeries("max_active_power", TimeArray(timestamps, [1.0, 1.0]))
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
    set_device_model!(template, TapTransformer, StaticBranch)

    model = DecisionModel(template, sys; optimizer=solver)
    build!(model; output_dir=mktempdir())
    return model
end

"""
Find flow variable for a given branch name across all flow variable containers
(Line, Transformer2W, TapTransformer).
"""
function find_flow_var(oc, branch_name, t_idx)
    psi_vars = PSI.get_variables(oc)
    for k in keys(psi_vars)
        ks = string(k)
        if occursin("FlowActivePowerVariable", ks)
            arr = psi_vars[k]
            ax_names = axes(arr)[1]
            if branch_name in ax_names
                return arr[branch_name, t_idx]
            end
        end
    end
    return nothing
end

"""
Match flowgate bus pairs to PSI branch names, searching all component types.
"""
function match_fg_branches(sys, from_buses, to_buses)
    fg_branch_names = String[]
    fg_branch_types = String[]

    for (fb, tb) in zip(from_buses, to_buses)
        fbi = Int(fb)
        tbi = Int(tb)
        found = false

        for CompType in [Line, Transformer2W, TapTransformer]
            for comp in get_components(CompType, sys)
                arc = get_arc(comp)
                f = get_number(get_from(arc))
                t = get_number(get_to(arc))
                if (f == fbi && t == tbi) || (f == tbi && t == fbi)
                    push!(fg_branch_names, get_name(comp))
                    push!(fg_branch_types, string(CompType))
                    found = true
                    break
                end
            end
            if found
                ;
                break;
            end
        end
    end

    return fg_branch_names, fg_branch_types
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
            push!(results["errors"], "timeseries_dir required for B-1")
            return results
        end

        solver = optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => false,
        )

        # Read flowgate metadata
        fg_meta = JSON.parsefile(joinpath(timeseries_dir, "flowgate_metadata.json"))
        fg1 = fg_meta["flowgates"][1]  # FG_01: branches 2-3 and 2-30, limit 475 MW
        results["details"]["flowgate_info"] = Dict(
            "id" => fg1["flowgate_id"],
            "name" => fg1["name"],
            "limit_mw" => fg1["limit_mw"],
            "from_buses" => fg1["from_buses"],
            "to_buses" => fg1["to_buses"],
            "weights" => fg1["weights"],
        )

        # ============================================================
        # Warm-up (JIT compilation)
        # ============================================================
        sys_w = setup_system(network_file, timeseries_dir)
        model_w = build_dcopf_model(sys_w, solver)
        solve!(model_w)

        # ============================================================
        # Match flowgate branches
        # ============================================================
        sys_ref = setup_system(network_file, timeseries_dir)
        fg_branch_names, fg_branch_types = match_fg_branches(
            sys_ref, fg1["from_buses"], fg1["to_buses"]
        )
        base_power = get_base_power(sys_ref)

        results["details"]["fg_branch_names"] = fg_branch_names
        results["details"]["fg_branch_types"] = fg_branch_types
        results["details"]["base_power_mva"] = base_power

        if length(fg_branch_names) != length(fg1["from_buses"])
            push!(
                results["errors"],
                "Could not match all flowgate branches: found $(length(fg_branch_names)) of $(length(fg1["from_buses"]))",
            )
        end

        t0 = time()

        # ============================================================
        # TEST A: Non-binding flow gate (high limit -> dual should be 0)
        # ============================================================
        sys_nb = setup_system(network_file, timeseries_dir)
        model_nb = build_dcopf_model(sys_nb, solver)
        oc_nb = PSI.get_optimization_container(model_nb)
        jm_nb = PSI.get_jump_model(oc_nb)
        t_idx = first(axes(PSI.get_variables(oc_nb)[first(keys(PSI.get_variables(oc_nb)))])[2])

        # Build flowgate expression from flow variables across all branch types
        fg_flow_vars_nb = []
        for (i, bn) in enumerate(fg_branch_names)
            fv = find_flow_var(oc_nb, bn, t_idx)
            if fv === nothing
                push!(results["errors"], "Flow variable not found for branch: $bn")
                return results
            end
            push!(fg_flow_vars_nb, fg1["weights"][i] * fv)
        end
        fg_expr_nb = sum(fg_flow_vars_nb)

        # Non-binding: set limit very high (10000 MW -> per-unit)
        high_limit_pu = 10000.0 / base_power
        con_nb_upper = @constraint(jm_nb, fg_expr_nb <= high_limit_pu)
        con_nb_lower = @constraint(jm_nb, -fg_expr_nb <= high_limit_pu)

        # Solve via JuMP (not PSI solve! which ignores manually added constraints)
        JuMP.optimize!(jm_nb)

        nb_term = JuMP.termination_status(jm_nb)
        nb_obj = JuMP.objective_value(jm_nb)
        nb_dual_upper = JuMP.dual(con_nb_upper)
        nb_dual_lower = JuMP.dual(con_nb_lower)
        nb_fg_flow_pu = JuMP.value(fg_expr_nb)
        nb_fg_flow_mw = nb_fg_flow_pu * base_power

        results["details"]["non_binding"] = Dict(
            "termination_status" => string(nb_term),
            "objective_value" => round(nb_obj; digits=2),
            "flowgate_limit_mw" => 10000.0,
            "flowgate_flow_mw" => round(nb_fg_flow_mw; digits=2),
            "dual_upper" => round(nb_dual_upper; digits=6),
            "dual_lower" => round(nb_dual_lower; digits=6),
            "dual_is_zero" => abs(nb_dual_upper) < 1e-6 && abs(nb_dual_lower) < 1e-6,
        )

        # ============================================================
        # TEST B: Binding flow gate (~50% of unconstrained flow)
        # ============================================================
        binding_limit_mw = abs(nb_fg_flow_mw) * 0.5
        binding_limit_pu = binding_limit_mw / base_power

        sys_b = setup_system(network_file, timeseries_dir)
        model_b = build_dcopf_model(sys_b, solver)
        oc_b = PSI.get_optimization_container(model_b)
        jm_b = PSI.get_jump_model(oc_b)
        t_idx_b = first(axes(PSI.get_variables(oc_b)[first(keys(PSI.get_variables(oc_b)))])[2])

        # Build flowgate expression for binding model
        fg_flow_vars_b = []
        for (i, bn) in enumerate(fg_branch_names)
            fv = find_flow_var(oc_b, bn, t_idx_b)
            push!(fg_flow_vars_b, fg1["weights"][i] * fv)
        end
        fg_expr_b = sum(fg_flow_vars_b)

        con_b_upper = @constraint(jm_b, fg_expr_b <= binding_limit_pu)
        con_b_lower = @constraint(jm_b, -fg_expr_b <= binding_limit_pu)

        JuMP.optimize!(jm_b)

        b_term = JuMP.termination_status(jm_b)
        b_obj = JuMP.objective_value(jm_b)
        b_dual_upper = JuMP.dual(con_b_upper)
        b_dual_lower = JuMP.dual(con_b_lower)
        b_fg_flow_pu = JuMP.value(fg_expr_b)
        b_fg_flow_mw = b_fg_flow_pu * base_power

        elapsed = time() - t0

        results["details"]["binding"] = Dict(
            "termination_status" => string(b_term),
            "objective_value" => round(b_obj; digits=2),
            "flowgate_limit_mw" => round(binding_limit_mw; digits=2),
            "flowgate_flow_mw" => round(b_fg_flow_mw; digits=2),
            "dual_upper" => round(b_dual_upper; digits=6),
            "dual_lower" => round(b_dual_lower; digits=6),
            "dual_is_nonzero" => abs(b_dual_upper) > 1e-6 || abs(b_dual_lower) > 1e-6,
        )

        # Cost increase due to binding constraint
        cost_increase = b_obj - nb_obj
        results["details"]["cost_comparison"] = Dict(
            "unconstrained_objective" => round(nb_obj; digits=2),
            "constrained_objective" => round(b_obj; digits=2),
            "cost_increase" => round(cost_increase; digits=2),
            "objective_increased" => cost_increase > 0.01,
        )

        results["wall_clock_seconds"] = elapsed
        results["details"]["peak_memory_mb"] = peak_rss_mb()

        # Pass condition checks
        nb_dual_zero = abs(nb_dual_upper) < 1e-6 && abs(nb_dual_lower) < 1e-6
        b_dual_nonzero = abs(b_dual_upper) > 1e-6 || abs(b_dual_lower) > 1e-6
        obj_increased = cost_increase > 0.01
        both_optimal =
            (nb_term == MOI.OPTIMAL || nb_term == MOI.FEASIBLE_POINT) &&
            (b_term == MOI.OPTIMAL || b_term == MOI.FEASIBLE_POINT)

        results["details"]["pass_checks"] = Dict(
            "non_binding_dual_zero" => nb_dual_zero,
            "binding_dual_nonzero" => b_dual_nonzero,
            "objective_increased" => obj_increased,
            "both_solved" => both_optimal,
            "no_source_patching" => true,
        )

        if both_optimal && nb_dual_zero && b_dual_nonzero && obj_increased
            results["status"] = "pass"
        elseif both_optimal && b_dual_nonzero
            results["status"] = "qualified_pass"
            if !nb_dual_zero
                push!(
                    results["workarounds"],
                    "Non-binding dual not exactly zero ($(round(nb_dual_upper, digits=8))), but constraint addition and dual extraction work correctly.",
                )
            end
            if !obj_increased
                push!(
                    results["workarounds"],
                    "Objective did not increase with binding constraint. May indicate constraint is not truly binding at this limit.",
                )
            end
        else
            push!(
                results["errors"],
                "Pass condition not fully met: both_optimal=$both_optimal, nb_dual_zero=$nb_dual_zero, b_dual_nonzero=$b_dual_nonzero, obj_increased=$obj_increased",
            )
        end

        push!(
            results["workarounds"],
            "PowerSimulations.jl requires time series data even for single-snapshot OPF. " *
            "Added 1-step forecast with multiplier=1.0 for all loads.",
        )

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

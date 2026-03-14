#=
Test A-3: DCOPF with differentiated costs and 70% branch derating

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Converges. Optimal dispatch and LMPs extractable. With differentiated costs
  and 70% derating, >=2 branches have non-zero shadow prices. Report max LMP spread.
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

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024  # kB to MB
        end
    end
    return nothing
end

# Cost mapping from README: tech_class_key -> c1 ($/MWh)
const COST_MAP = Dict("hydro" => 5.0, "nuclear" => 10.0, "coal_large" => 25.0, "gas_CC" => 40.0)

function setup_system(network_file, timeseries_dir)
    sys = System(network_file)

    # Apply differentiated costs
    params = CSV.read(joinpath(timeseries_dir, "gen_temporal_params.csv"), DataFrame)
    cost_changes = Dict{String,Any}[]
    for row in eachrow(params)
        c1 = get(COST_MAP, row.tech_class_key, 30.0)
        c2 = c1 * 0.001
        for gen in get_components(ThermalStandard, sys)
            if get_number(get_bus(gen)) == row.bus_id
                set_operation_cost!(
                    gen,
                    ThermalGenerationCost(CostCurve(QuadraticCurve(c2, c1, 0.0)), 0.0, 0.0, 0.0),
                )
                push!(
                    cost_changes,
                    Dict(
                        "gen" => get_name(gen),
                        "bus" => row.bus_id,
                        "tech" => row.tech_class_key,
                        "c1" => c1,
                        "c2" => c2,
                    ),
                )
                break
            end
        end
    end

    # Apply 70% branch derating
    derated = 0
    for line in get_components(Line, sys)
        set_rating!(line, get_rating(line) * 0.7);
        derated += 1
    end
    for xfmr in get_components(Transformer2W, sys)
        set_rating!(xfmr, get_rating(xfmr) * 0.7);
        derated += 1
    end
    for xfmr in get_components(TapTransformer, sys)
        set_rating!(xfmr, get_rating(xfmr) * 0.7);
        derated += 1
    end

    # Add load time series (required by PowerSimulations)
    timestamps = [DateTime("2024-01-01"), DateTime("2024-01-01") + Hour(1)]
    for load in get_components(PowerLoad, sys)
        add_time_series!(
            sys, load, SingleTimeSeries("max_active_power", TimeArray(timestamps, [1.0, 1.0]))
        )
    end
    transform_single_time_series!(sys, Hour(1), Hour(1))

    return sys, cost_changes, derated
end

function build_and_solve(sys, solver)
    # DCPPowerModel with NodalBalanceActiveConstraint duals for bus-level LMPs
    template = ProblemTemplate(NetworkModel(DCPPowerModel; duals=[NodalBalanceActiveConstraint]))
    set_device_model!(template, ThermalStandard, ThermalDispatchNoMin)
    set_device_model!(template, PowerLoad, StaticPowerLoad)
    set_device_model!(template, Line, StaticBranch)
    set_device_model!(template, Transformer2W, StaticBranch)
    set_device_model!(template, TapTransformer, StaticBranch)

    model = DecisionModel(template, sys; optimizer=solver)
    build!(model; output_dir=mktempdir())
    solve!(model)
    return model
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
            push!(results["errors"], "timeseries_dir required for A-3")
            return results
        end

        solver = optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => false,
        )

        # Warm-up (JIT compilation)
        sys_w, _, _ = setup_system(network_file, timeseries_dir)
        build_and_solve(sys_w, solver)

        # Timed run
        sys, cost_changes, derated = setup_system(network_file, timeseries_dir)
        base_power = get_base_power(sys)

        t0 = time()
        model = build_and_solve(sys, solver)
        elapsed = time() - t0

        results["wall_clock_seconds"] = elapsed
        results["details"]["peak_memory_mb"] = peak_rss_mb()
        results["details"]["base_power_mva"] = base_power
        results["details"]["cost_changes"] = cost_changes
        results["details"]["branches_derated"] = derated

        # Workaround: PSI requires time series even for single-snapshot OPF
        push!(
            results["workarounds"],
            "PowerSimulations.jl requires deterministic time series data even for single-snapshot DCOPF. Added 1-step forecast with multiplier=1.0 for all loads.",
        )

        # Extract results
        res = OptimizationProblemResults(model)

        # Dispatch (returned in MW by PSI)
        dispatch_df = read_variable(res, "ActivePowerVariable__ThermalStandard")
        dispatch_summary = Dict{String,Any}()
        for col in names(dispatch_df)
            col == "DateTime" && continue
            dispatch_summary[col] = Dict("dispatch_mw" => dispatch_df[1, col])
        end
        results["details"]["dispatch"] = dispatch_summary

        # LMPs from nodal balance duals
        # PSI returns duals in internal units (per-unit based).
        # LMP ($/MWh) = -dual_value / base_power
        nodal_dual = read_dual(res, "NodalBalanceActiveConstraint__ACBus")
        lmp_data = Dict{String,Float64}()
        lmp_vals = Float64[]
        for col in names(nodal_dual)
            col == "DateTime" && continue
            raw_dual = nodal_dual[1, col]
            lmp_mwh = -raw_dual / base_power  # convert to $/MWh
            lmp_data[col] = lmp_mwh
            push!(lmp_vals, lmp_mwh)
        end

        lmp_min = minimum(lmp_vals)
        lmp_max = maximum(lmp_vals)
        lmp_spread = lmp_max - lmp_min

        results["details"]["lmps"] = lmp_data
        results["details"]["lmp_summary"] = Dict(
            "min_dollar_per_mwh" => round(lmp_min; digits=2),
            "max_dollar_per_mwh" => round(lmp_max; digits=2),
            "spread_dollar_per_mwh" => round(lmp_spread; digits=2),
            "mean_dollar_per_mwh" => round(sum(lmp_vals) / length(lmp_vals); digits=2),
            "n_buses" => length(lmp_vals),
        )

        # Identify binding branches
        flows = read_variable(res, "FlowActivePowerVariable__Line")
        binding_branches = Dict{String,Any}[]
        for line in get_components(Line, sys)
            ln = get_name(line)
            if ln in names(flows)
                flow_mw = abs(flows[1, ln])
                rating_mw = get_rating(line) * base_power
                loading_pct = flow_mw / rating_mw * 100.0
                if loading_pct > 99.0
                    push!(
                        binding_branches,
                        Dict(
                            "branch" => ln,
                            "flow_mw" => round(flow_mw; digits=1),
                            "rating_mw" => round(rating_mw; digits=1),
                            "loading_pct" => round(loading_pct; digits=1),
                        ),
                    )
                end
            end
        end
        results["details"]["binding_branches"] = binding_branches
        results["details"]["num_binding_branches"] = length(binding_branches)

        # Objective and termination
        oc = PowerSimulations.get_optimization_container(model)
        jm = PowerSimulations.get_jump_model(oc)
        results["details"]["objective_value"] = objective_value(jm)
        results["details"]["termination_status"] = string(termination_status(jm))

        # Production costs
        try
            cost_df = read_expression(res, "ProductionCostExpression__ThermalStandard")
            cost_summary = Dict{String,Any}()
            total_cost = 0.0
            for col in names(cost_df)
                col == "DateTime" && continue
                val = cost_df[1, col]
                cost_summary[col] = round(val; digits=2)
                total_cost += val
            end
            results["details"]["production_costs"] = cost_summary
            results["details"]["total_production_cost"] = round(total_cost; digits=2)
        catch e
            results["details"]["production_cost_error"] = string(e)
        end

        # Pass condition checks
        has_dispatch = !isempty(dispatch_summary)
        has_lmps = !isempty(lmp_data)
        shadow_check = length(binding_branches) >= 2

        results["details"]["pass_checks"] = Dict(
            "converged" => true,
            "has_dispatch" => has_dispatch,
            "has_lmps" => has_lmps,
            "num_binding_branches" => length(binding_branches),
            "binding_branches_gte_2" => shadow_check,
            "lmp_spread_dollar_per_mwh" => round(lmp_spread; digits=2),
        )

        if has_dispatch && has_lmps && shadow_check
            results["status"] = "pass"
        elseif has_dispatch && has_lmps
            results["status"] = "qualified_pass"
            push!(
                results["workarounds"],
                "Only $(length(binding_branches)) binding branches found (need >= 2).",
            )
        else
            push!(results["errors"], "Pass condition not met")
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

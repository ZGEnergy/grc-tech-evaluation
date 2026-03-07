#=
Test D-4a: Error quality — Infeasible OPF (line limit set to 0)

Dimension: accessibility
Network: TINY (case39.m — IEEE 39-bus)
Tool: PowerSimulations.jl v0.30.2

Tests whether the tool produces a meaningful diagnostic when a line's thermal
limit is set to 0, making the OPF infeasible.
=#

using PowerSystems
using PowerSimulations
using HiGHS
using JuMP
using Dates
using TimeSeries

function prepare_system_for_opf!(sys::System)
    # Fix generators with active_power > Pmax
    for gen in get_components(ThermalStandard, sys)
        p = get_active_power(gen)
        pmax = get_active_power_limits(gen).max
        if p > pmax
            set_active_power!(gen, pmax)
        end
    end

    resolution = Hour(1)
    initial_time = DateTime("2024-01-01T00:00:00")
    timestamps = [initial_time, initial_time + resolution]

    for gen in get_components(ThermalStandard, sys)
        ta = TimeArray(timestamps, [1.0, 1.0])
        ts = SingleTimeSeries("max_active_power", ta)
        add_time_series!(sys, gen, ts)
    end

    for gen in get_components(RenewableDispatch, sys)
        ta = TimeArray(timestamps, [1.0, 1.0])
        ts = SingleTimeSeries("max_active_power", ta)
        add_time_series!(sys, gen, ts)
    end

    for load in get_components(PowerLoad, sys)
        ta = TimeArray(timestamps, [1.0, 1.0])
        ts = SingleTimeSeries("max_active_power", ta)
        add_time_series!(sys, load, ts)
    end

    transform_single_time_series!(sys, resolution, resolution)
end

println("=" ^ 60)
println("D-4a: Infeasible OPF — setting a line rate to 0")
println("=" ^ 60)

sys = System("/workspace/data/networks/case39.m")
prepare_system_for_opf!(sys)

# Set a critical line's rate to 0 to force infeasibility
target_line = nothing
for line in get_components(Line, sys)
    target_line = line
    break
end

if target_line !== nothing
    println("\nTarget line: ", get_name(target_line))
    println("Original rate: ", get_rate(target_line))
    set_rate!(target_line, 0.0)
    println("New rate: ", get_rate(target_line))
end

# Build and solve
solver = optimizer_with_attributes(HiGHS.Optimizer, "time_limit" => 60.0, "output_flag" => true)

template = ProblemTemplate(NetworkModel(PTDFPowerModel; duals=[CopperPlateBalanceConstraint]))
set_device_model!(template, ThermalStandard, ThermalBasicDispatch)
set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
set_device_model!(template, PowerLoad, StaticPowerLoad)
set_device_model!(template, Line, StaticBranch)
set_device_model!(template, Transformer2W, StaticBranch)
set_device_model!(template, TapTransformer, StaticBranch)

println("\n--- Building model ---")
try
    model = DecisionModel(template, sys; optimizer=solver, store_variable_names=true)
    build_status = build!(model; output_dir=mktempdir())
    println("Build status: ", build_status)

    if occursin("BUILT", string(build_status))
        println("\n--- Solving model ---")
        solve_status = solve!(model)
        println("Solve status: ", solve_status)

        # Try to extract results
        try
            res = OptimizationProblemResults(model)
            obj = get_objective_value(res)
            println("Objective value: ", obj)
        catch e
            println("Result extraction error: ", typeof(e))
            println("  ", sprint(showerror, e))
        end
    end
catch e
    println("\nERROR caught: ", typeof(e))
    println("Message: ", sprint(showerror, e))
    println("\nFull traceback:")
    println(sprint(showerror, e, catch_backtrace()))
end

println("\n--- END D-4a ---")

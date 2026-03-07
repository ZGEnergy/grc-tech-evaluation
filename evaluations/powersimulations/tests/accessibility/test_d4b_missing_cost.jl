#=
Test D-4b: Error quality — Missing generator cost curve

Dimension: accessibility
Network: TINY (case39.m — IEEE 39-bus)
Tool: PowerSimulations.jl v0.30.2

Tests whether the tool produces a meaningful diagnostic when a generator's
cost data is removed/nullified.
=#

using PowerSystems
using PowerSimulations
using HiGHS
using JuMP
using Dates
using TimeSeries

function prepare_system_for_opf!(sys::System)
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
println("D-4b: Missing generator cost curve")
println("=" ^ 60)

sys = System("/workspace/data/networks/case39.m")

# Try to remove/nullify cost data from a generator before preparing
target_gen = nothing
for gen in get_components(ThermalStandard, sys)
    target_gen = gen
    break
end

if target_gen !== nothing
    println("\nTarget generator: ", get_name(target_gen))
    println("Original cost: ", get_operation_cost(target_gen))

    # Try setting operation cost to a zero/empty cost
    println("\n--- Attempting to set zero cost ---")
    try
        # Try setting a RenewableGenerationCost (wrong type for ThermalStandard)
        zero_cost = RenewableGenerationCost(nothing)
        set_operation_cost!(target_gen, zero_cost)
        println("Set RenewableGenerationCost on ThermalStandard")
    catch e
        println("Cannot set RenewableGenerationCost: ", typeof(e))
        println("  ", sprint(showerror, e))
    end

    # Try setting cost with zero coefficients
    println("\n--- Attempting to set cost with zero variable cost ---")
    try
        zero_var = CostCurve(LinearCurve(0.0))
        zero_thermal_cost = ThermalGenerationCost(zero_var, nothing, nothing, nothing)
        set_operation_cost!(target_gen, zero_thermal_cost)
        println("Set zero-coefficient ThermalGenerationCost successfully")
        println("New cost: ", get_operation_cost(target_gen))
    catch e
        println("Cannot set zero cost: ", typeof(e))
        println("  ", sprint(showerror, e))
    end
end

# Now prepare and build
prepare_system_for_opf!(sys)

solver = optimizer_with_attributes(HiGHS.Optimizer, "time_limit" => 60.0, "output_flag" => true)

template = ProblemTemplate(NetworkModel(PTDFPowerModel; duals=[CopperPlateBalanceConstraint]))
set_device_model!(template, ThermalStandard, ThermalBasicDispatch)
set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
set_device_model!(template, PowerLoad, StaticPowerLoad)
set_device_model!(template, Line, StaticBranch)
set_device_model!(template, Transformer2W, StaticBranch)
set_device_model!(template, TapTransformer, StaticBranch)

println("\n--- Building model with missing/zero cost ---")
try
    model = DecisionModel(template, sys; optimizer=solver, store_variable_names=true)
    build_status = build!(model; output_dir=mktempdir())
    println("Build status: ", build_status)

    if occursin("BUILT", string(build_status))
        println("\n--- Solving model ---")
        solve_status = solve!(model)
        println("Solve status: ", solve_status)

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

println("\n--- END D-4b ---")

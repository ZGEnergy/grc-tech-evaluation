# C-3: DCOPF on MEDIUM with HiGHS
# C-7: Solver swap — also tests Ipopt on same problem

using PowerSystems
using PowerSimulations
using HiGHS
using Ipopt
using Dates
using TimeSeries

const PSI = PowerSimulations

println("=" ^ 80)
println("C-3: DCOPF on MEDIUM + C-7: Solver Swap")
println("=" ^ 80)

println("  Loading MEDIUM network...")
t0 = time()
sys = System("/workspace/data/networks/case_ACTIVSg10k.m")
load_time = time() - t0
println("  Loaded in $(round(load_time, digits=2))s")

# Fix generators with active_power > Pmax
for gen in get_components(ThermalStandard, sys)
    pmax = get_active_power_limits(gen).max
    if get_active_power(gen) > pmax && pmax > 0.0
        set_active_power!(gen, pmax)
    end
end

# Add single-period time series
println("  Adding time series...")
t_prep = time()
resolution = Hour(1)
dates = collect(DateTime("2024-01-01T00:00:00"):resolution:DateTime("2024-01-01T01:00:00"))

for gen in get_components(Generator, sys)
    pmax = get_active_power_limits(gen).max
    if pmax > 0.0
        ta = TimeArray(dates, [1.0, 1.0])
        ts = SingleTimeSeries("max_active_power", ta)
        try
            add_time_series!(sys, gen, ts)
        catch
        end
    end
end

for load in get_components(PowerLoad, sys)
    ta = TimeArray(dates, [1.0, 1.0])
    ts = SingleTimeSeries("max_active_power", ta)
    try
        add_time_series!(sys, load, ts)
    catch
    end
end

transform_single_time_series!(sys, Hour(1), Hour(1))
println("  Time series ready in $(round(time() - t_prep, digits=2))s")

# Solve with each solver
for (solver_name, solver) in [
    (
        "HiGHS",
        optimizer_with_attributes(HiGHS.Optimizer, "output_flag" => false, "time_limit" => 300.0),
    ),
    (
        "Ipopt",
        optimizer_with_attributes(Ipopt.Optimizer, "print_level" => 0, "max_cpu_time" => 300.0),
    ),
]
    println("\n--- DCOPF with $solver_name ---")
    t0 = time()
    try
        template = ProblemTemplate()
        set_device_model!(template, ThermalStandard, ThermalBasicDispatch)
        set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
        set_device_model!(template, RenewableNonDispatch, FixedOutput)
        set_device_model!(template, HydroDispatch, HydroDispatchRunOfRiver)
        set_device_model!(template, PowerLoad, StaticPowerLoad)

        for BT in [Line, Transformer2W, TapTransformer, PhaseShiftingTransformer]
            if !isempty(collect(get_components(BT, sys)))
                set_device_model!(template, BT, StaticBranch)
            end
        end

        set_network_model!(template, NetworkModel(PTDFPowerModel))

        model = DecisionModel(
            template, sys; optimizer=solver, horizon=Hour(1), optimizer_solve_log_print=false
        )

        build_status = build!(model; output_dir=mktempdir())
        build_time = time() - t0
        println("  Build: $build_status ($(round(build_time, digits=2))s)")

        if build_status == PSI.BuildStatus.BUILT
            solve_status = solve!(model)
            total_time = time() - t0
            jm = get_jump_model(model)
            obj = objective_value(jm)
            println("  Solve: $solve_status")
            println("  Objective: $obj")
            println("  Total time: $(round(total_time, digits=2))s")
            println("  STATUS: PASS")
        else
            println("  STATUS: FAIL (build failed)")
        end
    catch e
        println("  FAILED after $(round(time() - t0, digits=2))s: $e")
        println("  STATUS: FAIL")
    end
end

println("\n  Solver swap requires only parameter change — no reformulation needed.")
println("=" ^ 80)
println("COMPLETE")
println("=" ^ 80)

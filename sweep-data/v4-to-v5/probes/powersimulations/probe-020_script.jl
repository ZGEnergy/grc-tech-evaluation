# Probe 020: Verify DCOPF timing on ACTIVSg 10k network
# Claim: C-3 reports estimated timing without actual measurement (wall_clock_seconds: null)

using PowerSystems
using PowerSimulations
using HiGHS
using JuMP
using Dates
using Statistics
using TimeSeries

println("=" ^ 60)
println("Probe 020: DCOPF timing on ACTIVSg 10k")
println("=" ^ 60)

# --- Load system ---
println("\n--- Loading ACTIVSg 10k network ---")
t_load = @elapsed begin
    sys = System("/workspace/data/networks/case_ACTIVSg10k.m")
end
println("System load time: $(round(t_load, digits=2))s")

buses = collect(get_components(ACBus, sys))
println("Buses: $(length(buses))")
thermals = collect(get_components(ThermalStandard, sys))
println("ThermalStandard: $(length(thermals))")
renew_disp = collect(get_components(RenewableDispatch, sys))
println("RenewableDispatch: $(length(renew_disp))")

lines = collect(get_components(Line, sys))
transformers2w = collect(get_components(Transformer2W, sys))
tap_transformers = collect(get_components(TapTransformer, sys))
println(
    "Lines: $(length(lines)), Transformer2W: $(length(transformers2w)), TapTransformer: $(length(tap_transformers))",
)

all_gens = collect(get_components(Generator, sys))
println("Total generators: $(length(all_gens))")

# --- Fix generators with active_power > Pmax ---
println("\n--- Fixing generator limits ---")
fix_count = 0
for gen in thermals
    try
        lims = get_active_power_limits(gen)
        if get_active_power(gen) > lims.max
            set_active_power!(gen, lims.max)
            fix_count += 1
        end
    catch
    end
end
# For RenewableDispatch, use rating or max_active_power
for gen in renew_disp
    try
        lims = get_active_power_limits(gen)
        if get_active_power(gen) > lims.max
            set_active_power!(gen, lims.max)
            fix_count += 1
        end
    catch e
        # Try alternative: just clamp to rating
        try
            r = get_rating(gen)
            if get_active_power(gen) > r
                set_active_power!(gen, r)
                fix_count += 1
            end
        catch
        end
    end
end
println("Fixed $fix_count generators")

# --- Add time series ---
println("\n--- Adding time series ---")
t_ts = @elapsed begin
    resolution = Dates.Hour(1)
    dates = collect(DateTime("2024-01-01T00:00:00"):resolution:DateTime("2024-01-01T23:00:00"))

    for gen in get_components(Generator, sys)
        ta = TimeArray(dates, ones(length(dates)))
        ts = SingleTimeSeries("max_active_power", ta)
        add_time_series!(sys, gen, ts)
    end

    for load in get_components(PowerLoad, sys)
        ta = TimeArray(dates, ones(length(dates)))
        ts = SingleTimeSeries("max_active_power", ta)
        add_time_series!(sys, load, ts)
    end

    transform_single_time_series!(sys, Hour(24), Hour(1))
end
println("Time series setup: $(round(t_ts, digits=2))s")

# --- Build and solve DCOPF ---
function build_and_solve_dcopf(sys)
    template = ProblemTemplate(PTDFPowerModel)
    set_device_model!(template, ThermalStandard, ThermalBasicDispatch)
    set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
    set_device_model!(template, PowerLoad, StaticPowerLoad)
    set_device_model!(template, Line, StaticBranch)
    set_device_model!(template, Transformer2W, StaticBranch)
    set_device_model!(template, TapTransformer, StaticBranch)

    solver = optimizer_with_attributes(HiGHS.Optimizer, "output_flag" => false)

    model = DecisionModel(
        template,
        sys;
        optimizer=solver,
        horizon=Hour(1),
        initial_time=DateTime("2024-01-01T00:00:00"),
        optimizer_solve_log_print=false,
        store_variable_names=true,
    )

    build_status = build!(model; output_dir=mktempdir())
    solve_status = solve!(model)

    return model, build_status, solve_status
end

# Run 1 (includes JIT)
println("\n--- Run 1 (includes JIT) ---")
flush(stdout)
t1 = @elapsed begin
    model1, bs1, ss1 = build_and_solve_dcopf(sys)
end
println("Run 1: $(round(t1, digits=2))s  build=$(bs1)  solve=$(ss1)")
flush(stdout)

# Run 2
println("\n--- Run 2 ---")
flush(stdout)
t2 = @elapsed begin
    model2, bs2, ss2 = build_and_solve_dcopf(sys)
end
println("Run 2: $(round(t2, digits=2))s  build=$(bs2)  solve=$(ss2)")
flush(stdout)

# Run 3
println("\n--- Run 3 ---")
flush(stdout)
t3 = @elapsed begin
    model3, bs3, ss3 = build_and_solve_dcopf(sys)
end
println("Run 3: $(round(t3, digits=2))s  build=$(bs3)  solve=$(ss3)")
flush(stdout)

# --- Summary ---
times = [t1, t2, t3]
warm_times = [t2, t3]

println("\n" * "=" ^ 60)
println("TIMING SUMMARY")
println("=" ^ 60)
println(
    "All runs:  mean=$(round(mean(times), digits=2))s  median=$(round(median(times), digits=2))s  min=$(round(minimum(times), digits=2))s  max=$(round(maximum(times), digits=2))s",
)
println(
    "Warm runs: mean=$(round(mean(warm_times), digits=2))s  median=$(round(median(warm_times), digits=2))s  min=$(round(minimum(warm_times), digits=2))s  max=$(round(maximum(warm_times), digits=2))s",
)
println("\nSystem load time: $(round(t_load, digits=2))s")
println("Time series setup: $(round(t_ts, digits=2))s")
println(
    "\nOriginal claim: wall_clock_seconds=null, estimated <60s for HiGHS QP with ~15k constraints"
)
println("Probe measured: $(round(minimum(warm_times), digits=2))s (best warm run)")

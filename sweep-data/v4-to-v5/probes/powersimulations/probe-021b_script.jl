# Probe 021b: Quick follow-up - check read_variables API output values
using PowerSystems
using PowerSimulations
using HiGHS
using JuMP
using Dates
using TimeSeries
using DataFrames

sys = System("/workspace/data/networks/case39.m")
thermals = collect(get_components(ThermalStandard, sys))

# Fix gen-2
for gen in thermals
    lims = get_active_power_limits(gen)
    if get_active_power(gen) > lims.max
        set_active_power!(gen, lims.max)
    end
end

# Time series
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

# Build + solve
template = ProblemTemplate(PTDFPowerModel)
set_device_model!(template, ThermalStandard, ThermalBasicDispatch)
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
build!(model; output_dir=mktempdir())
solve!(model)

# Read results
res = OptimizationProblemResults(model)
vars = read_variables(res)

# Access ActivePowerVariable__ThermalStandard directly by string key
ap_key = "ActivePowerVariable__ThermalStandard"
if haskey(vars, ap_key)
    ap_df = vars[ap_key]
    println("ActivePowerVariable__ThermalStandard from read_variables():")
    println(ap_df)

    println("\n--- Comparison ---")
    println(
        rpad("Gen", 10) *
        rpad("API_val", 15) *
        rpad("JuMP_val", 15) *
        rpad("Pmax_pu", 12) *
        rpad("Pmax_MW", 12) *
        rpad("API/Pmax_pu", 12),
    )
    println("-"^76)

    for gen in thermals
        gname = get_name(gen)
        lims = get_active_power_limits(gen)
        bp = get_base_power(gen)

        if gname in names(ap_df)
            api_val = ap_df[1, gname]

            # Get JuMP value
            jm = model.internal.container.JuMPmodel
            all_v = all_variables(jm)
            jv = filter(
                v -> occursin(gname, string(name(v))) && occursin("ActivePower", string(name(v))),
                all_v,
            )
            jump_val = length(jv) > 0 ? value(first(jv)) : NaN

            ratio = api_val / lims.max
            println(
                rpad(gname, 10) *
                rpad(string(round(api_val; digits=4)), 15) *
                rpad(string(round(jump_val; digits=4)), 15) *
                rpad(string(round(lims.max; digits=4)), 12) *
                rpad(string(round(lims.max * bp; digits=1)), 12) *
                rpad(string(round(ratio; digits=2)), 12),
            )
        end
    end
else
    println("Key '$ap_key' not found. Available keys:")
    for k in keys(vars)
        println("  '$k' ($(typeof(k)))")
    end
end

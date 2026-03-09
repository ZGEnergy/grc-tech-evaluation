# Probe 021: Verify PSI dispatch values are ~100x larger than component limits
# Claim from A-4: "dispatch values returned by PSI are ~100x larger than Pmax"

using PowerSystems
using PowerSimulations
using HiGHS
using JuMP
using Dates
using TimeSeries
using DataFrames

println("=" ^ 60)
println("Probe 021: PSI dispatch units verification")
println("=" ^ 60)

# --- Load system ---
println("\n--- Loading IEEE 39-bus network ---")
sys = System("/workspace/data/networks/case39.m")

thermals = collect(get_components(ThermalStandard, sys))
println("ThermalStandard generators: $(length(thermals))")
println("Unit system: $(get_units_base(sys))")

println("\n--- Generator limits (system-base pu on 100 MVA base) ---")
for gen in thermals
    name = get_name(gen)
    lims = get_active_power_limits(gen)
    bp = get_base_power(gen)
    println(
        "  $name: Pmax=$(round(lims.max, digits=4)) pu = $(round(lims.max * bp, digits=1)) MW (base_power=$bp)",
    )
end

# Fix gen-2
for gen in thermals
    lims = get_active_power_limits(gen)
    if get_active_power(gen) > lims.max
        println("\nFixing $(get_name(gen)): $(get_active_power(gen)) -> $(lims.max)")
        set_active_power!(gen, lims.max)
    end
end

# --- Add time series ---
println("\n--- Adding time series ---")
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
println("Time series added and transformed")

# --- Build and solve DCOPF ---
println("\n--- Building and solving DCOPF ---")

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

build_status = build!(model; output_dir=mktempdir())
println("Build: $build_status")
solve_status = solve!(model)
println("Solve: $solve_status")

obj = objective_value(model.internal.container.JuMPmodel)
println("Objective value: $obj")

# --- Extract dispatch via results API ---
println("\n--- Extracting dispatch results ---")

res = OptimizationProblemResults(model)
vars = read_variables(res)

# Print all keys and their types
println("Variable keys:")
for (k, v) in vars
    println("  key=$(k)  type=$(typeof(k))  df_cols=$(names(v))")
end

# Get the ActivePower ThermalStandard data - try direct string access
ap_df = nothing
for (k, v) in vars
    ks = string(k)
    if occursin("ActivePower", ks) && occursin("ThermalStandard", ks)
        ap_df = v
        break
    end
end

if ap_df !== nothing
    println("\n--- DISPATCH VALUES vs COMPONENT LIMITS ---")
    println(
        rpad("Generator", 12) *
        rpad("Dispatch", 12) *
        rpad("Pmax(pu)", 12) *
        rpad("Pmax(MW)", 12) *
        rpad("Ratio", 10) *
        "Assessment",
    )
    println("-"^70)

    col_names = names(ap_df)
    for gen in thermals
        gname = get_name(gen)
        lims = get_active_power_limits(gen)
        bp = get_base_power(gen)
        pmax_mw = lims.max * bp

        if gname in col_names
            dispatch_val = ap_df[1, gname]
            ratio_to_pu = dispatch_val / lims.max
            ratio_to_mw = dispatch_val / pmax_mw

            assessment = ""
            if abs(ratio_to_pu - 1.0) < 0.1
                assessment = "~1x Pmax(pu) -> dispatch is in pu"
            elseif abs(ratio_to_mw - 1.0) < 0.1
                assessment = "~1x Pmax(MW) -> dispatch is in MW"
            elseif abs(ratio_to_pu - 100.0) < 20.0
                assessment = "~100x Pmax(pu) -> UNIT MISMATCH"
            else
                assessment = "ratio=$(round(ratio_to_pu, digits=1))x"
            end

            println(
                rpad(gname, 12) *
                rpad(string(round(dispatch_val; digits=2)), 12) *
                rpad(string(round(lims.max; digits=4)), 12) *
                rpad(string(round(pmax_mw; digits=1)), 12) *
                rpad(string(round(ratio_to_pu; digits=2)), 10) *
                assessment,
            )
        else
            println("$gname: NOT FOUND in dispatch results")
        end
    end
else
    println("ERROR: Could not find ActivePower ThermalStandard variable")
    # Try to directly access JuMP variables
    println("\n--- Attempting direct JuMP variable access ---")
    jm = model.internal.container.JuMPmodel
    all_vars = all_variables(jm)
    println("Total JuMP variables: $(length(all_vars))")
    for v in all_vars[1:min(20, length(all_vars))]
        println("  $(name(v)) = $(value(v))")
    end
end

# --- Also try direct JuMP access for comparison ---
println("\n--- Direct JuMP variable values ---")
try
    jm = model.internal.container.JuMPmodel
    all_vars = all_variables(jm)
    ap_vars = filter(
        v ->
            occursin("ActivePower", string(name(v))) &&
            occursin("ThermalStandard", string(name(v))),
        all_vars,
    )
    println("ActivePower ThermalStandard JuMP variables:")
    for v in ap_vars
        println("  $(name(v)) = $(value(v))")
    end
catch e
    println("JuMP access error: $e")
end

println("\n" * "=" ^ 60)
println("CONCLUSION")
println("=" ^ 60)

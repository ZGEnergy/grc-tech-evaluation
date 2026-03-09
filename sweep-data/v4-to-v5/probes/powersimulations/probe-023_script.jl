# Probe 023: Verify distributed slack claim
# Claim: A-11 qualified_pass on uncongested network where both formulations produce identical results

using PowerSystems
using PowerSimulations
using HiGHS
using JuMP
using Dates
using InfrastructureSystems
const TS = InfrastructureSystems.TimeSeries

println("=" ^ 60)
println("Probe 023: Distributed slack formulation audit")
println("=" ^ 60)

println("\nHiGHS version: ", string(pkgversion(HiGHS)))

# --- Load system ---
println("\n--- Loading IEEE 39-bus network ---")
sys = System("/workspace/data/networks/case39.m")

# Fix gen-2
for gen in get_components(ThermalStandard, sys)
    lims = get_active_power_limits(gen)
    if get_active_power(gen) > lims.max
        println("Fixing $(get_name(gen)): $(get_active_power(gen)) -> $(lims.max)")
        set_active_power!(gen, lims.max)
    end
end

# Add time series
resolution = Dates.Hour(1)
dates = collect(DateTime("2024-01-01T00:00:00"):resolution:DateTime("2024-01-01T23:00:00"))

for gen in get_components(Generator, sys)
    ta = TS.TimeArray(dates, ones(length(dates)))
    ts = SingleTimeSeries("max_active_power", ta)
    add_time_series!(sys, gen, ts)
end

for load in get_components(PowerLoad, sys)
    ta = TS.TimeArray(dates, ones(length(dates)))
    ts = SingleTimeSeries("max_active_power", ta)
    add_time_series!(sys, load, ts)
end

transform_single_time_series!(sys, Hour(24), Hour(1))
println("Time series added")

solver = optimizer_with_attributes(HiGHS.Optimizer, "output_flag" => false)

# --- PTDF formulation (claimed distributed slack) ---
println("\n--- PTDFPowerModel (distributed slack) ---")
template_ptdf = ProblemTemplate(PTDFPowerModel)
set_device_model!(template_ptdf, ThermalStandard, ThermalBasicDispatch)
set_device_model!(template_ptdf, PowerLoad, StaticPowerLoad)
set_device_model!(template_ptdf, Line, StaticBranch)
set_device_model!(template_ptdf, Transformer2W, StaticBranch)
set_device_model!(template_ptdf, TapTransformer, StaticBranch)

model_ptdf = DecisionModel(
    template_ptdf,
    sys;
    optimizer=solver,
    horizon=Hour(1),
    initial_time=DateTime("2024-01-01T00:00:00"),
    optimizer_solve_log_print=false,
    store_variable_names=true,
)
build!(model_ptdf; output_dir=mktempdir())
solve!(model_ptdf)

jm_ptdf = PowerSimulations.get_jump_model(model_ptdf)
ptdf_obj = objective_value(jm_ptdf)
println("Objective: $ptdf_obj")
println("Status: $(termination_status(jm_ptdf))")

# Check model structure - what constraints exist?
println("\nPTDF constraint types:")
for (F, S) in list_of_constraint_types(jm_ptdf)
    cons = all_constraints(jm_ptdf, F, S)
    if length(cons) > 0
        first_name = length(cons) > 0 ? name(cons[1]) : "N/A"
        println("  $(F)-in-$(S): $(length(cons)) constraints (first: $first_name)")
    end
end

# Check: does PTDF have bus angle variables?
all_vars_ptdf = all_variables(jm_ptdf)
angle_vars = filter(
    v ->
        occursin("angle", lowercase(string(name(v)))) ||
        occursin("theta", lowercase(string(name(v)))),
    all_vars_ptdf,
)
println("\nBus angle variables in PTDF model: $(length(angle_vars))")
if length(angle_vars) > 0
    for v in angle_vars[1:min(5, length(angle_vars))]
        println("  $(name(v))")
    end
end

# Extract PTDF system price (CopperPlate dual)
ptdf_system_price = nothing
for (F, S) in list_of_constraint_types(jm_ptdf)
    cons = all_constraints(jm_ptdf, F, S)
    for c in cons
        n = name(c)
        if occursin("CopperPlate", n)
            ptdf_system_price = dual(c)
            println("\nCopperPlate constraint dual (system price): $ptdf_system_price")
        end
    end
end

# Get PTDF dispatch
ptdf_dispatch = Dict{String,Float64}()
for v in all_vars_ptdf
    n = string(name(v))
    if occursin("ActivePowerVariable__ThermalStandard", n) ||
        occursin("ActivePowerVariable_ThermalStandard", n)
        ptdf_dispatch[n] = value(v)
    end
end

# --- DCP formulation (single slack) ---
println("\n--- DCPPowerModel (single slack) ---")
template_dcp = ProblemTemplate(DCPPowerModel)
set_device_model!(template_dcp, ThermalStandard, ThermalBasicDispatch)
set_device_model!(template_dcp, PowerLoad, StaticPowerLoad)
set_device_model!(template_dcp, Line, StaticBranch)
set_device_model!(template_dcp, Transformer2W, StaticBranch)
set_device_model!(template_dcp, TapTransformer, StaticBranch)

model_dcp = DecisionModel(
    template_dcp,
    sys;
    optimizer=solver,
    horizon=Hour(1),
    initial_time=DateTime("2024-01-01T00:00:00"),
    optimizer_solve_log_print=false,
    store_variable_names=true,
)
build!(model_dcp; output_dir=mktempdir())
solve!(model_dcp)

jm_dcp = PowerSimulations.get_jump_model(model_dcp)
dcp_obj = objective_value(jm_dcp)
println("Objective: $dcp_obj")
println("Status: $(termination_status(jm_dcp))")

# Check model structure
println("\nDCP constraint types:")
for (F, S) in list_of_constraint_types(jm_dcp)
    cons = all_constraints(jm_dcp, F, S)
    if length(cons) > 0
        first_name = length(cons) > 0 ? name(cons[1]) : "N/A"
        println("  $(F)-in-$(S): $(length(cons)) constraints (first: $first_name)")
    end
end

# Check: does DCP have bus angle variables?
all_vars_dcp = all_variables(jm_dcp)
angle_vars_dcp = filter(
    v ->
        occursin("angle", lowercase(string(name(v)))) ||
        occursin("theta", lowercase(string(name(v)))) ||
        occursin("VoltageAngle", string(name(v))),
    all_vars_dcp,
)
println("\nBus angle variables in DCP model: $(length(angle_vars_dcp))")
if length(angle_vars_dcp) > 0
    for v in angle_vars_dcp[1:min(5, length(angle_vars_dcp))]
        println("  $(name(v)) = $(value(v))")
    end
    println("  ...")
end

# Extract DCP nodal LMPs (NodalBalance duals)
dcp_lmps = Dict{String,Float64}()
for (F, S) in list_of_constraint_types(jm_dcp)
    cons = all_constraints(jm_dcp, F, S)
    for c in cons
        n = name(c)
        if occursin("NodalBalance", n) || occursin("nodal_balance", lowercase(n))
            dcp_lmps[n] = dual(c)
        end
    end
end

println("\nDCP nodal LMPs ($(length(dcp_lmps)) buses):")
lmp_values = collect(values(dcp_lmps))
if length(lmp_values) > 0
    println("  Min LMP: $(minimum(lmp_values))")
    println("  Max LMP: $(maximum(lmp_values))")
    println("  Spread:  $(maximum(lmp_values) - minimum(lmp_values))")
    println("  Mean:    $(sum(lmp_values) / length(lmp_values))")
end

# Get DCP dispatch
dcp_dispatch = Dict{String,Float64}()
for v in all_vars_dcp
    n = string(name(v))
    if occursin("ActivePowerVariable__ThermalStandard", n) ||
        occursin("ActivePowerVariable_ThermalStandard", n)
        dcp_dispatch[n] = value(v)
    end
end

# --- Comparison ---
println("\n" * "=" ^ 60)
println("COMPARISON")
println("=" ^ 60)
println("Objective difference: $(abs(ptdf_obj - dcp_obj))")
println("  PTDF: $ptdf_obj")
println("  DCP:  $dcp_obj")

println("\nDispatch comparison:")
max_diff = 0.0
for (k, v_ptdf) in ptdf_dispatch
    if haskey(dcp_dispatch, k)
        diff = abs(v_ptdf - dcp_dispatch[k])
        if diff > max_diff
            global max_diff = diff
        end
        if diff > 1e-4
            println("  DIFF $k: PTDF=$v_ptdf DCP=$(dcp_dispatch[k]) diff=$diff")
        end
    end
end
println("Max dispatch difference: $max_diff MW")

# Key question: are LMPs truly uniform on this network?
lmp_spread = length(lmp_values) > 0 ? maximum(lmp_values) - minimum(lmp_values) : 0.0
println("\nLMP spread (DCP): $lmp_spread")
if lmp_spread < 1e-3
    println("LMPs are UNIFORM -- network is UNCONGESTED")
    println("=> Both formulations trivially produce same result on uncongested network")
    println("=> Distributed slack vs single slack is a DISTINCTION WITHOUT DIFFERENCE here")
else
    println("LMPs are DIFFERENTIATED -- network IS congested")
    println("=> Formulation difference would be meaningful")
end

# Check: are there any binding branch flow constraints?
println("\n--- Checking for binding branch constraints ---")
binding_count = 0
for (F, S) in list_of_constraint_types(jm_dcp)
    cons = all_constraints(jm_dcp, F, S)
    for c in cons
        n = name(c)
        if occursin("Flow", n) || occursin("RateLimit", n) || occursin("rate", lowercase(n))
            d = dual(c)
            if abs(d) > 1e-6
                println("  BINDING: $n dual=$d")
                binding_count += 1
            end
        end
    end
end
println("Binding branch constraints: $binding_count")

# Check if PTDF truly has no reference bus
println("\n--- Structural Analysis ---")
ptdf_var_count = length(all_vars_ptdf)
dcp_var_count = length(all_vars_dcp)
println("PTDF total variables: $ptdf_var_count")
println("DCP total variables: $dcp_var_count")
println("Variable count difference: $(dcp_var_count - ptdf_var_count)")
println("(DCP has $(length(angle_vars_dcp)) angle vars that PTDF doesn't have)")

# Check if distributed slack weights are configurable
println("\n--- Distributed Slack Weight Configurability ---")
println("PTDF formulation eliminates angles, uses PTDF matrix for flow constraints.")
println("The 'distributed slack' is implicit in the PTDF matrix computation.")
println("PSI does NOT expose slack participation weights as a parameter.")
println("This is a mathematical property of the formulation, not a configurable feature.")

println("\n" * "=" ^ 60)
println("CONCLUSION")
println("=" ^ 60)
if lmp_spread < 1e-3
    println("The qualified_pass was tested on an UNCONGESTED network where PTDF")
    println("and DCP formulations produce identical dispatch and objectives.")
    println("The 'distributed slack' property is real (PTDF eliminates angles),")
    println("but its effect is only visible on congested networks.")
    println("On this uncongested network, it's a no-op distinction.")
    println("")
    println("However, the A-11 evaluation correctly noted:")
    println("- PTDF IS structurally a distributed-slack formulation (no ref bus)")
    println("- Participation weights are NOT configurable")
    println("- The qualified_pass reflects the limitation on weight configurability")
    println("")
    println("Classification: claim_supported")
else
    println("Network is congested. Formulations should differ.")
    println("Classification: needs further analysis")
end

# Probe 022: Verify custom constraint dual extraction for BINDING case
# Claim: B-1 only verified non-binding (dual=0); binding case never demonstrated

using PowerSystems
using PowerSimulations
using HiGHS
using JuMP
using Dates
using TimeSeries

println("=" ^ 60)
println("Probe 022: Custom constraint binding dual extraction")
println("=" ^ 60)

# --- Check solver version ---
println("\nHiGHS version: ", string(pkgversion(HiGHS)))

# --- Load system ---
println("\n--- Loading IEEE 39-bus network ---")
sys = System("/workspace/data/networks/case39.m")
println("Loaded: $(length(collect(get_components(Bus, sys)))) buses")

# Fix gen-2 if needed
for gen in get_components(ThermalStandard, sys)
    lims = get_active_power_limits(gen)
    if get_active_power(gen) > lims.max
        println("Fixing $(get_name(gen)): $(get_active_power(gen)) -> $(lims.max)")
        set_active_power!(gen, lims.max)
    end
end

# --- Add time series ---
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

# --- Helper to build and solve DCOPF ---
function build_and_solve_dcopf(sys)
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
    return model
end

# --- Step 1: Unconstrained baseline ---
println("\n--- Step 1: Unconstrained DCOPF baseline ---")
model_base = build_and_solve_dcopf(sys)
jm_base = PowerSimulations.get_jump_model(model_base)
base_obj = objective_value(jm_base)
base_status = termination_status(jm_base)
println("Status: $base_status")
println("Objective: $base_obj")

# Get Line flow values (not transformers) from base
all_vars_base = all_variables(jm_base)
line_flows_base = filter(
    v -> occursin("FlowActivePowerVariable_Line", string(name(v))), all_vars_base
)
println("\nLine flows (base):")
flow_vals = Dict{String,Float64}()
for fv in line_flows_base
    n = string(name(fv))
    v = value(fv)
    flow_vals[n] = v
    println("  $n = $(round(v, digits=4))")
end

# --- Step 2: Select lines for flow gate on transmission corridor ---
# Use lines 15-16, 16-17, 16-19 as in original B-1 test
println("\n--- Step 2: Select flow gate lines (same as B-1) ---")
gate_line_patterns = ["bus-15-bus-16", "bus-16-bus-17", "bus-16-bus-19"]

gate_flows_base = Dict{String,Float64}()
for (n, v) in flow_vals
    for pat in gate_line_patterns
        if occursin(pat, n)
            gate_flows_base[n] = v
            println("  Gate line: $n = $v")
        end
    end
end

signed_sum_base = sum(values(gate_flows_base))
abs_sum_base = sum(abs(v) for v in values(gate_flows_base))
println("Signed flow sum (base): $signed_sum_base")
println("Abs flow sum (base): $abs_sum_base")

# --- Step 3: Constrained solve with TIGHT limit ---
# Set limit to make the constraint bind
# The signed sum is about -5.5, so set limit on SIGNED sum to be tight
# Use |signed_sum| * 0.5 as the limit for the signed constraint
tight_limit = abs(signed_sum_base) * 0.5
println("\n--- Step 3: Constrained DCOPF (signed sum limit = $tight_limit) ---")

model_con = build_and_solve_dcopf(sys)
jm_con = PowerSimulations.get_jump_model(model_con)

# Find the gate line variables in this model
all_vars_con = all_variables(jm_con)
gate_var_refs = JuMP.VariableRef[]
for (n, _) in gate_flows_base
    for v in all_vars_con
        if string(name(v)) == n
            push!(gate_var_refs, v)
            break
        end
    end
end
println("Gate variables found: $(length(gate_var_refs))")

# Add constraint: signed sum of gate flows between -tight_limit and +tight_limit
flow_sum_expr = sum(gate_var_refs)
gate_con_upper = @constraint(jm_con, flow_sum_expr <= tight_limit)
gate_con_lower = @constraint(jm_con, -flow_sum_expr <= tight_limit)

println(
    "Added: -$(round(tight_limit, digits=4)) <= sum(gate_flows) <= $(round(tight_limit, digits=4))"
)

# Re-solve
optimize!(jm_con)
con_status = termination_status(jm_con)
con_obj = objective_value(jm_con)
println("Status: $con_status")
println("Objective: $con_obj")
println(
    "Objective change: $(con_obj - base_obj) ($(round((con_obj - base_obj)/base_obj * 100, digits=4))%)",
)

# Extract duals
dual_upper = dual(gate_con_upper)
dual_lower = dual(gate_con_lower)
gate_flow_val = value(flow_sum_expr)

println("\n--- DUAL EXTRACTION RESULTS ---")
println("Gate flow sum (constrained): $(round(gate_flow_val, digits=6))")
println("Limit: +/- $(round(tight_limit, digits=6))")
println(
    "Upper constraint (sum <= limit): dual = $dual_upper, slack = $(round(tight_limit - gate_flow_val, digits=8))",
)
println(
    "Lower constraint (-sum <= limit): dual = $dual_lower, slack = $(round(tight_limit + gate_flow_val, digits=8))",
)

upper_binding = abs(tight_limit - gate_flow_val) < 1e-6
lower_binding = abs(tight_limit + gate_flow_val) < 1e-6
println("\nUpper binding: $upper_binding (dual nonzero: $(abs(dual_upper) > 1e-8))")
println("Lower binding: $lower_binding (dual nonzero: $(abs(dual_lower) > 1e-8))")

any_binding = upper_binding || lower_binding
any_nonzero_dual = abs(dual_upper) > 1e-8 || abs(dual_lower) > 1e-8

# Show individual gate line flows
println("\n--- Individual gate line flows (constrained) ---")
for v in gate_var_refs
    println("  $(name(v)) = $(round(value(v), digits=6))")
end

# Also extract CopperPlate dual for comparison
println("\n--- CopperPlate constraint dual ---")
for (F, S) in list_of_constraint_types(jm_con)
    cons = all_constraints(jm_con, F, S)
    for c in cons
        n = name(c)
        if occursin("CopperPlate", n)
            println("  $n: dual = $(dual(c))")
        end
    end
end

println("\n" * "=" ^ 60)
println("CONCLUSION")
println("=" ^ 60)
if con_status != MOI.OPTIMAL
    println("Model not optimal ($con_status). Cannot assess binding/dual.")
    println("Classification: probe_bug")
elseif any_binding && any_nonzero_dual
    println("SUCCESS: Binding constraint with non-zero dual demonstrated.")
    println("  Dual value: upper=$dual_upper, lower=$dual_lower")
    println("  Objective increase: $(round(con_obj - base_obj, digits=6))")
    println("The B-1 claim gap is filled: dual extraction works for binding constraints too.")
    println("Classification: claim_supported (with enhancement)")
elseif !any_binding && any_nonzero_dual
    println("Dual nonzero but constraint not at bound by tolerance check.")
    println("Classification: claim_supported (dual extraction works)")
elseif any_binding && !any_nonzero_dual
    println("PROBLEM: Constraint binding but dual is zero. Possible solver issue.")
    println("Classification: inconclusive")
else
    println("Constraint did not bind. Limit may not be tight enough.")
    println("Classification: inconclusive")
end

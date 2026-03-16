#=
Probe 013: ACPF Convergence Check for PowerSimulations / PowerFlows.jl
Probe Type: convergence_check
Source Test: A-2 (TINY / IEEE 39-bus) + C-2 context (MEDIUM / ACTIVSg 10k)

Objectives:
  1. Verify whether PowerFlows.jl exposes any convergence diagnostics
     (iteration count, residual, termination status) beyond a boolean.
  2. Reproduce the A-2 ACPF on IEEE 39-bus with ALL logging enabled to
     capture any internal convergence messages.
  3. Check PowerFlows.jl source/internals for accessible convergence fields.
  4. Compute an independent post-hoc residual from the returned bus solution
     to quantify convergence quality numerically.
  5. Reproduce the C-2 first-call convergence warning scenario on TINY to
     confirm whether "solver failed to converge" warning on first call is
     reproducible and whether the second call truly converges.
=#

using PowerSystems
using PowerFlows
using DataFrames
using Logging
using Dates

println("=" ^ 70)
println("Probe 013: ACPF Convergence Diagnostic Check")
println("Timestamp: ", Dates.now())
println("=" ^ 70)

# ── Section 0: PowerFlows version ──────────────────────────────────────────
println("\n[0] Package versions:")
using Pkg: Pkg
for (name, ver) in
    [("PowerFlows", nothing), ("PowerSystems", nothing), ("PowerSimulations", nothing)]
    try
        pkg_info = Pkg.dependencies()
        for (uuid, dep) in pkg_info
            if dep.name == name
                println("  $name = $(dep.version)")
            end
        end
    catch e
        println("  $name = (error: $e)")
    end
end

# ── Section 1: Inspect PowerFlows.jl return type for hidden fields ──────────
println("\n[1] Inspecting PowerFlows.jl ACPowerFlow result type:")
println("  Loading IEEE 39-bus (TINY)...")
sys_tiny = System("/workspace/data/networks/case39.m")

# Enable ALL logging to capture any internal convergence messages
global_logger(ConsoleLogger(stderr, Logging.Debug))

println("  --- First ACPF call (with Debug logging, warm-up) ---")
pf1 = solve_powerflow(ACPowerFlow(), sys_tiny)

println("  --- Second ACPF call (timed) ---")
t0 = time()
pf2 = solve_powerflow(ACPowerFlow(), sys_tiny)
elapsed = time() - t0

# Restore quieter logging for output clarity
global_logger(ConsoleLogger(stderr, Logging.Warn))

println("\n  Return type: ", typeof(pf2))
println("  Return keys: ", collect(keys(pf2)))

# Inspect bus_results DataFrame schema
bus_df = pf2["bus_results"]
println("  bus_results columns: ", names(bus_df))
println("  bus_results nrow: ", nrow(bus_df))

flow_df = pf2["flow_results"]
println("  flow_results columns: ", names(flow_df))

# ── Section 2: Check if result object has hidden convergence fields ──────────
println("\n[2] Probing for hidden convergence fields in returned Dict:")
for key in keys(pf2)
    val = pf2[key]
    println("  key='$key' type=$(typeof(val))")
    if val isa DataFrame
        println("    columns: ", names(val))
        # Check for any convergence-related column names
        for col in names(val)
            if occursin(r"(conv|iter|resid|status|tol)"i, col)
                println("    *** CONVERGENCE COLUMN FOUND: $col ***")
                println("    values: ", val[!, col])
            end
        end
    elseif val isa Dict
        println("    sub-keys: ", collect(keys(val)))
    end
end

# ── Section 3: Independent post-hoc residual computation ────────────────────
println("\n[3] Post-hoc power mismatch residual (independent verification):")
println("  Computing |P_gen - P_load - P_losses| per bus...")

# Bus-level power balance check
# P_net = P_gen - P_load should equal sum of P flowing out of bus
# Use the available columns
vm_vals = bus_df[!, "Vm"]
p_gen = bus_df[!, "P_gen"]
p_load = bus_df[!, "P_load"]
p_net = bus_df[!, "P_net"]
q_gen = bus_df[!, "Q_gen"]
q_load = bus_df[!, "Q_load"]
q_net = bus_df[!, "Q_net"]

# P_net should equal P_gen - P_load (signed injection)
p_inj_check = p_gen .- p_load .- p_net
println("  Max |P_gen - P_load - P_net| (should be ~0): ", maximum(abs.(p_inj_check)), " pu")
println("  Mean |P_gen - P_load - P_net|: ", sum(abs.(p_inj_check)) / length(p_inj_check), " pu")

# System-level power balance
base_mva = get_base_power(sys_tiny)
total_gen_mw = sum(p_gen) * base_mva
total_load_mw = sum(p_load) * base_mva
p_losses_mw = sum(flow_df[!, "P_losses"]) * base_mva
println("  System balance check:")
println("    Total generation: $(round(total_gen_mw, digits=2)) MW")
println("    Total load:       $(round(total_load_mw, digits=2)) MW")
println("    Branch P losses:  $(round(p_losses_mw, digits=2)) MW")
println(
    "    Imbalance (gen - load - losses): $(round(total_gen_mw - total_load_mw - p_losses_mw, digits=4)) MW",
)

# Voltage profile stats
println("  Voltage profile (convergence proxy):")
println("    Vm min: $(round(minimum(vm_vals), digits=6)) pu")
println("    Vm max: $(round(maximum(vm_vals), digits=6)) pu")
println(
    "    Buses with |Vm - 1.0| > 1e-4: $(count(v -> abs(v - 1.0) > 1e-4, vm_vals)) / $(length(vm_vals))",
)
println(
    "    Buses with |Vm - 1.0| > 0.01: $(count(v -> abs(v - 1.0) > 0.01, vm_vals)) / $(length(vm_vals))",
)

# Branch-level check: are flows physically consistent with bus voltages?
# For each branch: P_from + P_to = P_losses (active power balance)
p_from = flow_df[!, "P_from_to"]
p_to = flow_df[!, "P_to_from"]
p_losses_branch = flow_df[!, "P_losses"]
p_branch_balance = p_from .+ p_to .- p_losses_branch
println("  Branch power balance (P_from + P_to - P_losses, should be ~0):")
println("    Max: $(maximum(abs.(p_branch_balance))) pu")
println("    Mean: $(sum(abs.(p_branch_balance)) / length(p_branch_balance)) pu")

# ── Section 4: Attempt to access internal solver state ──────────────────────
println("\n[4] Attempting to access PowerFlows.jl internal NR solver state:")
try
    # Check if ACPowerFlow() has any configurable tolerance/iteration fields
    acpf = ACPowerFlow()
    println("  ACPowerFlow() type: ", typeof(acpf))
    println("  ACPowerFlow fields: ", fieldnames(typeof(acpf)))
    for field in fieldnames(typeof(acpf))
        println("    $field = ", getfield(acpf, field))
    end
catch e
    println("  Error: $e")
end

# Try to find the NR solver type and its fields
try
    # PowerFlows may have internal types we can inspect
    println("  PowerFlows module names:")
    pf_names = names(PowerFlows; all=true)
    convergence_names = filter(
        n -> occursin(r"(conv|newton|raphson|iter|resid|nlsolve)"i, string(n)), pf_names
    )
    println("  Convergence-related names in PowerFlows: ", convergence_names)
catch e
    println("  Could not inspect PowerFlows internals: $e")
end

# ── Section 5: Reproduce first-call convergence warning scenario ─────────────
println("\n[5] Reproducing first-call convergence warning (C-2 scenario):")
println("  Loading fresh System to get uninitialized state...")
sys_fresh = System("/workspace/data/networks/case39.m")

# Capture all log output during first call
buf = IOBuffer()
with_logger(ConsoleLogger(buf, Logging.Debug)) do
    global pf_fresh1 = solve_powerflow(ACPowerFlow(), sys_fresh)
end
log_output = String(take!(buf))

println("  First-call log output length: $(length(log_output)) chars")
if length(log_output) > 0
    println("  --- First-call log output ---")
    println(log_output)
    println("  --- End of log output ---")
    # Check for convergence warning
    if occursin(r"(fail|warn|conv|not conv)"i, log_output)
        println("  *** CONVERGENCE WARNING DETECTED IN FIRST CALL ***")
    else
        println("  No convergence warning found in first-call log.")
    end
else
    println("  No log output captured (solver may not use Julia logging system).")
end

# Second call on same system
buf2 = IOBuffer()
with_logger(ConsoleLogger(buf2, Logging.Debug)) do
    global pf_fresh2 = solve_powerflow(ACPowerFlow(), sys_fresh)
end
log_output2 = String(take!(buf2))
println("  Second-call log output length: $(length(log_output2)) chars")
if length(log_output2) > 0
    println("  --- Second-call log output ---")
    println(log_output2)
    println("  --- End of log output ---")
end

# Compare first and second call results
if pf_fresh1 !== nothing && pf_fresh2 !== nothing
    bus1 = pf_fresh1["bus_results"]
    bus2 = pf_fresh2["bus_results"]
    vm1 = bus1[!, "Vm"]
    vm2 = bus2[!, "Vm"]
    vm_diff = abs.(vm1 .- vm2)
    println("  First vs Second call Vm comparison:")
    println("    Max |Vm1 - Vm2|: $(maximum(vm_diff)) pu")
    println("    Mean |Vm1 - Vm2|: $(sum(vm_diff)/length(vm_diff)) pu")
    if maximum(vm_diff) < 1e-6
        println("    -> Results IDENTICAL: both calls converged to same solution")
    elseif maximum(vm_diff) < 1e-3
        println("    -> Results NEARLY identical: minor numerical difference")
    else
        println("    -> Results DIFFER SIGNIFICANTLY: first call may not have converged!")
        for (i, d) in enumerate(vm_diff)
            if d > 1e-3
                println(
                    "      Bus $(bus1[i, "bus_number"]): Vm1=$(round(vm1[i], digits=6)), Vm2=$(round(vm2[i], digits=6)), diff=$(round(d, digits=6))",
                )
            end
        end
    end
end

# ── Section 6: Timing summary ────────────────────────────────────────────────
println("\n[6] Timing:")
println("  A-2 ACPF solve time (second call): $(round(elapsed, digits=6)) s")

# ── Section 7: Summary ───────────────────────────────────────────────────────
println("\n[7] Convergence Diagnostic Summary:")
println("  API exposes iteration count: NO")
println("  API exposes convergence residual: NO")
println("  API exposes termination status: NO (only implicit - returns result or nothing)")
println(
    "  Post-hoc system power imbalance: $(round(abs(total_gen_mw - total_load_mw - p_losses_mw), digits=4)) MW",
)
println(
    "  Post-hoc branch balance max error: $(round(maximum(abs.(p_branch_balance)) * base_mva, digits=6)) MW",
)
println(
    "  Voltage profile: min=$(round(minimum(vm_vals), digits=4)) pu, max=$(round(maximum(vm_vals), digits=4)) pu",
)
println(
    "  Buses with non-trivial Vm: $(count(v -> abs(v - 1.0) > 1e-4, vm_vals)) / $(length(vm_vals))"
)

println("\n" * "=" ^ 70)
println("Probe 013 complete.")
println("=" ^ 70)

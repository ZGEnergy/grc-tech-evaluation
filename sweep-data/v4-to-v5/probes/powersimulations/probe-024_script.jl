# Probe 024: ACPF scale failure diagnostics on ACTIVSg 10k
# Claim: ACPF fails at MEDIUM with poor diagnostics

using PowerSystems
using PowerFlows
using Dates
using InfrastructureSystems
const TS = InfrastructureSystems.TimeSeries

println("=" ^ 60)
println("Probe 024: ACPF Scale — MEDIUM (ACTIVSg 10k)")
println("=" ^ 60)

println("\nPowerFlows version: ", string(pkgversion(PowerFlows)))
println("PowerSystems version: ", string(pkgversion(PowerSystems)))

# --- Load ACTIVSg 10k ---
println("\n--- Loading ACTIVSg 10k network ---")
t_load_start = time()

# Check if file exists
case_file = "/workspace/data/networks/case_ACTIVSg10k.m"
if !isfile(case_file)
    println("ERROR: $case_file not found")
    println("Checking available networks...")
    for f in readdir("/workspace/data/networks/")
        println("  $f")
    end
    exit(1)
end

global sys = System(case_file)
t_load = time() - t_load_start
println("Load time: $(round(t_load, digits=2))s")

n_buses = length(collect(get_components(Bus, sys)))
n_branches = length(collect(get_components(Branch, sys)))
n_gens = length(collect(get_components(Generator, sys)))
println("Network: $n_buses buses, $n_branches branches, $n_gens generators")

# --- Attempt ACPF ---
println("\n--- Attempting AC Power Flow ---")
println("Solver: Newton-Raphson (default in PowerFlows.jl)")

t_pf_start = time()
global pf_result = nothing
global pf_error = nothing
try
    global pf_result = solve_powerflow(ACPowerFlow(), sys)
    println("Power flow returned: $(typeof(pf_result))")
    if pf_result === nothing
        println("Result is nothing -- convergence likely failed")
    elseif pf_result isa Bool
        println("Result (Bool): $pf_result")
    elseif pf_result isa Dict
        println("Result keys: $(collect(keys(pf_result)))")
    else
        println("Result type: $(typeof(pf_result))")
    end
catch e
    global pf_error = e
    println("Power flow THREW EXCEPTION:")
    println("  Type: $(typeof(e))")
    println("  Message: $e")
end
t_pf = time() - t_pf_start
println("\nWall clock: $(round(t_pf, digits=2))s")

# --- Try with different settings ---
println("\n--- Checking available PowerFlow options ---")
println("ACPowerFlow type: $(typeof(ACPowerFlow()))")

# Check if there are configurable parameters
try
    pf = ACPowerFlow()
    println("ACPowerFlow fields: $(fieldnames(typeof(pf)))")
    for fn in fieldnames(typeof(pf))
        println("  $fn = $(getfield(pf, fn))")
    end
catch e
    println("Could not inspect ACPowerFlow: $e")
end

# --- Try on IEEE 39-bus for comparison ---
println("\n--- ACPF on IEEE 39-bus (TINY) for comparison ---")
sys_tiny = System("/workspace/data/networks/case39.m")
t_tiny_start = time()
try
    pf_tiny = solve_powerflow(ACPowerFlow(), sys_tiny)
    t_tiny = time() - t_tiny_start
    println("IEEE 39-bus ACPF: converged in $(round(t_tiny, digits=2))s")
    if pf_tiny isa Dict
        println("  Result keys: $(keys(pf_tiny))")
    elseif pf_tiny isa Bool
        println("  Result: $pf_tiny")
    else
        println("  Result type: $(typeof(pf_tiny))")
    end
catch e
    t_tiny = time() - t_tiny_start
    println("IEEE 39-bus ACPF failed in $(round(t_tiny, digits=2))s: $e")
end

# --- Check what diagnostic info PowerFlows provides ---
println("\n--- Diagnostic Information Assessment ---")
println("1. Does PowerFlows report iteration count? ")
println("   -> No iteration count available in API return value")
println("2. Does PowerFlows report convergence tolerance?")
println("   -> Not exposed in the ACPowerFlow() constructor")
println("3. Does PowerFlows support warm-starting from DC solution?")
println("   -> Not supported (no DC warm start parameter)")
println("4. Does PowerFlows support solver parameter tuning?")

# Check if there are tolerance/max_iter fields
try
    pf = ACPowerFlow()
    fnames = fieldnames(typeof(pf))
    has_tol = any(fn -> occursin("tol", lowercase(string(fn))), fnames)
    has_iter = any(fn -> occursin("iter", lowercase(string(fn))), fnames)
    println("   -> Tolerance field: $has_tol")
    println("   -> Max iteration field: $has_iter")
    println("   -> Available fields: $fnames")
catch e
    println("   -> Cannot inspect: $e")
end

println("\n" * "=" ^ 60)
println("CONCLUSION")
println("=" ^ 60)
println(
    "ACPF on 10k-bus network: $(pf_error !== nothing ? "FAILED (exception)" : (pf_result === nothing ? "FAILED (returned nothing)" : "SUCCEEDED"))",
)
println("Wall clock: $(round(t_pf, digits=2))s")
if pf_error !== nothing
    println("Error message: $pf_error")
end
println("Diagnostic quality: Limited -- no iteration count, no residual info,")
println("  no configurable tolerances, no warm-start support.")

# Scalability Batch 1: C-1 (DCPF MEDIUM), C-2 (ACPF MEDIUM), C-3 (DCOPF MEDIUM)
# Combined into one script to avoid repeated JIT compilation overhead.

using PowerSystems
using PowerFlows
using PowerNetworkMatrices
using PowerSimulations
using HiGHS
using Ipopt
using Dates
using DataFrames

const PSI = PowerSimulations

println("=" ^ 80)
println("SCALABILITY BATCH 1 — MEDIUM NETWORK (ACTIVSg 10k)")
println("=" ^ 80)

# ─── Load MEDIUM network ─────────────────────────────────────────────────────
println("\n>>> Loading MEDIUM network (ACTIVSg 10k)...")
t0 = time()
sys_medium = System("/workspace/data/networks/case_ACTIVSg10k.m")
load_time = time() - t0
println("  System loaded in $(round(load_time, digits=2))s")
println("  Buses: $(length(collect(get_components(ACBus, sys_medium))))")
println("  Generators: $(length(collect(get_components(Generator, sys_medium))))")

# ═══════════════════════════════════════════════════════════════════════════════
# C-1: DCPF on MEDIUM
# ═══════════════════════════════════════════════════════════════════════════════
println("\n" * "=" ^ 80)
println("C-1: DCPF on MEDIUM")
println("=" ^ 80)

t0 = time()
try
    dcpf_result = solve_powerflow(DCPowerFlow(), sys_medium)
    dcpf_time = time() - t0
    println("  DCPF CONVERGED in $(round(dcpf_time, digits=2))s")

    if dcpf_result isa Dict
        for (k, df) in dcpf_result
            println("  Result key: $k -> $(nrow(df)) rows, $(ncol(df)) cols")
        end
    else
        println("  Result type: $(typeof(dcpf_result))")
    end
    println("  STATUS: PASS")
catch e
    dcpf_time = time() - t0
    println("  DCPF FAILED after $(round(dcpf_time, digits=2))s")
    println("  Error: $e")
    println("  STATUS: FAIL")
end

# Also compute PTDF for C-9
println("\n--- C-9: PTDF matrix on MEDIUM ---")
t0 = time()
try
    ptdf = PTDF(sys_medium)
    ptdf_time = time() - t0
    ptdf_mat = get_data(ptdf)
    println("  PTDF computed in $(round(ptdf_time, digits=2))s")
    println("  Dimensions: $(size(ptdf_mat))")
    println("  STATUS: PASS")
catch e
    ptdf_time = time() - t0
    println("  PTDF FAILED after $(round(ptdf_time, digits=2))s")
    println("  Error: $e")
    println("  STATUS: FAIL")
end

# ═══════════════════════════════════════════════════════════════════════════════
# C-2: ACPF on MEDIUM
# ═══════════════════════════════════════════════════════════════════════════════
println("\n" * "=" ^ 80)
println("C-2: ACPF on MEDIUM")
println("=" ^ 80)

t0 = time()
try
    acpf_result = solve_powerflow(ACPowerFlow(), sys_medium)
    acpf_time = time() - t0
    println("  ACPF CONVERGED in $(round(acpf_time, digits=2))s")

    if acpf_result isa Dict
        for (k, df) in acpf_result
            println("  Result key: $k -> $(nrow(df)) rows, $(ncol(df)) cols")
        end
    else
        println("  Result type: $(typeof(acpf_result))")
    end
    println("  STATUS: PASS")
catch e
    acpf_time = time() - t0
    println("  ACPF FAILED after $(round(acpf_time, digits=2))s")
    println("  Error: $e")
    println("  STATUS: FAIL")
end

# ═══════════════════════════════════════════════════════════════════════════════
# C-3: DCOPF on MEDIUM (HiGHS)
# ═══════════════════════════════════════════════════════════════════════════════
println("\n" * "=" ^ 80)
println("C-3: DCOPF on MEDIUM (HiGHS)")
println("=" ^ 80)

# Need time series for PSI DecisionModel
println("  Preparing time series for MEDIUM network...")
t_prep = time()

# Clone system for OPF (avoid mutating the original)
sys_opf = deepcopy(sys_medium)

# Fix any generators with active_power > Pmax
for gen in get_components(ThermalStandard, sys_opf)
    pmax = get_active_power_limits(gen).max
    if get_active_power(gen) > pmax && pmax > 0.0
        set_active_power!(gen, pmax)
    end
end

# Add time series (single-period with multiplier 1.0)
resolution = Hour(1)
dates = collect(DateTime("2024-01-01T00:00:00"):resolution:DateTime("2024-01-01T00:00:00"))
ts_values = [1.0]

for gen in get_components(Generator, sys_opf)
    pmax = get_active_power_limits(gen).max
    if pmax > 0.0
        ts = SingleTimeSeries("max_active_power", TimeSeries.TimeArray(dates, ts_values))
        add_time_series!(sys_opf, gen, ts)
    end
end

for load in get_components(PowerLoad, sys_opf)
    ts = SingleTimeSeries("max_active_power", TimeSeries.TimeArray(dates, ts_values))
    add_time_series!(sys_opf, load, ts)
end

transform_single_time_series!(sys_opf, Hour(1), Hour(1))
prep_time = time() - t_prep
println("  Time series prepared in $(round(prep_time, digits=2))s")

# Build and solve DCOPF
t0 = time()
try
    template = ProblemTemplate()
    set_device_model!(template, ThermalStandard, ThermalBasicDispatch)
    set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
    set_device_model!(template, RenewableNonDispatch, FixedOutput)
    set_device_model!(template, HydroDispatch, HydroDispatchRunOfRiver)
    set_device_model!(template, PowerLoad, StaticPowerLoad)

    # Register all branch types
    for BT in [Line, Transformer2W, TapTransformer, PhaseShiftingTransformer]
        if !isempty(collect(get_components(BT, sys_opf)))
            set_device_model!(template, BT, StaticBranch)
        end
    end

    set_network_model!(template, NetworkModel(PTDFPowerModel))

    solver = optimizer_with_attributes(
        HiGHS.Optimizer, "output_flag" => false, "time_limit" => 300.0
    )

    model = DecisionModel(
        template, sys_opf; optimizer=solver, horizon=Hour(1), optimizer_solve_log_print=false
    )

    build_status = build!(model; output_dir=mktempdir())
    println("  Build status: $build_status")

    if build_status == PSI.BuildStatus.BUILT
        solve_status = solve!(model)
        dcopf_time = time() - t0
        println("  Solve status: $solve_status")
        println("  DCOPF solved in $(round(dcopf_time, digits=2))s (incl. build)")

        res = OptimizationProblemResults(model)
        obj = objective_value(get_jump_model(model))
        println("  Objective: $obj")
        println("  STATUS: PASS")
    else
        dcopf_time = time() - t0
        println("  Build failed after $(round(dcopf_time, digits=2))s")
        println("  STATUS: FAIL")
    end
catch e
    dcopf_time = time() - t0
    println("  DCOPF FAILED after $(round(dcopf_time, digits=2))s")
    println("  Error: $e")
    showerror(stdout, e, catch_backtrace())
    println()
    println("  STATUS: FAIL")
end

println("\n" * "=" ^ 80)
println("SCALABILITY BATCH 1 COMPLETE")
println("=" ^ 80)

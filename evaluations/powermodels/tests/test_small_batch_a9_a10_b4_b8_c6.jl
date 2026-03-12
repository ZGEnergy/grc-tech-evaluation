#=
SMALL network batch runner for tests: A-9, A-10, B-4, B-8, C-6
Network: ACTIVSg 2000-bus
=#

using PowerModels, JuMP, HiGHS, Ipopt, JSON
using Random, LinearAlgebra, SparseArrays

const NETWORK_FILE = joinpath(@__DIR__, "..", "..", "..", "data", "networks", "case_ACTIVSg2000.m")

println("=== Warming up (case39 2-period DCOPF) ===")
try
    _d = PowerModels.parse_file(
        joinpath(@__DIR__, "..", "..", "..", "data", "networks", "case39.m")
    )
    _mn = PowerModels.replicate(_d, 2)
    PowerModels.solve_mn_opf(_mn, DCPPowerModel, HiGHS.Optimizer)
    println("Warm-up done.")
catch e
    println("Warm-up failed (non-fatal): $e")
end

# ============================================================
# Run individual test scripts via include()
# ============================================================

function run_test(test_name, script_path)
    println("\n" * "="^60)
    println("=== Running $test_name ===")
    println("="^60)
    t0 = time()
    result = nothing
    try
        include(script_path)
        result = run(NETWORK_FILE)
        println("\n--- $test_name RESULT ---")
        println("status: $(result["status"])")
        println("wall_clock_seconds: $(result["wall_clock_seconds"])")
        if !isempty(result["errors"])
            println("errors: $(result["errors"])")
        end
    catch e
        println("ERROR in $test_name: $e")
        result = Dict(
            "status" => "error",
            "wall_clock_seconds" => time() - t0,
            "errors" => [string(e)],
            "details" => Dict(),
            "workarounds" => String[],
        )
    end
    return result
end

all_results = Dict{String,Any}()

# A-9: SCOPF SMALL
a9_result = run_test(
    "A-9 SCOPF SMALL", joinpath(@__DIR__, "expressiveness", "test_a9_scopf_small.jl")
)
all_results["A-9"] = a9_result

# A-10: Lossy DCOPF + LMP Decomposition SMALL
a10_result = run_test(
    "A-10 Lossy DCOPF LMP Decomposition SMALL",
    joinpath(@__DIR__, "expressiveness", "test_a10_lossy_dcopf_lmp_decomposition_small.jl"),
)
all_results["A-10"] = a10_result

# B-4: Stochastic Scenario Wrapping SMALL
b4_result = run_test(
    "B-4 Stochastic Scenario Wrapping SMALL",
    joinpath(@__DIR__, "extensibility", "test_b4_stochastic_scenario_wrapping_small.jl"),
)
all_results["B-4"] = b4_result

# B-8: Reference Bus Configuration SMALL
b8_result = run_test(
    "B-8 Reference Bus Configuration SMALL",
    joinpath(@__DIR__, "extensibility", "test_b8_reference_bus_configuration_small.jl"),
)
all_results["B-8"] = b8_result

# C-6: Stochastic DC OPF Scale SMALL
c6_result = run_test(
    "C-6 Stochastic DCOPF Scale SMALL",
    joinpath(@__DIR__, "scalability", "test_c6_stochastic_dcopf_scale_small.jl"),
)
all_results["C-6"] = c6_result

# ============================================================
# Summary
# ============================================================
println("\n" * "="^60)
println("=== BATCH SUMMARY ===")
println("="^60)
for (test_id, result) in sort(collect(all_results); by=x->x[1])
    status = get(result, "status", "unknown")
    wc = get(result, "wall_clock_seconds", NaN)
    errors = get(result, "errors", String[])
    println(
        "$test_id: $status ($(round(wc, digits=1))s)$(isempty(errors) ? "" : " ERRORS: $(length(errors))")",
    )
end

println("\nFull results JSON:")
println(JSON.json(all_results, 2))

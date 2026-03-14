#!/usr/bin/env julia
# test_gate.jl — Gate tests G-1, G-2, G-3 for PowerModels

using PowerModels
using Dates

PowerModels.silence()

function audit_network(data::Dict)
    issues = String[]

    for (id, bus) in data["bus"]
        if !isfinite(get(bus, "vmin", NaN)) || !isfinite(get(bus, "vmax", NaN))
            push!(issues, "Bus $id has non-finite voltage bounds")
        end
    end

    has_slack = any(bus["bus_type"] == 3 for (_, bus) in data["bus"])
    if !has_slack
        push!(issues, "No slack/reference bus (bus_type=3) found")
    end

    zero_rate_a = 0
    for (id, br) in data["branch"]
        ra = get(br, "rate_a", NaN)
        if !isfinite(ra)
            push!(issues, "Branch $id has non-finite rate_a")
        end
        if isfinite(ra) && ra == 0.0
            zero_rate_a += 1
        end
    end
    if zero_rate_a > 0
        push!(issues, "$(zero_rate_a) branches have rate_a = 0 (unconstrained flow limit)")
    end

    zero_x = 0
    for (id, br) in data["branch"]
        xval = get(br, "br_x", NaN)
        if isfinite(xval) && xval == 0.0
            zero_x += 1
        end
    end
    if zero_x > 0
        push!(issues, "$(zero_x) branches have br_x = 0 (may cause singularity in AC)")
    end

    gen_no_cost = 0
    for (id, gen) in data["gen"]
        if !haskey(data, "gencost") && !haskey(gen, "cost")
            gen_no_cost += 1
        end
    end
    if gen_no_cost > 0
        push!(issues, "$(gen_no_cost) generators missing cost data")
    end

    for (id, gen) in data["gen"]
        for field in ["pmin", "pmax", "qmin", "qmax"]
            val = get(gen, field, NaN)
            if !isfinite(val)
                push!(issues, "Gen $id has non-finite $field")
            end
        end
    end

    return issues
end

function run_gate_test(
    test_id, network_label, filepath, expected_buses, expected_branches, expected_gens
)
    println("\n" * "="^70)
    println("TEST $test_id — $network_label")
    println("File: $filepath")
    println("="^70)

    if !isfile(filepath)
        println("FAIL: File not found: $filepath")
        return (status=:fail, buses=0, branches=0, gens=0, load_time=0.0, issues=["File not found"])
    end

    t0 = time()
    local data
    try
        data = PowerModels.parse_file(filepath)
    catch e
        elapsed = time() - t0
        println("FAIL: parse_file threw exception: $e")
        return (
            status=:fail,
            buses=0,
            branches=0,
            gens=0,
            load_time=elapsed,
            issues=["parse_file error: $e"],
        )
    end
    elapsed = time() - t0

    actual_buses = length(data["bus"])
    actual_branches = length(data["branch"])
    actual_gens = length(data["gen"])

    println("Load time:  $(round(elapsed, digits=2))s")
    println(
        "Buses:      $actual_buses  (expected: $(isnothing(expected_buses) ? "verify" : expected_buses))",
    )
    println(
        "Branches:   $actual_branches  (expected: $(isnothing(expected_branches) ? "verify" : expected_branches))",
    )
    println(
        "Generators: $actual_gens  (expected: $(isnothing(expected_gens) ? "verify" : expected_gens))",
    )

    count_pass = true
    if !isnothing(expected_buses) && actual_buses != expected_buses
        println("MISMATCH: buses expected $expected_buses, got $actual_buses")
        count_pass = false
    end
    if !isnothing(expected_branches) && actual_branches != expected_branches
        println("MISMATCH: branches expected $expected_branches, got $actual_branches")
        count_pass = false
    end
    if !isnothing(expected_gens) && actual_gens != expected_gens
        println("MISMATCH: generators expected $expected_gens, got $actual_gens")
        count_pass = false
    end

    issues = audit_network(data)
    if isempty(issues)
        println("Data quality: OK (no issues found)")
    else
        println("Data quality issues:")
        for iss in issues
            println("  - $iss")
        end
    end

    status = count_pass ? :pass : :fail
    println("\nResult: $(uppercase(string(status)))")
    return (
        status=status,
        buses=actual_buses,
        branches=actual_branches,
        gens=actual_gens,
        load_time=elapsed,
        issues=issues,
    )
end

WORKSPACE = "/workspace"

r1 = run_gate_test(
    "G-1", "TINY (IEEE 39-bus)", joinpath(WORKSPACE, "data/networks/case39.m"), 39, 46, 10
)

if r1.status == :fail
    println("\nG-1 FAILED — disqualifying. Halting. scale_cap: NONE")
    exit(1)
end

r2 = run_gate_test(
    "G-2",
    "SMALL (ACTIVSg 2000)",
    joinpath(WORKSPACE, "data/networks/case_ACTIVSg2000.m"),
    2000,
    3206,
    544,
)

if r2.status == :fail
    println("\nG-2 FAILED. scale_cap: TINY")
    exit(2)
end

r3 = run_gate_test(
    "G-3",
    "MEDIUM (ACTIVSg 10k)",
    joinpath(WORKSPACE, "data/networks/case_ACTIVSg10k.m"),
    10000,
    12706,
    2485,
)

if r3.status == :fail
    println("\nG-3 FAILED. scale_cap: SMALL")
    exit(3)
end

println("\nAll gate tests PASSED. scale_cap: MEDIUM")
exit(0)

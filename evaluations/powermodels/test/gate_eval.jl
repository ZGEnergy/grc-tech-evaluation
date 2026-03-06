#!/usr/bin/env julia
# Gate evaluation script for PowerModels
# Tests G-1 (TINY/case39), G-2 (SMALL/case_ACTIVSg2000), G-3 (MEDIUM/case_ACTIVSg10k)

using PowerModels
using Printf

const DATA_DIR = normpath(joinpath(@__DIR__, "..", "..", "..", "data", "networks"))

const NETWORKS = [
    ("TINY", "case39.m", 39, 46, 10),
    ("SMALL", "case_ACTIVSg2000.m", nothing, nothing, nothing),
    ("MEDIUM", "case_ACTIVSg10k.m", nothing, nothing, nothing),
]

function audit_data_quality(data::Dict, tier::String)
    issues = String[]
    warnings = String[]

    # Check bus voltages for NaN/Inf
    nan_vm = 0;
    inf_vm = 0;
    nan_va = 0;
    inf_va = 0
    for (_, bus) in data["bus"]
        vm = get(bus, "vm", nothing)
        va = get(bus, "va", nothing)
        if vm !== nothing
            isnan(vm) && (nan_vm += 1)
            isinf(vm) && (inf_vm += 1)
        end
        if va !== nothing
            isnan(va) && (nan_va += 1)
            isinf(va) && (inf_va += 1)
        end
    end
    nan_vm > 0 && push!(issues, "$(nan_vm) buses with NaN voltage magnitude")
    inf_vm > 0 && push!(issues, "$(inf_vm) buses with Inf voltage magnitude")
    nan_va > 0 && push!(issues, "$(nan_va) buses with NaN voltage angle")
    inf_va > 0 && push!(issues, "$(inf_va) buses with Inf voltage angle")

    # Check branch ratings for NaN/Inf and missing limits
    nan_rate = 0;
    inf_rate = 0;
    missing_rate = 0
    for (_, branch) in data["branch"]
        rate_a = get(branch, "rate_a", nothing)
        if rate_a === nothing
            missing_rate += 1
        elseif isnan(rate_a)
            nan_rate += 1
        elseif isinf(rate_a)
            inf_rate += 1
        elseif rate_a == 0.0
            missing_rate += 1
        end
    end
    nan_rate > 0 && push!(issues, "$(nan_rate) branches with NaN rate_a")
    inf_rate > 0 && push!(issues, "$(inf_rate) branches with Inf rate_a")
    missing_rate > 0 &&
        push!(warnings, "$(missing_rate) branches with missing/zero rate_a (flow limits)")

    # Check generator limits for NaN/Inf
    nan_pmax = 0;
    inf_pmax = 0;
    nan_pmin = 0
    for (_, gen) in data["gen"]
        pmax = get(gen, "pmax", nothing)
        pmin = get(gen, "pmin", nothing)
        if pmax !== nothing && isnan(pmax)
            ;
            nan_pmax += 1;
        end
        if pmax !== nothing && isinf(pmax)
            ;
            inf_pmax += 1;
        end
        if pmin !== nothing && isnan(pmin)
            ;
            nan_pmin += 1;
        end
    end
    nan_pmax > 0 && push!(issues, "$(nan_pmax) generators with NaN pmax")
    inf_pmax > 0 && push!(issues, "$(inf_pmax) generators with Inf pmax")
    nan_pmin > 0 && push!(issues, "$(nan_pmin) generators with NaN pmin")

    # Check generator cost data
    missing_cost = 0;
    has_cost = 0
    for (_, gen) in data["gen"]
        ncost = get(gen, "ncost", nothing)
        cost = get(gen, "cost", nothing)
        if ncost === nothing || cost === nothing || (isa(cost, Vector) && isempty(cost))
            missing_cost += 1
        else
            has_cost += 1
        end
    end
    missing_cost > 0 &&
        push!(warnings, "$(missing_cost)/$(length(data["gen"])) generators missing cost data")
    has_cost > 0 && push!(warnings, "$(has_cost)/$(length(data["gen"])) generators have cost data")

    # Check for slack/reference bus
    ref_buses = [k for (k, bus) in data["bus"] if get(bus, "bus_type", 0) == 3]
    if isempty(ref_buses)
        push!(issues, "No reference/slack bus found (bus_type == 3)")
    end

    return issues, warnings, length(ref_buses)
end

function run_gate_test(tier::String, filename::String, exp_buses, exp_branches, exp_gens)
    filepath = joinpath(DATA_DIR, filename)
    println("\n" * "="^70)
    println("Gate Test: $(tier) — $(filename)")
    println("="^70)

    if !isfile(filepath)
        println("FAIL: File not found: $(filepath)")
        return (
            status=:fail,
            reason="File not found",
            buses=0,
            branches=0,
            gens=0,
            load_time=0.0,
            issues=String[],
            warnings=String[],
            ref_buses=0,
        )
    end

    # Parse with timing
    t_start = time()
    local data
    try
        data = PowerModels.parse_file(filepath)
    catch e
        println("FAIL: Parse error: $(e)")
        return (
            status=:fail,
            reason="Parse error: $(e)",
            buses=0,
            branches=0,
            gens=0,
            load_time=0.0,
            issues=String[],
            warnings=String[],
            ref_buses=0,
        )
    end
    load_time = time() - t_start

    actual_buses = length(data["bus"])
    actual_branches = length(data["branch"])
    actual_gens = length(data["gen"])

    @printf("  Buses:      %d", actual_buses)
    if exp_buses !== nothing
        println(exp_buses == actual_buses ? " ✓" : " ✗ (expected $(exp_buses))")
    else
        println(" (recorded)")
    end

    @printf("  Branches:   %d", actual_branches)
    if exp_branches !== nothing
        println(exp_branches == actual_branches ? " ✓" : " ✗ (expected $(exp_branches))")
    else
        println(" (recorded)")
    end

    @printf("  Generators: %d", actual_gens)
    if exp_gens !== nothing
        println(exp_gens == actual_gens ? " ✓" : " ✗ (expected $(exp_gens))")
    else
        println(" (recorded)")
    end

    @printf("  Load time:  %.3f s\n", load_time)

    # Count check for known references
    count_ok = true
    if exp_buses !== nothing && actual_buses != exp_buses
        ;
        count_ok = false;
    end
    if exp_branches !== nothing && actual_branches != exp_branches
        ;
        count_ok = false;
    end
    if exp_gens !== nothing && actual_gens != exp_gens
        ;
        count_ok = false;
    end

    # Sanity check for unknown references
    if exp_buses === nothing
        if tier == "SMALL" && !(1500 <= actual_buses <= 2500)
            println("  WARNING: SMALL expected ~2000 buses, got $(actual_buses)")
        elseif tier == "MEDIUM" && !(8000 <= actual_buses <= 12000)
            println("  WARNING: MEDIUM expected ~10000 buses, got $(actual_buses)")
        end
    end

    # Data quality audit
    issues, warnings, ref_bus_count = audit_data_quality(data, tier)

    println("\n  Data Quality Audit:")
    if isempty(issues)
        println("    No critical issues found")
    else
        for issue in issues
            println("    ISSUE: $(issue)")
        end
    end
    for w in warnings
        println("    NOTE: $(w)")
    end
    println("    Reference buses: $(ref_bus_count)")

    status = count_ok && isempty(issues) ? :pass : (isempty(issues) ? :pass : :fail)
    # Issues are critical failures; warnings are informational
    if !count_ok && exp_buses !== nothing
        status = :fail
    end

    println("\n  Result: $(uppercase(string(status)))")

    return (
        status=status,
        reason="",
        buses=actual_buses,
        branches=actual_branches,
        gens=actual_gens,
        load_time=load_time,
        issues=issues,
        warnings=warnings,
        ref_buses=ref_bus_count,
    )
end

# Run all tests
results = Dict{String,NamedTuple}()
for (tier, filename, eb, ebr, eg) in NETWORKS
    results[tier] = run_gate_test(tier, filename, eb, ebr, eg)
end

println("\n" * "="^70)
println("SUMMARY")
println("="^70)
for (tier, _, _, _, _) in NETWORKS
    r = results[tier]
    @printf(
        "  %-8s %s  (buses=%d, branches=%d, gens=%d, time=%.3fs)\n",
        tier,
        uppercase(string(r.status)),
        r.buses,
        r.branches,
        r.gens,
        r.load_time
    )
end

# Determine scale_cap
if results["TINY"].status != :pass
    println("\nscale_cap: NONE (TINY gate failed — disqualifying)")
elseif results["SMALL"].status != :pass
    println("\nscale_cap: TINY")
elseif results["MEDIUM"].status != :pass
    println("\nscale_cap: SMALL")
else
    println("\nscale_cap: MEDIUM")
end

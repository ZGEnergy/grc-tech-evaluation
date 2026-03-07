#!/usr/bin/env julia
# Gate tests for PowerModels.jl — G-1, G-2, G-3
# Tests network ingestion for TINY (case39), SMALL (case_ACTIVSg2000), MEDIUM (case_ACTIVSg10k)

using PowerModels

# Path to shared network data
const DATA_DIR = joinpath(@__DIR__, "..", "..", "..", "data", "networks")

# Reference counts: (buses, branches, generators)
const NETWORKS = [
    ("G-1", "TINY", "case39.m", 39, 46, 10),
    ("G-2", "SMALL", "case_ACTIVSg2000.m", 2000, 3206, 544),
    ("G-3", "MEDIUM", "case_ACTIVSg10k.m", 10000, 12706, 2485),
]

function audit_data_quality(data::Dict)
    issues = String[]

    # Check bus voltages for NaN/Inf
    for (bid, bus) in data["bus"]
        vm = get(bus, "vm", nothing)
        if vm !== nothing && (isnan(vm) || isinf(vm))
            push!(issues, "Bus $bid has invalid Vm: $vm")
        end
        va = get(bus, "va", nothing)
        if va !== nothing && (isnan(va) || isinf(va))
            push!(issues, "Bus $bid has invalid Va: $va")
        end
        vmax = get(bus, "vmax", nothing)
        vmin = get(bus, "vmin", nothing)
        if vmax !== nothing && (isnan(vmax) || isinf(vmax))
            push!(issues, "Bus $bid has invalid Vmax: $vmax")
        end
        if vmin !== nothing && (isnan(vmin) || isinf(vmin))
            push!(issues, "Bus $bid has invalid Vmin: $vmin")
        end
    end

    # Check branch flow limits and ratings
    branches_missing_rate = 0
    for (brid, branch) in data["branch"]
        rate_a = get(branch, "rate_a", 0.0)
        if rate_a == 0.0
            branches_missing_rate += 1
        end
        for field in ["br_r", "br_x"]
            val = get(branch, field, nothing)
            if val !== nothing && (isnan(val) || isinf(val))
                push!(issues, "Branch $brid has invalid $field: $val")
            end
        end
    end
    if branches_missing_rate > 0
        push!(
            issues,
            "$branches_missing_rate / $(length(data["branch"])) branches have zero or missing rate_a (flow limit)",
        )
    end

    # Check generator limits and cost data
    gens_missing_cost = 0
    for (gid, gen) in data["gen"]
        pmax = get(gen, "pmax", nothing)
        pmin = get(gen, "pmin", nothing)
        if pmax !== nothing && (isnan(pmax) || isinf(pmax))
            push!(issues, "Gen $gid has invalid Pmax: $pmax")
        end
        if pmin !== nothing && (isnan(pmin) || isinf(pmin))
            push!(issues, "Gen $gid has invalid Pmin: $pmin")
        end
        qmax = get(gen, "qmax", nothing)
        qmin = get(gen, "qmin", nothing)
        if qmax !== nothing && (isnan(qmax) || isinf(qmax))
            push!(issues, "Gen $gid has invalid Qmax: $qmax")
        end
        if qmin !== nothing && (isnan(qmin) || isinf(qmin))
            push!(issues, "Gen $gid has invalid Qmin: $qmin")
        end
    end

    # Check for generator cost data
    if haskey(data, "gencost") || any(haskey(gen, "cost") for (_, gen) in data["gen"])
        # cost data present
    else
        # PowerModels may store cost in gen directly after parsing
        has_cost = any(haskey(gen, "cost") || haskey(gen, "ncost") for (_, gen) in data["gen"])
        if !has_cost
            push!(issues, "No generator cost data found")
        end
    end

    # Check for slack/reference bus (type 3)
    slack_buses = [bid for (bid, bus) in data["bus"] if get(bus, "bus_type", 0) == 3]
    if isempty(slack_buses)
        push!(issues, "No slack/reference bus (type 3) identified")
    end

    return issues, slack_buses, branches_missing_rate
end

function run_gate_tests()
    results = []

    for (test_id, tier, filename, exp_buses, exp_branches, exp_gens) in NETWORKS
        filepath = joinpath(DATA_DIR, filename)
        println("=" ^ 70)
        println("$test_id: Ingesting $tier network ($filename)")
        println("  Expected: $exp_buses buses, $exp_branches branches, $exp_gens generators")

        if !isfile(filepath)
            println("  ERROR: File not found: $filepath")
            push!(
                results,
                (
                    test_id,
                    tier,
                    filename,
                    "FAIL",
                    "File not found",
                    0,
                    0,
                    0,
                    exp_buses,
                    exp_branches,
                    exp_gens,
                    0.0,
                    String[],
                    Int[],
                    0,
                ),
            )
            if tier == "TINY"
                println("\n  TINY gate failed — halting.")
                break
            end
            continue
        end

        # Parse and time it
        t_start = time()
        local data
        try
            data = PowerModels.parse_file(filepath)
        catch e
            elapsed = time() - t_start
            errmsg = sprint(showerror, e)
            println("  ERROR parsing: $errmsg")
            push!(
                results,
                (
                    test_id,
                    tier,
                    filename,
                    "FAIL",
                    "Parse error: $errmsg",
                    0,
                    0,
                    0,
                    exp_buses,
                    exp_branches,
                    exp_gens,
                    elapsed,
                    String[],
                    Int[],
                    0,
                ),
            )
            if tier == "TINY"
                println("\n  TINY gate failed — halting.")
                break
            end
            continue
        end
        elapsed = time() - t_start

        actual_buses = length(data["bus"])
        actual_branches = length(data["branch"])
        actual_gens = length(data["gen"])

        println(
            "  Actual:   $actual_buses buses, $actual_branches branches, $actual_gens generators"
        )
        println("  Load time: $(round(elapsed, digits=3))s")

        counts_match = (
            actual_buses == exp_buses && actual_branches == exp_branches && actual_gens == exp_gens
        )

        if !counts_match
            println("  WARNING: Count mismatch!")
        end

        # Data quality audit
        issues, slack_buses, missing_rates = audit_data_quality(data)
        if !isempty(issues)
            println("  Data quality issues:")
            for issue in issues
                println("    - $issue")
            end
        else
            println("  Data quality: All checks passed")
        end
        println("  Slack buses: $slack_buses")

        # Determine pass/fail: counts must match, no NaN/Inf critical issues
        critical_issues = filter(i -> occursin("invalid", i) || occursin("No slack", i), issues)
        status = counts_match && isempty(critical_issues) ? "PASS" : "FAIL"
        println("  Result: $status")

        push!(
            results,
            (
                test_id,
                tier,
                filename,
                status,
                counts_match ? "Counts match" : "Count mismatch",
                actual_buses,
                actual_branches,
                actual_gens,
                exp_buses,
                exp_branches,
                exp_gens,
                elapsed,
                issues,
                slack_buses,
                missing_rates,
            ),
        )

        if status == "FAIL" && tier == "TINY"
            println("\n  TINY gate failed — halting.")
            break
        end
    end

    # Summary
    println("\n" * "=" ^ 70)
    println("GATE TEST SUMMARY")
    println("=" ^ 70)
    for r in results
        println("  $(r[1]) ($(r[2])): $(r[4])")
    end

    # Determine scale_cap
    statuses = Dict(r[2] => r[4] for r in results)
    if get(statuses, "TINY", "FAIL") == "FAIL"
        println("\nscale_cap: NONE")
    elseif get(statuses, "SMALL", "FAIL") == "FAIL"
        println("\nscale_cap: TINY")
    elseif get(statuses, "MEDIUM", "FAIL") == "FAIL"
        println("\nscale_cap: SMALL")
    else
        println("\nscale_cap: MEDIUM")
    end

    return results
end

results = run_gate_tests()

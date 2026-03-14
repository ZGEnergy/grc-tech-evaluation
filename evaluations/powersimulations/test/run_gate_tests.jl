#!/usr/bin/env julia
# run_gate_tests.jl — Gate tests G-1, G-2, G-3 for PowerSimulations (via PowerSystems.jl)
#
# Loads MATPOWER .m files, counts buses/branches/generators, performs data quality audit.

using PowerSystems
using Dates
using Logging

# Suppress verbose PowerSystems logging (it logs a LOT of info on MATPOWER import)
global_logger(ConsoleLogger(stderr, Logging.Error))

const DATA_DIR = "/workspace/data/networks"

struct GateResult
    test_id::String
    label::String
    network_file::String
    expected_buses::Int
    expected_branches::Int
    expected_gens::Int
    actual_buses::Int
    actual_branches::Int
    actual_gens::Int
    load_time::Float64
    passed::Bool
    audit_notes::Vector{String}
    warnings::Vector{String}
end

function count_components(sys::System)
    buses = length(collect(get_components(ACBus, sys)))

    # Branches: collect all subtypes of Branch
    branches = length(collect(get_components(Branch, sys)))

    # Generators: collect all subtypes of Generator
    gens = length(collect(get_components(Generator, sys)))

    return buses, branches, gens
end

function audit_system(sys::System)
    notes = String[]

    # Check for NaN/Inf in bus voltages
    for bus in get_components(ACBus, sys)
        vm = get_magnitude(bus)
        if !isfinite(vm)
            push!(notes, "Bus $(get_name(bus)) has non-finite voltage magnitude")
        end
    end

    # Check for slack/reference bus
    slack_buses = [b for b in get_components(ACBus, sys) if get_bustype(b) == ACBusTypes.REF]
    if isempty(slack_buses)
        push!(notes, "No slack/reference bus found")
    else
        push!(notes, "Slack bus(es): $(join([get_name(b) for b in slack_buses], ", "))")
    end

    # Check branch flow limits
    zero_limit = 0
    missing_limit = 0
    for br in get_components(Branch, sys)
        rate = get_rating(br)
        if !isfinite(rate)
            missing_limit += 1
        elseif rate == 0.0
            zero_limit += 1
        end
    end
    if zero_limit > 0
        push!(notes, "$zero_limit branches have rate = 0 (unconstrained)")
    end
    if missing_limit > 0
        push!(notes, "$missing_limit branches have non-finite rate")
    end

    # Check generator limits
    nan_gen_limits = 0
    no_limits_gens = 0
    for gen in get_components(Generator, sys)
        try
            al = get_active_power_limits(gen)
            if !isfinite(al.min) || !isfinite(al.max)
                nan_gen_limits += 1
            end
        catch
            no_limits_gens += 1
        end
    end
    if nan_gen_limits > 0
        push!(notes, "$nan_gen_limits generators have non-finite active power limits")
    end
    if no_limits_gens > 0
        push!(
            notes,
            "$no_limits_gens generators do not support get_active_power_limits (e.g. RenewableDispatch)",
        )
    end

    # Check for generators with cost data (operation_cost)
    gens_with_cost = 0
    gens_without_cost = 0
    for gen in get_components(Generator, sys)
        oc = try
            get_operation_cost(gen)
        catch
            ;
            nothing
        end
        if oc === nothing
            gens_without_cost += 1
        else
            gens_with_cost += 1
        end
    end
    if gens_without_cost > 0
        push!(notes, "$gens_without_cost generators missing operation cost data")
    end
    if gens_with_cost > 0
        push!(notes, "$gens_with_cost generators have operation cost data")
    end

    # Check for zero reactance branches
    zero_x = 0
    for br in get_components(Branch, sys)
        x = get_x(br)
        if isfinite(x) && x == 0.0
            zero_x += 1
        end
    end
    if zero_x > 0
        push!(notes, "$zero_x branches have zero reactance (may cause singularity)")
    end

    return notes
end

function run_gate_test(test_id, label, filepath, exp_buses, exp_branches, exp_gens)
    println("\n" * "="^60)
    println("$test_id: $label")
    println("="^60)

    warnings = String[]
    local sys, actual_buses, actual_branches, actual_gens, load_time

    try
        t0 = time()
        # Redirect stderr to capture PowerSystems warnings
        sys = System(filepath)
        load_time = time() - t0
        println("  Load time: $(round(load_time, digits=2))s")
    catch e
        println("  FAILED to load: $e")
        return GateResult(
            test_id,
            label,
            filepath,
            exp_buses,
            exp_branches,
            exp_gens,
            0,
            0,
            0,
            0.0,
            false,
            ["Failed to load: $(sprint(showerror, e))"],
            String[],
        )
    end

    actual_buses, actual_branches, actual_gens = count_components(sys)

    println("  Buses:      expected=$exp_buses  actual=$actual_buses")
    println("  Branches:   expected=$exp_branches  actual=$actual_branches")
    println("  Generators: expected=$exp_gens  actual=$actual_gens")

    passed = (
        actual_buses == exp_buses && actual_branches == exp_branches && actual_gens == exp_gens
    )

    println("  Status: $(passed ? "PASS" : "FAIL")")

    # Run audit
    audit_notes = audit_system(sys)
    for note in audit_notes
        println("  [audit] $note")
    end

    return GateResult(
        test_id,
        label,
        filepath,
        exp_buses,
        exp_branches,
        exp_gens,
        actual_buses,
        actual_branches,
        actual_gens,
        load_time,
        passed,
        audit_notes,
        warnings,
    )
end

# Run all three gate tests
results = GateResult[]

push!(
    results, run_gate_test("G-1", "TINY (IEEE 39-bus)", joinpath(DATA_DIR, "case39.m"), 39, 46, 10)
)

push!(
    results,
    run_gate_test(
        "G-2", "SMALL (ACTIVSg2000)", joinpath(DATA_DIR, "case_ACTIVSg2000.m"), 2000, 3206, 544
    ),
)

push!(
    results,
    run_gate_test(
        "G-3", "MEDIUM (ACTIVSg10k)", joinpath(DATA_DIR, "case_ACTIVSg10k.m"), 10000, 12706, 2485
    ),
)

# Summary
println("\n" * "="^60)
println("SUMMARY")
println("="^60)
for r in results
    status = r.passed ? "PASS" : "FAIL"
    println(
        "  $(r.test_id) $(r.label): $status " *
        "($(r.actual_buses)/$(r.actual_branches)/$(r.actual_gens) " *
        "vs $(r.expected_buses)/$(r.expected_branches)/$(r.expected_gens)) " *
        "[$(round(r.load_time, digits=2))s]",
    )
end

# Determine scale_cap
if !results[1].passed
    println("\n  scale_cap: NONE (TINY failed — disqualifying)")
elseif !results[2].passed
    println("\n  scale_cap: TINY (SMALL failed)")
elseif !results[3].passed
    println("\n  scale_cap: SMALL (MEDIUM failed)")
else
    println("\n  scale_cap: MEDIUM (all passed)")
end

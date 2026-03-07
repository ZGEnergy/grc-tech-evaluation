"""
Gate tests for PowerSimulations.jl
"""

using PowerSystems
using Dates
using Printf

const DATA_DIR = joinpath(@__DIR__, "..", "..", "..", "data", "networks")

const TESTS = [
    (id="G-1", label="TINY", file="case39.m", buses=39, branches=46, gens=10),
    (id="G-2", label="SMALL", file="case_ACTIVSg2000.m", buses=2000, branches=3206, gens=544),
    (id="G-3", label="MEDIUM", file="case_ACTIVSg10k.m", buses=10000, branches=12706, gens=2485),
]

function count_components(sys::System)
    buses = length(collect(get_components(ACBus, sys)))
    branches = length(collect(get_components(Branch, sys)))
    gens = length(collect(get_components(Generator, sys)))
    return (buses=buses, branches=branches, gens=gens)
end

function audit_system(sys::System)
    notes = String[]
    errors = String[]

    # Slack bus check
    slack_buses = collect(get_components(x -> get_bustype(x) == ACBusTypes.REF, ACBus, sys))
    if isempty(slack_buses)
        push!(errors, "No slack/reference bus found")
    else
        push!(notes, "Slack bus(es): $(join([get_name(b) for b in slack_buses], ", "))")
    end

    # NaN / Inf checks on bus voltages
    nan_count = 0
    inf_count = 0
    for bus in get_components(ACBus, sys)
        vm = get_magnitude(bus)
        va = get_angle(bus)
        if isnan(vm) || isnan(va)
            nan_count += 1
        end
        if isinf(vm) || isinf(va)
            inf_count += 1
        end
    end
    if nan_count > 0
        push!(errors, "Found $nan_count buses with NaN voltage magnitude or angle")
    else
        push!(notes, "No NaN values in bus voltages")
    end
    if inf_count > 0
        push!(errors, "Found $inf_count buses with Inf voltage magnitude or angle")
    else
        push!(notes, "No Inf values in bus voltages")
    end

    # Generator cost data check
    gens_with_cost = 0
    gens_without_cost = 0
    for gen in get_components(Generator, sys)
        op_cost = get_operation_cost(gen)
        if op_cost !== nothing
            gens_with_cost += 1
        else
            gens_without_cost += 1
        end
    end
    push!(
        notes, "Generators with cost data: $gens_with_cost / $(gens_with_cost + gens_without_cost)"
    )
    if gens_without_cost > 0
        push!(notes, "WARNING: $gens_without_cost generators missing cost data")
    end

    # Branch flow limit check
    branches_with_limits = 0
    branches_without_limits = 0
    for br in get_components(Branch, sys)
        rating = get_rating(br)
        if rating > 0.0
            branches_with_limits += 1
        else
            branches_without_limits += 1
        end
    end
    push!(
        notes,
        "Branches with flow limits: $branches_with_limits / $(branches_with_limits + branches_without_limits)",
    )
    if branches_without_limits > 0
        push!(notes, "WARNING: $branches_without_limits branches with zero/missing flow limits")
    end

    return notes, errors
end

function main()
    println("PowerSimulations.jl Gate Tests")
    println("Protocol version: v4")
    ts = Dates.format(Dates.now(), "yyyy-mm-ddTHH:MM:SS")
    println("Timestamp: $ts")

    all_results = []
    halt = false

    for t in TESTS
        if halt
            push!(
                all_results,
                (
                    test_id=t.id,
                    label=t.label,
                    file=t.file,
                    status="skip",
                    exp_b=t.buses,
                    exp_br=t.branches,
                    exp_g=t.gens,
                    act_b=0,
                    act_br=0,
                    act_g=0,
                    load_time=0.0,
                    notes=["Skipped due to prior gate failure"],
                    errors=String[],
                ),
            )
            continue
        end

        filepath = joinpath(DATA_DIR, t.file)
        println("\n" * "="^70)
        println("$(t.id): Loading $(t.label) network - $(t.file)")
        println("="^70)

        actual_buses = 0
        actual_branches = 0
        actual_gens = 0
        load_time = 0.0
        notes = String[]
        test_errors = String[]
        status = "fail"

        try
            t0 = time()
            sys = System(filepath)
            load_time = time() - t0

            counts = count_components(sys)
            actual_buses = counts.buses
            actual_branches = counts.branches
            actual_gens = counts.gens

            @printf("  Expected: %d buses / %d branches / %d gens\n", t.buses, t.branches, t.gens)
            @printf(
                "  Actual:   %d buses / %d branches / %d gens\n",
                actual_buses,
                actual_branches,
                actual_gens
            )
            @printf("  Load time: %.2f seconds\n", load_time)

            buses_ok = actual_buses == t.buses
            branches_ok = actual_branches == t.branches
            gens_ok = actual_gens == t.gens

            if !buses_ok
                push!(test_errors, "Bus count mismatch: expected $(t.buses), got $actual_buses")
            end
            if !branches_ok
                push!(
                    test_errors,
                    "Branch count mismatch: expected $(t.branches), got $actual_branches",
                )
            end
            if !gens_ok
                push!(test_errors, "Generator count mismatch: expected $(t.gens), got $actual_gens")
            end

            audit_notes, audit_errors = audit_system(sys)
            append!(notes, audit_notes)
            append!(test_errors, audit_errors)

            if buses_ok && branches_ok && gens_ok
                status = "pass"
            end

        catch e
            push!(test_errors, "Exception during load: $(sprint(showerror, e))")
            @printf("  ERROR: %s\n", sprint(showerror, e))
        end

        println("  Status: $(uppercase(status))")
        if !isempty(test_errors)
            println("  Errors:")
            for err in test_errors
                println("    - $err")
            end
        end
        if !isempty(notes)
            println("  Notes:")
            for n in notes
                println("    - $n")
            end
        end

        push!(
            all_results,
            (
                test_id=t.id,
                label=t.label,
                file=t.file,
                status=status,
                exp_b=t.buses,
                exp_br=t.branches,
                exp_g=t.gens,
                act_b=actual_buses,
                act_br=actual_branches,
                act_g=actual_gens,
                load_time=load_time,
                notes=notes,
                errors=test_errors,
            ),
        )

        if status == "fail" && t.id == "G-1"
            println("\n*** HALT: TINY gate (G-1) failed - disqualifying ***")
            halt = true
        end
    end

    # Summary
    println("\n" * "="^70)
    println("SUMMARY")
    println("="^70)

    scale_cap = "MEDIUM"
    for r in all_results
        symbol = r.status == "pass" ? "PASS" : (r.status == "skip" ? "SKIP" : "FAIL")
        @printf(
            "  %s (%s): %s  [%d/%d/%d vs %d/%d/%d] (%.2fs)\n",
            r.test_id,
            r.label,
            symbol,
            r.act_b,
            r.act_br,
            r.act_g,
            r.exp_b,
            r.exp_br,
            r.exp_g,
            r.load_time
        )
    end

    if all_results[1].status != "pass"
        scale_cap = "NONE"
    elseif all_results[2].status != "pass"
        scale_cap = "TINY"
    elseif all_results[3].status != "pass"
        scale_cap = "SMALL"
    end

    println("\nEffective scale_cap: $scale_cap")
    println("Done.")

    return all_results, scale_cap
end

main()

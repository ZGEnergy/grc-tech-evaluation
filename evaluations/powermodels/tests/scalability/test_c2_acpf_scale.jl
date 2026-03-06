
#= Test C-2: ACPF at MEDIUM (10000 buses) =#

using PowerModels, Ipopt, JuMP, JSON
PowerModels.silence()

function preprocess_data!(data)
    for (i, gen) in data["gen"]
        if !haskey(gen, "cost") || isempty(get(gen, "cost", []))
            gen["model"] = 2
            gen["ncost"] = 2
            gen["cost"] = [20.0, 0.0]
        end
    end
    for (i, br) in data["branch"]
        if get(br, "rate_a", 0.0) == 0.0
            br["rate_a"] = 9999.0
        end
    end
end

function run(network_file::String="/workspace/data/networks/case_ACTIVSg10k.m")
    results = Dict{String,Any}(
        "test_id" => "C-2",
        "test_name" => "acpf_scale",
        "network" => "MEDIUM",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        t_parse = time()
        data = PowerModels.parse_file(network_file)
        parse_time = time() - t_parse
        preprocess_data!(data)

        nbus = length(data["bus"])
        nbranch = length(data["branch"])
        ngen = length(data["gen"])
        results["details"]["num_buses"] = nbus
        results["details"]["num_branches"] = nbranch
        results["details"]["num_generators"] = ngen
        results["details"]["parse_time_seconds"] = round(parse_time; digits=3)

        # Memory measurement
        GC.gc()
        mem_before = Base.gc_live_bytes() / 1024^2

        # Solve AC power flow using compute_ac_pf!
        t_solve = time()
        result_ac = PowerModels.compute_ac_pf(data)
        solve_time = time() - t_solve

        GC.gc()
        mem_after = Base.gc_live_bytes() / 1024^2
        peak_memory = mem_after - mem_before

        results["details"]["solve_time_seconds"] = round(solve_time; digits=4)
        results["details"]["peak_memory_mb"] = round(peak_memory; digits=2)

        # Check convergence
        term_status = result_ac["termination_status"]
        results["details"]["termination_status"] = string(term_status)

        if term_status == LOCALLY_SOLVED || term_status == OPTIMAL
            results["details"]["converges_ac"] = true

            # Extract solution stats
            bus_vm = [bus["vm"] for (_, bus) in result_ac["solution"]["bus"]]
            bus_va = [bus["va"] for (_, bus) in result_ac["solution"]["bus"]]

            results["details"]["vm_min"] = round(minimum(bus_vm); digits=4)
            results["details"]["vm_max"] = round(maximum(bus_vm); digits=4)
            results["details"]["vm_mean"] = round(sum(bus_vm) / length(bus_vm); digits=4)
            results["details"]["va_min_rad"] = round(minimum(bus_va); digits=4)
            results["details"]["va_max_rad"] = round(maximum(bus_va); digits=4)
            results["details"]["total_buses_solved"] = length(bus_vm)

            # Try to get iteration count from Ipopt
            results["details"]["objective"] = get(result_ac, "objective", NaN)

            results["details"]["method"] = "compute_ac_pf (Newton-Raphson via native solver)"
            results["status"] = "pass"
        else
            results["details"]["converges_ac"] = false
            push!(results["errors"], "AC PF did not converge: $term_status")

            # Try with solve_ac_pf (JuMP-based) as fallback
            results["details"]["attempting_fallback"] = "solve_ac_pf with Ipopt"
            t_solve2 = time()
            solver = optimizer_with_attributes(
                Ipopt.Optimizer, "max_iter" => 10000, "print_level" => 0, "tol" => 1e-6
            )
            result_ac2 = solve_ac_pf(data, solver)
            solve_time2 = time() - t_solve2

            term_status2 = result_ac2["termination_status"]
            results["details"]["fallback_status"] = string(term_status2)
            results["details"]["fallback_solve_time"] = round(solve_time2; digits=4)

            if term_status2 == LOCALLY_SOLVED || term_status2 == OPTIMAL
                results["details"]["converges_ac"] = true
                bus_vm2 = [bus["vm"] for (_, bus) in result_ac2["solution"]["bus"]]
                results["details"]["vm_min"] = round(minimum(bus_vm2); digits=4)
                results["details"]["vm_max"] = round(maximum(bus_vm2); digits=4)
                results["details"]["method"] = "solve_ac_pf with Ipopt (fallback)"
                results["status"] = "pass"
            end
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
    finally
        results["wall_clock_seconds"] = time() - t0
    end
    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

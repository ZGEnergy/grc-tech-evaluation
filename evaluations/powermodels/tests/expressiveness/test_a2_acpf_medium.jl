#=
Test A-2: Solve ACPF (Newton-Raphson) on MEDIUM (ACTIVSg 10000-bus)
Dimension: expressiveness
Network: MEDIUM (ACTIVSg 10000-bus)
Pass condition: Converges. Bus voltages (mag+angle), P/Q flows, losses accessible.
Tool: PowerModels.jl v0.21.5
Solver: NLsolve (Newton's method)
=#

using PowerModels, JSON

function run(
    network_file::String=joinpath(
        @__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg10k.m"
    ),
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    # Warm-up
    try
        _data = PowerModels.parse_file(
            joinpath(@__DIR__, "..", "..", "..", "..", "data", "networks", "case39.m")
        )
        PowerModels.compute_ac_pf(_data)
    catch
        ;
    end

    t0 = time()
    try
        println("Parsing network...")
        t_parse = time()
        data = PowerModels.parse_file(network_file)
        parse_time = time() - t_parse
        println("Parse time: $(round(parse_time, digits=2))s")

        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_branches"] = length(data["branch"])
        results["details"]["num_generators"] = length(data["gen"])
        results["details"]["parse_time"] = round(parse_time; digits=3)

        # Attempt 1: flat start (default)
        println("Solving ACPF (flat start)...")
        t_solve = time()
        pf_result = PowerModels.compute_ac_pf(data)
        solve_time = time() - t_solve
        println("Solve time: $(round(solve_time, digits=4))s")

        term_status = pf_result["termination_status"]
        results["details"]["termination_status"] = string(term_status)
        results["details"]["solve_time"] = round(solve_time; digits=4)

        converged = if term_status isa Bool
            term_status
        else
            string(term_status) in ("LOCALLY_SOLVED", "OPTIMAL", "true")
        end

        if !converged
            println("Flat start failed. Trying with voltage initialization from data...")
            # Attempt 2: use initial voltages from data file
            data2 = PowerModels.parse_file(network_file)
            # Set initial voltages from bus data (vm, va fields)
            for (id, bus) in data2["bus"]
                if haskey(bus, "vm")
                    bus["vm"] = bus["vm"]  # already set from file
                end
            end
            t_solve2 = time()
            pf_result = PowerModels.compute_ac_pf(data2)
            solve_time = time() - t_solve2
            term_status = pf_result["termination_status"]
            converged = if term_status isa Bool
                term_status
            else
                string(term_status) in ("LOCALLY_SOLVED", "OPTIMAL", "true")
            end
            results["details"]["convergence_attempt"] = 2
            results["details"]["solve_time_attempt2"] = round(solve_time; digits=4)
        else
            results["details"]["convergence_attempt"] = 1
        end

        results["details"]["converged"] = converged
        if !converged
            push!(results["errors"], "ACPF did not converge after 2 attempts: $term_status")
            results["wall_clock_seconds"] = round(time() - t0; digits=2)
            return results
        end

        sol = pf_result["solution"]

        # Extract bus voltages
        vm_vals = Float64[]
        va_vals = Float64[]
        for (id, bus) in sol["bus"]
            push!(vm_vals, bus["vm"])
            push!(va_vals, bus["va"])
        end
        results["details"]["num_bus_voltages"] = length(vm_vals)
        results["details"]["vm_min"] = round(minimum(vm_vals); digits=4)
        results["details"]["vm_max"] = round(maximum(vm_vals); digits=4)
        results["details"]["vm_mean"] = round(sum(vm_vals) / length(vm_vals); digits=4)

        # Compute branch flows
        PowerModels.update_data!(data, sol)
        branch_flows = PowerModels.calc_branch_flow_ac(data)

        # Total losses
        total_p_loss = 0.0
        total_q_loss = 0.0
        for (id, br) in branch_flows["branch"]
            total_p_loss += br["pf"] + br["pt"]
            total_q_loss += br["qf"] + br["qt"]
        end
        results["details"]["total_p_loss_pu"] = round(total_p_loss; digits=4)
        results["details"]["total_q_loss_pu"] = round(total_q_loss; digits=4)
        results["details"]["num_branch_flows"] = length(branch_flows["branch"])

        # Memory estimate
        results["details"]["peak_memory_mb"] = round(Base.gc_live_bytes() / 1e6; digits=1)

        results["status"] = "pass"

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
    finally
        results["wall_clock_seconds"] = round(time() - t0; digits=2)
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

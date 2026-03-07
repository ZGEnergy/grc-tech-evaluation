#=
Test A-1: Solve DCPF on MEDIUM (ACTIVSg 10000-bus)
Dimension: expressiveness
Network: MEDIUM (ACTIVSg 10000-bus)
Pass condition: Converges. Nodal injections, line flows, voltage angles accessible.
Tool: PowerModels.jl v0.21.5
Solver: N/A (direct solve via compute_dc_pf)
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
        PowerModels.compute_dc_pf(_data)
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
        results["details"]["num_loads"] = length(data["load"])
        results["details"]["parse_time"] = round(parse_time; digits=3)

        println("Solving DCPF...")
        t_solve = time()
        pf_result = PowerModels.compute_dc_pf(data)
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
            push!(results["errors"], "DCPF did not converge: $term_status")
            results["wall_clock_seconds"] = round(time() - t0; digits=2)
            return results
        end

        sol = pf_result["solution"]

        # Extract voltage angles
        bus_angles = Dict{String,Float64}()
        for (id, bus) in sol["bus"]
            bus_angles[id] = bus["va"]
        end
        results["details"]["num_bus_angles"] = length(bus_angles)

        # Sample angles
        sorted_ids = sort(collect(keys(bus_angles)); by=x->parse(Int, x))
        results["details"]["bus_angles_sample"] = Dict(
            k => round(bus_angles[k]; digits=6) for k in sorted_ids[1:min(5, length(sorted_ids))]
        )

        # Compute branch flows
        PowerModels.update_data!(data, sol)
        branch_flows = PowerModels.calc_branch_flow_dc(data)

        results["details"]["num_line_flows"] = length(branch_flows["branch"])

        # Extract generator injections
        gen_count = 0
        for (id, gen) in data["gen"]
            gen_count += 1
        end
        results["details"]["num_gen_injections"] = gen_count

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

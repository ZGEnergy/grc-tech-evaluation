#=
Test A-1: Solve DCPF on TINY (IEEE 39-bus)
Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Converges. Nodal injections, line flows, voltage angles accessible as structured output.
Tool: PowerModels.jl v0.21.5
Solver: N/A (direct solve via compute_dc_pf)
=#

using PowerModels, JSON

function is_converged(term_status)
    # Native PF functions return Bool; JuMP-based return MOI status strings
    if term_status isa Bool
        return term_status
    end
    s = string(term_status)
    return s in ("LOCALLY_SOLVED", "OPTIMAL", "true")
end

function run(
    network_file::String=joinpath(@__DIR__, "..", "..", "..", "..", "data", "networks", "case39.m")
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    # Warm-up run (exclude JIT from timing)
    try
        _data = PowerModels.parse_file(network_file)
        PowerModels.compute_dc_pf(_data)
    catch
        ;
    end

    t0 = time()
    try
        # Parse network
        data = PowerModels.parse_file(network_file)

        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_branches"] = length(data["branch"])
        results["details"]["num_generators"] = length(data["gen"])

        # Solve DC power flow (native linear solve, no JuMP)
        pf_result = PowerModels.compute_dc_pf(data)

        term_status = pf_result["termination_status"]
        results["details"]["termination_status"] = string(term_status)
        results["details"]["solve_time"] = get(pf_result, "solve_time", nothing)

        if !is_converged(term_status)
            push!(results["errors"], "DCPF did not converge: $term_status")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        sol = pf_result["solution"]

        # Extract voltage angles (radians)
        bus_angles = Dict{String,Float64}()
        for (id, bus) in sol["bus"]
            bus_angles[id] = bus["va"]
        end
        results["details"]["bus_angles_sample"] = Dict(
            k => v for
            (k, v) in Iterators.take(sort(collect(bus_angles); by=x->parse(Int, x[1])), 5)
        )

        # Compute branch flows using DC branch flow calculation
        PowerModels.update_data!(data, sol)
        branch_flows = PowerModels.calc_branch_flow_dc(data)

        # Extract line flows
        line_flows = Dict{String,Dict{String,Float64}}()
        for (id, br) in branch_flows["branch"]
            line_flows[id] = Dict("pf" => br["pf"], "pt" => br["pt"])
        end
        results["details"]["line_flows_sample"] = Dict(
            k => v for
            (k, v) in Iterators.take(sort(collect(line_flows); by=x->parse(Int, x[1])), 5)
        )

        # Extract generator injections from data (after update_data!, gen pg is set)
        gen_injections = Dict{String,Float64}()
        for (id, gen) in data["gen"]
            gen_injections[id] = gen["pg"]
        end
        results["details"]["generator_injections"] = gen_injections

        # Also check if solution has gen data
        if haskey(sol, "gen")
            for (id, gen) in sol["gen"]
                gen_injections[id] = gen["pg"]
            end
        end

        # Compute net bus injections (gen - load at each bus)
        bus_injections = Dict{String,Float64}()
        for (id, _) in data["bus"]
            bus_injections[id] = 0.0
        end
        for (_, gen) in data["gen"]
            bus_id = string(gen["gen_bus"])
            bus_injections[bus_id] = get(bus_injections, bus_id, 0.0) + gen["pg"]
        end
        for (_, load) in data["load"]
            bus_id = string(load["load_bus"])
            bus_injections[bus_id] = get(bus_injections, bus_id, 0.0) - load["pd"]
        end
        results["details"]["net_bus_injections_sample"] = Dict(
            k => round(v; digits=4) for
            (k, v) in Iterators.take(sort(collect(bus_injections); by=x->parse(Int, x[1])), 5)
        )

        results["details"]["num_bus_angles"] = length(bus_angles)
        results["details"]["num_line_flows"] = length(line_flows)
        results["details"]["num_gen_injections"] = length(gen_injections)

        results["status"] = "pass"

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

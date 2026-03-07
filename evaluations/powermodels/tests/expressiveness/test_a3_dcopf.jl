#=
Test A-3: Solve DC OPF with gen costs and line flow limits on TINY (IEEE 39-bus)
Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Converges. Optimal dispatch and LMPs/shadow prices extractable.
Tool: PowerModels.jl v0.21.5
Solver: HiGHS
=#

using PowerModels, JuMP, HiGHS, JSON

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

    # Warm-up run
    try
        _data = PowerModels.parse_file(network_file)
        PowerModels.solve_dc_opf(_data, HiGHS.Optimizer)
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

        # Solver settings
        optimizer = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => true,
        )

        # Solve DC OPF with duals enabled for LMP extraction
        opf_result = PowerModels.solve_dc_opf(
            data, optimizer; setting=Dict("output" => Dict("duals" => true))
        )

        term_status = string(opf_result["termination_status"])
        results["details"]["termination_status"] = term_status
        results["details"]["solve_time"] = opf_result["solve_time"]
        results["details"]["objective"] = opf_result["objective"]

        if !(term_status in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"])
            push!(results["errors"], "DC OPF did not converge: $term_status")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        sol = opf_result["solution"]

        # Extract optimal dispatch
        gen_dispatch = Dict{String,Dict{String,Any}}()
        for (id, gen) in sol["gen"]
            gen_dispatch[id] = Dict("pg" => gen["pg"], "gen_bus" => data["gen"][id]["gen_bus"])
        end
        results["details"]["gen_dispatch"] = gen_dispatch

        # Extract LMPs (shadow prices on power balance constraints)
        bus_lmps = Dict{String,Float64}()
        for (id, bus) in sol["bus"]
            if haskey(bus, "lam_kcl_r")
                bus_lmps[id] = bus["lam_kcl_r"]
            end
        end
        results["details"]["bus_lmps"] = bus_lmps
        results["details"]["num_lmps_extracted"] = length(bus_lmps)

        if isempty(bus_lmps)
            push!(results["errors"], "No LMPs (lam_kcl_r) found in solution")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        lmp_vals = collect(values(bus_lmps))
        results["details"]["lmp_min"] = minimum(lmp_vals)
        results["details"]["lmp_max"] = maximum(lmp_vals)
        results["details"]["lmp_mean"] = sum(lmp_vals) / length(lmp_vals)

        # Extract branch flows
        branch_flows = Dict{String,Dict{String,Any}}()
        for (id, br) in sol["branch"]
            branch_flows[id] = Dict("pf" => br["pf"])
        end
        results["details"]["branch_flows_sample"] = Dict(
            k => v for
            (k, v) in Iterators.take(sort(collect(branch_flows); by=x->parse(Int, x[1])), 5)
        )

        # Total generation
        total_gen = sum(g["pg"] for (_, g) in sol["gen"])
        results["details"]["total_generation_pu"] = total_gen

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

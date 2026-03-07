#=
Test A-3: Solve DC OPF on MEDIUM (ACTIVSg 10000-bus)
Dimension: expressiveness
Network: MEDIUM (ACTIVSg 10000-bus)
Pass condition: Solves. Dispatch, LMPs, branch flows accessible.
Tool: PowerModels.jl v0.21.5
Solver: HiGHS
Note: ACTIVSg10k has branches with zero rate_a. PowerModels handles this by
      setting them to a large default value internally.
=#

using PowerModels, JuMP, HiGHS, Ipopt, JSON

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

    t0 = time()
    try
        println("Parsing network...")
        t_parse = time()
        data = PowerModels.parse_file(network_file)
        parse_time = time() - t_parse
        println("Parse time: $(round(parse_time, digits=2))s")

        # Fix generators with empty cost arrays
        n_fixed = 0
        for (id, gen) in data["gen"]
            if gen["model"] == 2 && (gen["ncost"] == 0 || isempty(gen["cost"]))
                gen["cost"] = [0.0, 0.0, 0.0]
                gen["ncost"] = 3
                n_fixed += 1
            end
        end

        # Count branches with zero rate_a
        zero_rate = count(br -> br["rate_a"] == 0.0, values(data["branch"]))

        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_branches"] = length(data["branch"])
        results["details"]["num_generators"] = length(data["gen"])
        results["details"]["generators_cost_fixed"] = n_fixed
        results["details"]["branches_zero_rate_a"] = zero_rate
        results["details"]["parse_time"] = round(parse_time; digits=3)

        # Try Ipopt first (handles QP natively, HiGHS may have issues with large QP)
        println("Solving DC OPF with Ipopt...")
        optimizer = JuMP.optimizer_with_attributes(
            Ipopt.Optimizer, "max_iter" => 10000, "tol" => 1e-6, "print_level" => 3
        )

        t_solve = time()
        result = PowerModels.solve_dc_opf(
            data, optimizer; setting=Dict("output" => Dict("duals" => true))
        )
        solve_time = time() - t_solve
        println("Solve time: $(round(solve_time, digits=2))s")

        term = string(result["termination_status"])
        results["details"]["termination_status"] = term
        results["details"]["objective"] = round(result["objective"]; digits=2)
        results["details"]["solve_time"] = round(solve_time; digits=3)
        results["details"]["solver_used"] = "Ipopt"

        if !(term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"])
            # Fallback to HiGHS
            println("Ipopt result: $term. Trying HiGHS...")
            optimizer2 = JuMP.optimizer_with_attributes(
                HiGHS.Optimizer,
                "time_limit" => 300.0,
                "presolve" => "on",
                "threads" => 1,
                "output_flag" => true,
            )
            t_solve2 = time()
            result = PowerModels.solve_dc_opf(
                data, optimizer2; setting=Dict("output" => Dict("duals" => true))
            )
            solve_time = time() - t_solve2
            term = string(result["termination_status"])
            results["details"]["termination_status"] = term
            results["details"]["objective"] = round(result["objective"]; digits=2)
            results["details"]["solve_time_highs"] = round(solve_time; digits=3)
            results["details"]["solver_used"] = "HiGHS (fallback)"
        end

        if !(term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"])
            push!(results["errors"], "DC OPF did not converge: $term")
            results["wall_clock_seconds"] = round(time() - t0; digits=2)
            return results
        end

        # Extract dispatch
        total_gen = 0.0
        gen_count = 0
        for (id, gen) in result["solution"]["gen"]
            total_gen += gen["pg"]
            gen_count += 1
        end
        results["details"]["total_generation_pu"] = round(total_gen; digits=2)
        results["details"]["num_gen_dispatched"] = gen_count

        # Extract LMPs
        lmp_vals = Float64[]
        for (id, bus) in result["solution"]["bus"]
            if haskey(bus, "lam_kcl_r")
                push!(lmp_vals, bus["lam_kcl_r"])
            end
        end
        if !isempty(lmp_vals)
            results["details"]["num_lmps"] = length(lmp_vals)
            results["details"]["lmp_min"] = round(minimum(lmp_vals); digits=2)
            results["details"]["lmp_max"] = round(maximum(lmp_vals); digits=2)
            results["details"]["lmp_mean"] = round(sum(lmp_vals) / length(lmp_vals); digits=2)
            results["details"]["lmp_range"] = round(maximum(lmp_vals) - minimum(lmp_vals); digits=2)
        end

        # Branch flows
        n_flows = length(result["solution"]["branch"])
        results["details"]["num_branch_flows"] = n_flows

        results["details"]["peak_memory_mb"] = round(Base.gc_live_bytes() / 1e6; digits=1)

        results["status"] = "pass"

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        push!(results["errors"], sprint(showerror, e, catch_backtrace()))
    finally
        results["wall_clock_seconds"] = round(time() - t0; digits=2)
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end


#= Test C-7: Solver swap — DC OPF at MEDIUM with HiGHS, GLPK, SCIP, Ipopt =#

using PowerModels, JuMP, HiGHS, GLPK, SCIP, Ipopt, JSON
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
        "test_id" => "C-7",
        "test_name" => "solver_swap",
        "network" => "MEDIUM",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        data = PowerModels.parse_file(network_file)
        preprocess_data!(data)

        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_branches"] = length(data["branch"])
        results["details"]["num_generators"] = length(data["gen"])

        solvers = Dict(
            "HiGHS" => HiGHS.Optimizer,
            "GLPK" => GLPK.Optimizer,
            "SCIP" => optimizer_with_attributes(
                SCIP.Optimizer, "display/verblevel" => 0, "limits/time" => 300.0
            ),
            "Ipopt" =>
                optimizer_with_attributes(Ipopt.Optimizer, "print_level" => 0, "max_iter" => 10000),
        )

        solver_results = Dict{String,Any}()
        solver_order = ["HiGHS", "GLPK", "SCIP", "Ipopt"]

        for name in solver_order
            solver = solvers[name]
            GC.gc()
            mem_before = Base.gc_live_bytes() / 1024^2
            t_s = time()
            try
                result = solve_dc_opf(data, solver; setting=Dict("output" => Dict("duals" => true)))
                solve_time = time() - t_s
                GC.gc()
                mem_after = Base.gc_live_bytes() / 1024^2

                solver_results[name] = Dict(
                    "wall_clock_seconds" => round(solve_time; digits=4),
                    "peak_memory_mb" => round(mem_after - mem_before; digits=2),
                    "termination_status" => string(result["termination_status"]),
                    "objective" => result["objective"],
                    "success" => true,
                )
            catch e
                solve_time = time() - t_s
                solver_results[name] = Dict(
                    "wall_clock_seconds" => round(solve_time; digits=4),
                    "termination_status" => "ERROR",
                    "error" => string(typeof(e), ": ", sprint(showerror, e)),
                    "success" => false,
                )
            end
        end

        results["details"]["solver_results"] = solver_results
        results["details"]["reformulation_required"] = false
        results["details"]["swap_mechanism"] = "Change optimizer argument to solve_dc_opf — no reformulation, no code changes beyond solver selection"

        # Compare objectives across successful solvers
        successful = [(name, sr) for (name, sr) in solver_results if get(sr, "success", false)]
        if length(successful) >= 2
            objs = [(name, sr["objective"]) for (name, sr) in successful]
            max_obj = maximum(o for (_, o) in objs)
            min_obj = minimum(o for (_, o) in objs)
            results["details"]["objective_range"] = round(max_obj - min_obj; digits=6)
            results["details"]["objectives_consistent"] = (max_obj - min_obj) < 1.0
        end

        n_success = count(get(sr, "success", false) for (_, sr) in solver_results)
        results["details"]["solvers_successful"] = n_success
        results["details"]["solvers_total"] = length(solver_order)

        if n_success >= 2
            results["status"] = "pass"
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

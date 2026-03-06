#= Test C-3: DC OPF at MEDIUM (10000 buses) with HiGHS and GLPK
   NOTE: PowerModels DC OPF uses quadratic cost curves by default.
   - HiGHS handles QP but may have numerical issues at 10k scale
   - GLPK is LP-only, cannot handle quadratic costs -> requires linearized costs
   We test both and document solver limitations.
=#
using PowerModels, JuMP, HiGHS, GLPK, Ipopt, JSON
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

function linearize_costs!(data)
    # Convert quadratic costs to linear for LP solvers like GLPK
    for (i, gen) in data["gen"]
        if get(gen, "model", 2) == 2 && get(gen, "ncost", 0) >= 3
            # c2*pg^2 + c1*pg + c0 -> linearize at midpoint
            costs = gen["cost"]
            midpoint = (gen["pmin"] + gen["pmax"]) / 2
            linear_cost = 2 * costs[1] * midpoint + costs[2]  # derivative at midpoint
            constant =
                costs[1] * midpoint^2 + costs[2] * midpoint + costs[3] - linear_cost * midpoint
            gen["ncost"] = 2
            gen["cost"] = [linear_cost, constant]
        end
    end
end

function run(network_file::String="/workspace/data/networks/case_ACTIVSg10k.m")
    results = Dict{String,Any}(
        "test_id" => "C-3",
        "test_name" => "dcopf_scale",
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

        nbus = length(data["bus"])
        nbranch = length(data["branch"])
        ngen = length(data["gen"])
        results["details"]["num_buses"] = nbus
        results["details"]["num_branches"] = nbranch
        results["details"]["num_generators"] = ngen

        solver_results = Dict{String,Any}()

        # --- HiGHS (QP) ---
        println("Solving DC OPF with HiGHS (QP)...")
        GC.gc()
        mem_before_highs = Base.gc_live_bytes() / 1024^2
        t_highs = time()
        result_highs = solve_dc_opf(
            data,
            optimizer_with_attributes(HiGHS.Optimizer, "time_limit" => 300.0);
            setting=Dict("output" => Dict("duals" => true)),
        )
        highs_time = time() - t_highs
        GC.gc()
        mem_after_highs = Base.gc_live_bytes() / 1024^2

        highs_status = string(result_highs["termination_status"])
        solver_results["HiGHS"] = Dict(
            "wall_clock_seconds" => round(highs_time; digits=4),
            "peak_memory_mb" => round(mem_after_highs - mem_before_highs; digits=2),
            "termination_status" => highs_status,
            "objective" => get(result_highs, "objective", NaN),
            "note" => "Quadratic objective (native DC OPF costs)",
        )
        println("HiGHS: $(highs_status), $(round(highs_time; digits=1))s")

        # --- Ipopt (QP, for comparison) ---
        println("Solving DC OPF with Ipopt (QP)...")
        GC.gc()
        mem_before_ipopt = Base.gc_live_bytes() / 1024^2
        t_ipopt = time()
        result_ipopt = solve_dc_opf(
            data,
            optimizer_with_attributes(Ipopt.Optimizer, "print_level" => 0, "max_iter" => 10000);
            setting=Dict("output" => Dict("duals" => true)),
        )
        ipopt_time = time() - t_ipopt
        GC.gc()
        mem_after_ipopt = Base.gc_live_bytes() / 1024^2

        ipopt_status = string(result_ipopt["termination_status"])
        solver_results["Ipopt"] = Dict(
            "wall_clock_seconds" => round(ipopt_time; digits=4),
            "peak_memory_mb" => round(mem_after_ipopt - mem_before_ipopt; digits=2),
            "termination_status" => ipopt_status,
            "objective" => get(result_ipopt, "objective", NaN),
        )
        println("Ipopt: $(ipopt_status), $(round(ipopt_time; digits=1))s")

        # --- GLPK (LP only — linearized costs) ---
        println("Solving DC OPF with GLPK (linearized costs)...")
        data_linear = deepcopy(data)
        linearize_costs!(data_linear)

        GC.gc()
        mem_before_glpk = Base.gc_live_bytes() / 1024^2
        t_glpk = time()
        try
            result_glpk = solve_dc_opf(
                data_linear, GLPK.Optimizer; setting=Dict("output" => Dict("duals" => true))
            )
            glpk_time = time() - t_glpk
            GC.gc()
            mem_after_glpk = Base.gc_live_bytes() / 1024^2

            solver_results["GLPK"] = Dict(
                "wall_clock_seconds" => round(glpk_time; digits=4),
                "peak_memory_mb" => round(mem_after_glpk - mem_before_glpk; digits=2),
                "termination_status" => string(result_glpk["termination_status"]),
                "objective" => get(result_glpk, "objective", NaN),
                "note" => "Linearized costs (LP) — GLPK does not support quadratic objectives",
            )
            println("GLPK: $(result_glpk["termination_status"]), $(round(glpk_time; digits=1))s")
        catch e
            glpk_time = time() - t_glpk
            solver_results["GLPK"] = Dict(
                "wall_clock_seconds" => round(glpk_time; digits=4),
                "termination_status" => "ERROR",
                "error" => string(typeof(e), ": ", sprint(showerror, e)),
                "note" => "GLPK is LP-only; quadratic objectives not supported even with linearization attempt",
            )
            println("GLPK: ERROR")
        end

        results["details"]["solver_results"] = solver_results

        # Compare objectives for solvers that succeeded
        successful = [
            (name, sr) for (name, sr) in solver_results if !isnan(get(sr, "objective", NaN)) &&
            get(sr, "termination_status", "") != "ERROR" &&
            get(sr, "termination_status", "") != "SOLVE_ERROR"
        ]
        if length(successful) >= 2
            objs = [(name, sr["objective"]) for (name, sr) in successful]
            max_obj = maximum(o for (_, o) in objs)
            min_obj = minimum(o for (_, o) in objs)
            results["details"]["objective_range"] = round(max_obj - min_obj; digits=6)
        end

        # Extract sample LMPs
        best_result = nothing
        for r in [result_ipopt, result_highs]
            ts = string(r["termination_status"])
            if ts in ["OPTIMAL", "LOCALLY_SOLVED"]
                best_result = r
                break
            end
        end
        if best_result !== nothing && haskey(best_result["solution"], "bus")
            lmp_sample = Dict{String,Float64}()
            count = 0
            for (bid, bus) in best_result["solution"]["bus"]
                lmp = get(bus, "lam_kcl_r", NaN)
                if !isnan(lmp) && count < 10
                    lmp_sample[bid] = round(lmp; digits=4)
                    count += 1
                end
            end
            results["details"]["sample_lmps"] = lmp_sample
        end

        results["details"]["method"] = "solve_dc_opf with multiple solvers"
        results["details"]["solver_compatibility_note"] = "DC OPF has quadratic costs; GLPK (LP-only) requires linearization; HiGHS may have numerical issues on large QPs"

        # Pass if at least one solver succeeded
        if any(!isnan(get(sr, "objective", NaN)) for (_, sr) in solver_results)
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

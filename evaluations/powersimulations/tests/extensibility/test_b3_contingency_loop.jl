#=
Test B-3: Contingency Loop (N-1 DCPF, all 46 branches)

Dimension: extensibility
Network: TINY (case39.m — IEEE 39-bus, 46 branches)
Pass condition: Runs in a loop without re-parsing the base model from file each
               iteration. Base model cloned or modified in-place.
Tool: PowerSimulations.jl v0.30.2 (via PowerFlows.jl)
=#

using PowerSystems
using PowerFlows
using JSON
using DataFrames

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        # 1. Load system ONCE
        t_load = time()
        sys = System(network_file)
        load_time = time() - t_load
        results["details"]["system_load_time_seconds"] = load_time

        n_buses = length(collect(get_components(ACBus, sys)))
        all_branches = collect(get_components(Branch, sys))
        n_branches = length(all_branches)
        results["details"]["network"] = Dict("buses" => n_buses, "branches" => n_branches)

        # 2. Solve base case DCPF
        t_base = time()
        base_result = solve_powerflow(DCPowerFlow(), sys)
        base_time = time() - t_base
        results["details"]["base_solve_time_seconds"] = base_time

        if base_result === nothing || isempty(base_result)
            push!(results["errors"], "Base case DCPF did not converge")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # Extract base case flows for reference
        result_key = first(keys(base_result))
        base_flow_df = base_result[result_key]["flow_results"]

        # Compute base case line loading (|flow| / rating)
        # For DCPF, we use P_from_to as the flow
        results["details"]["base_flow_columns"] = string.(names(base_flow_df))

        # 3. N-1 contingency loop — modify in-place, solve, restore
        contingency_results = Dict{String,Any}[]
        contingency_times = Float64[]
        n_converged = 0
        n_diverged = 0
        max_loading_overall = 0.0
        worst_contingency = ""
        worst_branch = ""

        # Get branch ratings for loading calculation
        branch_ratings = Dict{String,Float64}()
        for branch in all_branches
            rating = get_rating(branch)
            branch_ratings[get_name(branch)] = rating
        end

        # JIT warmup: first contingency will include compilation time
        # We track per-contingency times to show JIT effect

        t_loop = time()
        for (i, branch) in enumerate(all_branches)
            branch_name = get_name(branch)
            was_available = get_available(branch)

            t_cont = time()

            # Disable branch (in-place modification — NO reload from file)
            set_available!(branch, false)

            # Solve DCPF with this branch out
            pf_result = nothing
            converged = false
            try
                pf_result = solve_powerflow(DCPowerFlow(), sys)
                converged = pf_result !== nothing && !isempty(pf_result)
            catch e
                # Some contingencies may cause island formation => solver error
                converged = false
            end

            cont_time = time() - t_cont
            push!(contingency_times, cont_time)

            cont_record = Dict{String,Any}(
                "contingency_branch" => branch_name,
                "contingency_index" => i,
                "converged" => converged,
                "solve_time_seconds" => cont_time,
            )

            if converged
                n_converged += 1

                # Extract flows and compute max loading
                rk = first(keys(pf_result))
                flow_df = pf_result[rk]["flow_results"]

                max_loading = 0.0
                max_loading_branch = ""
                for row_i in 1:nrow(flow_df)
                    line_name = flow_df[row_i, "line_name"]
                    p_flow = abs(flow_df[row_i, "P_from_to"])
                    rating = get(branch_ratings, line_name, Inf)
                    if rating > 0
                        loading = p_flow / rating
                        if loading > max_loading
                            max_loading = loading
                            max_loading_branch = line_name
                        end
                    end
                end

                cont_record["max_loading"] = max_loading
                cont_record["max_loading_branch"] = max_loading_branch

                if max_loading > max_loading_overall
                    max_loading_overall = max_loading
                    worst_contingency = branch_name
                    worst_branch = max_loading_branch
                end
            else
                n_diverged += 1
                cont_record["max_loading"] = nothing
            end

            push!(contingency_results, cont_record)

            # Restore branch (in-place — NO reload)
            set_available!(branch, was_available)
        end
        loop_time = time() - t_loop

        # 4. Timing summary
        results["details"]["loop_time_seconds"] = loop_time
        results["details"]["n_contingencies"] = n_branches
        results["details"]["n_converged"] = n_converged
        results["details"]["n_diverged"] = n_diverged
        results["details"]["per_contingency_avg_seconds"] = loop_time / n_branches

        # Separate JIT (first solve) from steady-state
        if length(contingency_times) >= 3
            first_time = contingency_times[1]
            rest_times = contingency_times[2:end]
            results["details"]["first_contingency_time_seconds"] = first_time
            results["details"]["avg_subsequent_time_seconds"] = sum(rest_times) / length(rest_times)
            results["details"]["min_contingency_time_seconds"] = minimum(rest_times)
            results["details"]["max_contingency_time_seconds"] = maximum(rest_times)
        end

        # 5. Overall results
        results["details"]["max_loading_overall"] = max_loading_overall
        results["details"]["worst_contingency"] = worst_contingency
        results["details"]["worst_overloaded_branch"] = worst_branch

        # 6. Top 5 worst contingencies
        converged_results = filter(r -> r["converged"], contingency_results)
        sort!(converged_results; by=r -> -get(r, "max_loading", 0.0))
        results["details"]["top5_contingencies"] = converged_results[1:min(
            5, length(converged_results)
        )]

        # 7. Method documentation
        results["details"]["method"] = Dict(
            "model_reuse" => "In-place modification via set_available!(branch, false/true)",
            "no_file_reload" => true,
            "approach" => "Load system once, toggle branch availability, solve DCPF, restore",
            "solver" => "PowerFlows.jl DCPowerFlow() — direct linear solve, no external optimizer",
        )

        # Did it work?
        if n_converged > 0
            results["status"] = "pass"
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

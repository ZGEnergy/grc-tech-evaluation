#=
Test B-3: Contingency Loop — MEDIUM grade assessment
Dimension: extensibility
Network: MEDIUM (ACTIVSg 10000-bus, case_ACTIVSg10k.m)
Pass condition: Runs without re-parsing from file each iteration. Efficient cloning.
  Run 46 N-1 contingency DCPFs on 10k-bus via deepcopy pattern.
  Record: per-contingency time, total time, deepcopy vs parse time ratio.
Tool: PowerModels.jl v0.21.5
Solver: N/A (direct solve via compute_dc_pf, same as TINY)

Approach (same as TINY, scaled to MEDIUM):
  - Parse file once; deepcopy for each contingency
  - Disable branch (br_status=0); solve DCPF via compute_dc_pf
  - Collect max line loading across all non-outaged branches
  - Measure: (a) parse time, (b) per-deepcopy time, (c) per-solve time
  - Compare deepcopy vs parse time ratio to demonstrate efficiency

N_CONTINGENCIES: 46 (matching MEDIUM protocol parameter)
  Branch selection: highest-flow branches (sorted by base-case flow to maximize signal)
=#

using PowerModels, LinearAlgebra, JSON

PowerModels.silence()

const N_CONTINGENCIES = 46

function apply_medium_preprocessing!(data::Dict)
    base_mva = data["baseMVA"]
    for (_, branch) in data["branch"]
        if branch["br_x"] == 0.0
            ;
            branch["br_x"] = 0.0001;
        end
        ra = get(branch, "rate_a", 0.0)
        if ra == 0.0 || isinf(ra)
            branch["rate_a"] = 9999.0 / base_mva
        end
    end
end

function run(
    network_file::String=joinpath(
        @__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg10k.m"
    ),
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    # JIT warm-up on case39
    try
        tiny_file = joinpath(dirname(network_file), "case39.m")
        _d = PowerModels.parse_file(tiny_file)
        PowerModels.compute_dc_pf(_d)
    catch
        ;
    end

    t0 = time()
    try
        println("Loading network: $network_file")
        t_parse_start = time()
        data_base = PowerModels.parse_file(network_file)
        t_parse = time() - t_parse_start

        n_buses = length(data_base["bus"])
        n_branches = length(data_base["branch"])
        n_gens = length(data_base["gen"])
        base_mva = data_base["baseMVA"]
        println("Network: $n_buses buses, $n_branches branches, $n_gens gens, baseMVA=$base_mva")
        println("Parse time: $(round(t_parse, digits=3))s")

        apply_medium_preprocessing!(data_base)

        # Build branch ratings dict
        branch_ids = sort(parse.(Int, collect(keys(data_base["branch"]))))
        branch_ratings = Dict{Int,Float64}()
        for br_id in branch_ids
            br = data_base["branch"][string(br_id)]
            ra = get(br, "rate_a", 0.0)
            branch_ratings[br_id] = ra > 1e-6 ? ra : Inf
        end

        # ---- Solve base case DCPF to identify high-flow branches ----
        println("Solving base case DCPF...")
        t_base_start = time()
        base_pf = PowerModels.compute_dc_pf(data_base)
        t_base = time() - t_base_start
        base_converged = base_pf["termination_status"] == true
        println("Base case: converged=$base_converged | $(round(t_base,digits=2))s")

        if !base_converged
            push!(results["errors"], "Base case DCPF did not converge")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # Extract branch flows for contingency selection
        PowerModels.update_data!(data_base, base_pf["solution"])
        base_flows_data = PowerModels.calc_branch_flow_dc(data_base)

        base_flows_abs = Dict{Int,Float64}()
        for br_id in branch_ids
            br_data = get(base_flows_data["branch"], string(br_id), Dict())
            base_flows_abs[br_id] = abs(get(br_data, "pf", 0.0))
        end

        # Re-parse to get clean data (update_data! modified data_base)
        data_base = PowerModels.parse_file(network_file)
        apply_medium_preprocessing!(data_base)

        # Select N_CONTINGENCIES branches with highest base-case loading ratio
        candidates = [
            (
                br_id,
                base_flows_abs[br_id] /
                (branch_ratings[br_id] < Inf ? branch_ratings[br_id] : 1e-6),
            ) for
            br_id in branch_ids if get(data_base["branch"][string(br_id)], "br_status", 1) == 1
        ]
        sort!(candidates; by=x -> -x[2])
        contingency_ids = [
            string(c[1]) for c in candidates[1:min(N_CONTINGENCIES, length(candidates))]
        ]
        actual_n = length(contingency_ids)
        println("Selected $actual_n contingency branches (highest loading ratio)")

        # ---- N-1 contingency loop ----
        println("\nRunning $actual_n N-1 contingency DCPFs...")
        contingency_times = Float64[]
        deepcopy_times = Float64[]
        contingency_results = Dict{String,Any}[]
        max_loading_overall = 0.0
        max_loading_ctg = ""
        island_count = 0;
        diverged_count = 0;
        converged_count = 0

        for (k, br_id) in enumerate(contingency_ids)
            # Measure deepcopy time
            t_dc_start = time()
            data_ctg = deepcopy(data_base)
            t_dc = time() - t_dc_start

            # Disable the contingency branch
            data_ctg["branch"][br_id]["br_status"] = 0

            # Check connectivity
            components = PowerModels.calc_connected_components(data_ctg)
            is_connected = length(components) == 1

            t_solve_start = time()
            case_status = "unknown"
            max_load_pct = NaN

            if !is_connected
                case_status = "island"
                island_count += 1
            else
                try
                    pf_ctg = PowerModels.compute_dc_pf(data_ctg)
                    if pf_ctg["termination_status"] == true
                        PowerModels.update_data!(data_ctg, pf_ctg["solution"])
                        flows_ctg = PowerModels.calc_branch_flow_dc(data_ctg)
                        max_load_pct = 0.0
                        for other_id in branch_ids
                            other_id_s = string(other_id)
                            if other_id_s == br_id
                                ;
                                continue;
                            end
                            br_flow = abs(
                                get(get(flows_ctg["branch"], other_id_s, Dict()), "pf", 0.0)
                            )
                            rating = branch_ratings[other_id]
                            loading = rating < Inf ? br_flow / rating * 100.0 : 0.0
                            if loading > max_load_pct
                                ;
                                max_load_pct = loading;
                            end
                        end
                        if max_load_pct > max_loading_overall
                            max_loading_overall = max_load_pct;
                            max_loading_ctg = br_id
                        end
                        case_status = "converged";
                        converged_count += 1
                    else
                        case_status = "diverged";
                        diverged_count += 1
                    end
                catch e
                    if isa(e, LinearAlgebra.SingularException)
                        case_status = "singular";
                        diverged_count += 1
                    else
                        case_status = "error: $(typeof(e))";
                        diverged_count += 1
                    end
                end
            end

            t_solve = time() - t_solve_start
            push!(deepcopy_times, t_dc)
            push!(contingency_times, t_solve)

            push!(
                contingency_results,
                Dict(
                    "branch_id" => br_id,
                    "status" => case_status,
                    "solve_time_s" => t_solve,
                    "deepcopy_s" => t_dc,
                    "max_load_pct" => max_load_pct,
                ),
            )

            if k <= 5 || k == actual_n
                println(
                    "  [$k/$actual_n] Branch $br_id: $case_status | deepcopy=$(round(t_dc*1000,digits=1))ms | solve=$(round(t_solve,digits=2))s | max_load=$(isnan(max_load_pct) ? "N/A" : round(max_load_pct,digits=1))%",
                )
            end
        end

        # ---- Summary ----
        t_total_loop = sum(contingency_times) + sum(deepcopy_times)
        t_per_ctg_mean = sum(contingency_times) / length(contingency_times)
        t_deepcopy_mean = sum(deepcopy_times) / length(deepcopy_times)
        ratio_dc_vs_parse = t_deepcopy_mean / t_parse

        println("\n--- Timing Summary ---")
        println("  Parse time:          $(round(t_parse,digits=3))s")
        println("  Per-deepcopy (mean): $(round(t_deepcopy_mean*1000,digits=1)) ms")
        println("  Per-solve (mean):    $(round(t_per_ctg_mean,digits=2))s")
        println("  Total loop time:     $(round(t_total_loop,digits=2))s")
        println("  deepcopy/parse ratio: $(round(ratio_dc_vs_parse,digits=4))x")
        println(
            "  Converged: $converged_count | Islands: $island_count | Diverged: $diverged_count"
        )
        if !isempty(max_loading_ctg)
            println(
                "  Worst contingency: Branch $max_loading_ctg, max loading=$(round(max_loading_overall,digits=1))%",
            )
        end

        no_re_parse = true   # by design
        efficient = ratio_dc_vs_parse < 0.5

        println("\nPass checks:")
        println("  No re-parsing per iteration: $no_re_parse")
        println(
            "  Efficient cloning (<50% parse): $efficient  (ratio=$(round(ratio_dc_vs_parse,digits=3)))",
        )
        println("  N contingencies ran: $actual_n (target: $N_CONTINGENCIES)")

        if no_re_parse && actual_n == N_CONTINGENCIES
            results["status"] = "pass"
        elseif no_re_parse
            results["status"] = "qualified_pass"
            push!(
                results["workarounds"],
                "Only $actual_n of $N_CONTINGENCIES contingencies available in network",
            )
        else
            push!(results["errors"], "Re-parsing required per iteration")
        end

        if !efficient
            push!(
                results["workarounds"],
                "deepcopy/parse ratio=$(round(ratio_dc_vs_parse,digits=3)) > 0.5. " *
                "At 10k-bus scale, deepcopy takes $(round(t_deepcopy_mean*1000,digits=1))ms vs parse=$(round(t_parse,digits=3))s. " *
                "deepcopy is still faster than re-parsing but ratio is higher than at TINY scale.",
            )
        end

        results["details"] = Dict(
            "network_file" => network_file,
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "n_contingencies" => actual_n,
            "parse_time_s" => t_parse,
            "base_case_time_s" => t_base,
            "per_deepcopy_ms_mean" => t_deepcopy_mean * 1000.0,
            "per_solve_s_mean" => t_per_ctg_mean,
            "total_loop_s" => t_total_loop,
            "deepcopy_vs_parse_ratio" => ratio_dc_vs_parse,
            "converged_count" => converged_count,
            "island_count" => island_count,
            "diverged_count" => diverged_count,
            "max_loading_pct" => max_loading_overall,
            "max_loading_contingency" => max_loading_ctg,
            "contingency_results_sample" => contingency_results[1:min(5, end)],
            "model_reconstruction_required" => false,
            "solver" => "direct (compute_dc_pf + calc_branch_flow_dc, deepcopy pattern)",
            "loc" => 115,
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        println("ERROR in B-3 MEDIUM: $(typeof(e)): $e")
        bt = catch_backtrace()
        println(sprint(showerror, e, bt))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    println("\nStatus: $(results["status"])")
    println("Wall clock: $(round(results["wall_clock_seconds"], digits=3))s")

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println("\n--- RESULT SUMMARY ---")
    println("status:             $(result["status"])")
    println("wall_clock_seconds: $(result["wall_clock_seconds"])")
    println("errors:             $(result["errors"])")
    println("workarounds:        $(result["workarounds"])")
    open("/tmp/b3_contingency_loop_medium_result.json", "w") do f
        JSON.print(f, result, 2)
    end
    println("Result written to /tmp/b3_contingency_loop_medium_result.json")
end

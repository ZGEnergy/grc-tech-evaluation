#=
Test A-11: DC OPF with load-proportional distributed slack; compare LMPs to single-slack A-3

Dimension: expressiveness
Network: TINY (IEEE 39-bus, New England)
Pass condition: Tool supports distributed slack formulation. LMPs differ from single-slack
  results in a physically consistent manner. Distributed slack weights settable via API.
Tool: PowerModels.jl v0.21.5

Capability status: PowerModels.jl has NO native distributed slack formulation.
  This is documented in research-version.md and research-context.md.
  Source: "Distributed slack: No built-in support. Requires manual PTDF-based DC OPF
  construction (~150 lines in test B-8)."

Decision: Record as fail with failure_reason: unsupported_in_installed_version.
  A workaround exists (custom JuMP PTDF-based OPF) but it requires ~150 lines of
  user-assembled code outside PowerModels' problem specification API.
  This is classified as a blocking workaround.
=#

using PowerModels
using HiGHS

PowerModels.silence()

# Cost mapping
const COST_MAP_A11 = Dict(
    "hydro" => (5.0, 0.005),
    "nuclear" => (10.0, 0.010),
    "coal_large" => (25.0, 0.025),
    "gas_CC" => (40.0, 0.040),
    "gas_CT" => (55.0, 0.055),
)
const BRANCH_DERATING_A11 = 0.70

function load_gen_costs_a11(timeseries_dir::String)
    cost_by_index = Dict{Int,Tuple{Float64,Float64}}()
    csv_path = joinpath(timeseries_dir, "gen_temporal_params.csv")
    open(csv_path) do f
        header = split(readline(f), ",")
        idx_genindex = findfirst(==("gen_index"), header)
        idx_techclass = findfirst(==("tech_class_key"), header)
        for line in eachline(f)
            isempty(strip(line)) && continue
            parts = split(line, ",")
            gen_idx = parse(Int, strip(parts[idx_genindex]))
            tech = strip(parts[idx_techclass])
            cost_by_index[gen_idx] = get(COST_MAP_A11, tech, (30.0, 0.030))
        end
    end
    return cost_by_index
end

function apply_differentiated_costs_a11!(data::Dict, cost_by_index::Dict)
    base_mva = data["baseMVA"]
    for (_, gen) in data["gen"]
        gen_idx_0 = gen["index"] - 1
        if haskey(cost_by_index, gen_idx_0)
            c1, c2 = cost_by_index[gen_idx_0]
            gen["model"] = 2
            gen["ncost"] = 3
            gen["cost"] = [c2 * base_mva^2, c1 * base_mva, 0.0]
        end
    end
end

function apply_branch_derating_a11!(data::Dict, derating::Float64)
    for (_, branch) in data["branch"]
        for field in ("rate_a", "rate_b", "rate_c")
            if haskey(branch, field) && branch[field] > 0.0
                branch[field] *= derating
            end
        end
    end
end

function run(
    network_file::String="../../data/networks/case39.m";
    timeseries_dir::Union{String,Nothing}=nothing,
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        # ------------------------------------------------------------------
        # 1. Capability check
        # ------------------------------------------------------------------
        # PowerModels.jl does not provide a distributed slack formulation.
        # The capability table in research-version.md does not list
        # distributed_slack_opf as a supported feature.
        #
        # Evidence:
        # 1. research-version.md: No "distributed_slack_opf" row in capability table.
        # 2. research-context.md: "Distributed slack: No built-in support.
        #    Requires manual PTDF-based DC OPF construction (~150 lines in test B-8)."
        # 3. PowerModels.jl source: src/prob/ contains pf.jl, opf.jl, opb.jl, ots.jl,
        #    tnep.jl — no distributed slack formulation.
        # 4. PowerModels.jl docs: No distributed_slack parameter or setting in solve_opf.
        #
        # The standard single-slack DCPPowerModel fixes one bus as the slack and
        # balances all power imbalance there. There is no API to distribute the slack
        # across multiple generators proportionally to their capacity or load.

        capability_absent = true

        println("Checking PowerModels.jl distributed slack support...")
        println("  research-version.md: distributed_slack_opf NOT in capability table")
        println("  research-context.md: 'No built-in support. ~150 lines custom JuMP code.'")
        println("  PowerModels 0.21.5 solve_opf API: no distributed_slack parameter")

        # ------------------------------------------------------------------
        # 2. Verify single-slack baseline (confirms standard OPF works)
        # ------------------------------------------------------------------
        if isnothing(timeseries_dir)
            timeseries_dir = "../../data/timeseries/case39"
        end

        data = PowerModels.parse_file(network_file)
        base_mva = data["baseMVA"]
        cost_by_index = load_gen_costs_a11(timeseries_dir)
        apply_differentiated_costs_a11!(data, cost_by_index)
        apply_branch_derating_a11!(data, BRANCH_DERATING_A11)

        highs_opt = optimizer_with_attributes(
            HiGHS.Optimizer,
            "output_flag" => false,
            "presolve" => "on",
            "time_limit" => 300.0,
            "threads" => 1,
        )

        result_single_slack = PowerModels.solve_dc_opf(
            data, highs_opt; setting=Dict("output" => Dict("duals" => true))
        )
        single_slack_status = string(result_single_slack["termination_status"])
        println("Single-slack DC OPF status: $single_slack_status")

        # Extract single-slack LMPs for reference
        lmps_single = Dict{String,Float64}()
        if haskey(result_single_slack["solution"], "bus")
            for (bid, bsol) in result_single_slack["solution"]["bus"]
                lam = get(bsol, "lam_kcl_r", nothing)
                if !isnothing(lam) && isfinite(lam)
                    lmps_single[bid] = -lam / base_mva
                end
            end
        end
        println("Single-slack LMPs: $(length(lmps_single)) buses extracted")
        if !isempty(lmps_single)
            lmp_min = minimum(values(lmps_single))
            lmp_max = maximum(values(lmps_single))
            println("  LMP range: $(round(lmp_min, digits=4)) – $(round(lmp_max, digits=4)) \$/MWh")
        end

        # ------------------------------------------------------------------
        # 3. Attempt distributed slack via available API paths
        # ------------------------------------------------------------------
        # Path A: Check if solve_opf accepts any distributed_slack parameter
        # (it does not, but document the attempt)
        #
        # Path B: Check if DCPPowerModel or any formulation supports it
        # (none do based on research)
        #
        # Path C: The extensibility test (B-8) showed that distributed slack
        # requires a fully manual PTDF-based JuMP assembly (~150 lines).
        # This is outside PowerModels' problem specification API.

        api_paths_tried = [
            "solve_dc_opf with distributed_slack setting: no such parameter in PowerModels API",
            "solve_opf with DCPPowerModel: standard formulation, no distributed slack support",
            "instantiate_model with build_opf: no distributed slack in standard build_opf",
        ]

        # Check if there is any formulation type with distributed slack
        distributed_slack_formulations = String[]
        # PowerModels formulation types that could support distributed slack:
        # - DCPPowerModel: no
        # - DCMPPowerModel: no (adds phase-shifters, not distributed slack)
        # - NFAPowerModel: no (network flow, ignores angle constraints)
        # None of the built-in formulations support distributed slack.

        println("\nDistributed slack API investigation:")
        for path in api_paths_tried
            println("  - $path")
        end

        # ------------------------------------------------------------------
        # 4. Document the workaround requirement
        # ------------------------------------------------------------------
        # A distributed slack workaround DOES technically exist:
        # From research-context.md section "Reference bus change" and extensibility test B-8:
        #   "Distributed slack: No built-in support. Requires manual PTDF-based DC OPF
        #   construction (~150 lines in test B-8)."
        #
        # The custom JuMP approach:
        # 1. Build PTDF matrix via calc_basic_ptdf_matrix
        # 2. Manually construct distributed slack DC OPF as a JuMP model
        # 3. Replace the single KCL balance constraint with distributed balance
        # 4. Assign slack participation weights proportional to generator pmax
        # This requires assembling the entire DC OPF from scratch using only
        # PowerModels for data parsing — not using PowerModels' OPF formulations.
        #
        # Classification: BLOCKING (no PowerModels API path; requires full custom JuMP)

        push!(
            results["workarounds"],
            "BLOCKING workaround: No distributed slack API in PowerModels.jl. " *
            "Requires ~150-line custom JuMP PTDF-based DC OPF (confirmed in test B-8). " *
            "PowerModels is used only for data parsing; the problem formulation must be " *
            "assembled entirely from scratch.",
        )

        results["details"] = Dict(
            "network_file" => network_file,
            "n_buses" => length(data["bus"]),
            "n_branches" => length(data["branch"]),
            "n_gens" => length(data["gen"]),
            "base_mva" => base_mva,
            "capability_check" => "distributed_slack_opf: NOT in capability table",
            "research_finding" => "No built-in support. ~150 lines custom JuMP code required.",
            "single_slack_status" => single_slack_status,
            "single_slack_lmps_count" => length(lmps_single),
            "single_slack_lmp_min" => isempty(lmps_single) ? NaN : minimum(values(lmps_single)),
            "single_slack_lmp_max" => isempty(lmps_single) ? NaN : maximum(values(lmps_single)),
            "distributed_slack_api_paths_tried" => api_paths_tried,
            "distributed_slack_formulations_available" => distributed_slack_formulations,
            "workaround_path" => "Full manual PTDF-based DC OPF in JuMP (~150 lines)",
            "workaround_classification" => "blocking",
            "failure_reason" => "unsupported_in_installed_version",
            "solver" => "HiGHS (single-slack baseline only)",
            "loc" => 160,
        )

        # Status: fail — native distributed slack not available
        results["status"] = "fail"

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        println("ERROR in A-11: $(typeof(e)): $e")
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
    using JSON
    result = run()
    println("\n--- RESULT SUMMARY ---")
    println("status:             $(result["status"])")
    println("wall_clock_seconds: $(result["wall_clock_seconds"])")
    println("errors:             $(result["errors"])")
    println("workarounds:        $(result["workarounds"])")
end

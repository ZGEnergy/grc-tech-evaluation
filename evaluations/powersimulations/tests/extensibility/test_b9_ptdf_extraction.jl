#=
Test B-9: PTDF Extraction (compute PTDF, verify against DCPF)

Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: PTDF accessible via API. Flows match DCPF within 1e-6.
  Phase-shifter handling required (corrections or exclusion).
Tool: PowerSimulations.jl v0.30.2 (PowerNetworkMatrices.jl v0.12.1)
=#

using PowerSystems
using PowerFlows
using PowerNetworkMatrices
using JSON
using Logging
using DataFrames
using LinearAlgebra

global_logger(ConsoleLogger(stderr, Logging.Error))

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024
        end
    end
    return nothing
end

function run(
    network_file::String="/workspace/data/networks/case39.m";
    timeseries_dir::Union{String,Nothing}=nothing,
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    try
        sys = System(network_file)
        base_power = get_base_power(sys)

        # ===== 1. Compute PTDF matrix =====
        # Warm-up
        _ = PTDF(sys)

        t0 = time()
        ptdf = PTDF(sys)
        elapsed_ptdf = time() - t0

        results["details"]["ptdf_wall_clock_seconds"] = elapsed_ptdf

        # Get PTDF matrix — ptdf.data is (buses x branches) in PowerNetworkMatrices.jl
        ptdf_matrix = ptdf.data
        n_rows, n_cols = size(ptdf_matrix)

        # axes[1] = bus numbers, axes[2] = branch names
        bus_axes = ptdf.axes[1]
        branch_axes = ptdf.axes[2]

        results["details"]["ptdf_dimensions"] = Dict(
            "rows" => n_rows, "cols" => n_cols, "interpretation" => "rows=buses, cols=branches"
        )
        results["details"]["ptdf_branch_count"] = length(branch_axes)
        results["details"]["ptdf_bus_count"] = length(bus_axes)

        # PTDF matrix statistics
        results["details"]["ptdf_stats"] = Dict(
            "min" => round(minimum(ptdf_matrix); digits=6),
            "max" => round(maximum(ptdf_matrix); digits=6),
            "mean_abs" => round(mean(abs.(ptdf_matrix)); digits=6),
            "nnz_fraction" =>
                round(count(x -> abs(x) > 1e-10, ptdf_matrix) / length(ptdf_matrix); digits=4),
        )

        # ===== 2. Run DCPF for reference flows =====
        # Warm-up
        _ = solve_powerflow(DCPowerFlow(), sys)

        t0_pf = time()
        pf_result = solve_powerflow(DCPowerFlow(), sys)
        elapsed_pf = time() - t0_pf

        result_key = first(keys(pf_result))
        inner = pf_result[result_key]
        bus_df = inner["bus_results"]
        flow_df = inner["flow_results"]

        results["details"]["dcpf_wall_clock_seconds"] = elapsed_pf

        # ===== 3. Extract injection vector =====
        # Build Pinj vector matching PTDF bus ordering
        # Pinj = P_gen - P_load for each bus (in per-unit)
        bus_pinj = Dict{Int,Float64}()
        for row in eachrow(bus_df)
            bus_pinj[row.bus_number] = row.P_net  # net injection in p.u.
        end

        # Build Pinj vector in PTDF bus axis order
        pinj = Float64[]
        for bus_num in bus_axes
            push!(pinj, get(bus_pinj, bus_num, 0.0))
        end

        # ===== 4. Compute PTDF-predicted flows =====
        # ptdf_matrix is (buses x branches), so flow = ptdf_matrix' * Pinj
        # gives a vector of branch flows
        predicted_flows_pu = ptdf_matrix' * pinj

        # ===== 5. Compare with DCPF flows =====
        # Build a map of DCPF flows by branch name
        dcpf_flows = Dict{String,Float64}()
        for row in eachrow(flow_df)
            dcpf_flows[row.line_name] = row.P_from_to  # in per-unit
        end

        # Check for phase shifters (nonzero SHIFT in branch data)
        has_phase_shifters = false
        for pst in get_components(PhaseShiftingTransformer, sys)
            has_phase_shifters = true
            break
        end
        results["details"]["has_phase_shifters"] = has_phase_shifters

        # Compare flows
        max_error = 0.0
        mean_error = 0.0
        n_compared = 0
        flow_comparison = Dict{String,Any}[]

        for (i, branch_name) in enumerate(branch_axes)
            if haskey(dcpf_flows, branch_name)
                ptdf_flow = predicted_flows_pu[i]
                dcpf_flow = dcpf_flows[branch_name]
                err = abs(ptdf_flow - dcpf_flow)
                max_error = max(max_error, err)
                mean_error += err
                n_compared += 1

                push!(
                    flow_comparison,
                    Dict(
                        "branch" => branch_name,
                        "ptdf_flow_pu" => round(ptdf_flow; digits=8),
                        "dcpf_flow_pu" => round(dcpf_flow; digits=8),
                        "error_pu" => round(err; digits=10),
                        "error_mw" => round(err * base_power; digits=6),
                    ),
                )
            end
        end

        if n_compared > 0
            mean_error /= n_compared
        end

        results["details"]["flow_comparison_count"] = n_compared
        results["details"]["max_error_pu"] = max_error
        results["details"]["max_error_mw"] = max_error * base_power
        results["details"]["mean_error_pu"] = mean_error
        results["details"]["mean_error_mw"] = mean_error * base_power

        # Show top 5 worst and best matches
        sort!(flow_comparison; by=x -> -x["error_pu"])
        results["details"]["worst_5_matches"] = flow_comparison[1:min(5, length(flow_comparison))]
        results["details"]["best_5_matches"] = flow_comparison[max(1, end - 4):end]

        # ===== 6. Also extract LODF as bonus =====
        t0_lodf = time()
        lodf = LODF(sys)
        elapsed_lodf = time() - t0_lodf

        lodf_matrix = lodf.data
        results["details"]["lodf_wall_clock_seconds"] = elapsed_lodf
        results["details"]["lodf_dimensions"] = Dict(
            "rows" => size(lodf_matrix, 1), "cols" => size(lodf_matrix, 2)
        )

        # ===== 7. API LOC count =====
        # PTDF extraction: 1 line (ptdf = PTDF(sys))
        # Flow prediction: 1 line (flows = get_data(ptdf) * pinj)
        # Total: 2 LOC for PTDF extraction + prediction
        results["details"]["ptdf_extraction_loc"] = 1
        results["details"]["flow_prediction_loc"] = 1

        results["wall_clock_seconds"] = elapsed_ptdf + elapsed_pf
        results["details"]["peak_memory_mb"] = peak_rss_mb()

        # ===== Pass condition =====
        tolerance = 1e-6
        flows_match = max_error < tolerance
        ptdf_accessible = length(branch_axes) > 0 && length(bus_axes) > 0
        dimensions_correct =
            length(branch_axes) == nrow(flow_df) && length(bus_axes) == nrow(bus_df)

        results["details"]["pass_checks"] = Dict(
            "ptdf_accessible" => ptdf_accessible,
            "dimensions_correct" => dimensions_correct,
            "flows_match_1e6" => flows_match,
            "max_error_pu" => max_error,
            "tolerance" => tolerance,
            "phase_shifters_handled" => !has_phase_shifters || flows_match,
        )

        if ptdf_accessible && flows_match
            results["status"] = "pass"
        else
            push!(results["errors"], "Max error $(max_error) exceeds tolerance $(tolerance)")
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    end

    return results
end

using Statistics: mean

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

#=
Test B-9: PTDF Matrix Extraction and Validation Against DCPF Flows

Dimension: extensibility
Network: TINY (IEEE 39-bus, New England)
Pass condition: PTDF matrix accessible via native API, internal matrix extraction,
  or unit-injection computation. Flow predictions match DCPF results within 1e-6.
  If phase-shifting transformers present (nonzero SHIFT), apply Pbusinj/Pfinj
  correction or exclude those branches.
Tool: PowerModels.jl v0.21.5
depends_on: A-1
=#

using PowerModels
using LinearAlgebra

PowerModels.silence()

function run(
    network_file::String=joinpath(@__DIR__, "..", "..", "..", "..", "data", "networks", "case39.m");
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
        data = PowerModels.parse_file(network_file)
        base_mva = data["baseMVA"]
        n_buses = length(data["bus"])
        n_branches = length(data["branch"])

        # --- Phase-shifter check ---
        has_phase_shifters = false
        n_phase_shifters = 0
        for (_, br) in data["branch"]
            shift = get(br, "shift", 0.0)
            if abs(shift) > 1e-8
                has_phase_shifters = true
                n_phase_shifters += 1
            end
        end
        println(
            "Phase-shifting transformers: $n_phase_shifters (has_phase_shifters=$has_phase_shifters)",
        )

        # --- Compute PTDF matrix ---
        basic_data = PowerModels.make_basic_network(deepcopy(data))
        nb = length(basic_data["bus"])
        nbr = length(basic_data["branch"])

        ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data)
        ptdf_rows, ptdf_cols = size(ptdf)

        println("PTDF dimensions: $ptdf_rows x $ptdf_cols (expected: $nbr x $nb)")

        # --- Validate single-row API ---
        ptdf_row1 = PowerModels.calc_basic_ptdf_row(basic_data, 1)
        row1_diff = maximum(abs.(ptdf[1, :] .- ptdf_row1))
        println("Single-row API match: max diff = $row1_diff")

        # --- Solve DCPF to get reference flows ---
        basic_data_pf = PowerModels.make_basic_network(deepcopy(data))
        pf_result = PowerModels.compute_dc_pf(basic_data_pf)
        # update_data! merges the solution (bus angles) back into the data dict
        PowerModels.update_data!(basic_data_pf, pf_result["solution"])
        # calc_branch_flow_dc returns a dict with branch flows (not in-place)
        flow_dict = PowerModels.calc_branch_flow_dc(basic_data_pf)

        # Extract actual flows
        branch_ids = sort(parse.(Int, collect(keys(basic_data_pf["branch"]))))
        flow_actual = zeros(nbr)
        for (l, br_id) in enumerate(branch_ids)
            br_flow = flow_dict["branch"][string(br_id)]
            flow_actual[l] = get(br_flow, "pf", 0.0)
        end

        # --- Compute net bus injections ---
        bus_ids = sort(parse.(Int, collect(keys(basic_data_pf["bus"]))))
        p_inj = zeros(nb)

        for (_, gen) in basic_data_pf["gen"]
            if gen["gen_status"] == 1
                bus = gen["gen_bus"]
                idx = findfirst(==(bus), bus_ids)
                if idx !== nothing
                    p_inj[idx] += get(gen, "pg", 0.0)
                end
            end
        end
        for (_, load) in basic_data_pf["load"]
            if load["status"] == 1
                bus = load["load_bus"]
                idx = findfirst(==(bus), bus_ids)
                if idx !== nothing
                    p_inj[idx] -= get(load, "pd", 0.0)
                end
            end
        end

        # --- Predict flows via PTDF ---
        flow_predicted = ptdf * p_inj

        # --- Compare ---
        flow_diff = abs.(flow_predicted .- flow_actual)
        max_diff = maximum(flow_diff)
        mean_diff = sum(flow_diff) / length(flow_diff)
        rms_diff = sqrt(sum(flow_diff .^ 2) / length(flow_diff))

        tolerance = 1e-6
        flows_match = max_diff < tolerance

        println("\nFlow comparison:")
        println("  Max error: $max_diff pu")
        println("  Mean error: $mean_diff pu")
        println("  RMS error: $rms_diff pu")
        println("  Tolerance: $tolerance")
        println("  Match: $flows_match")

        # --- PTDF matrix properties ---
        ptdf_max = maximum(ptdf)
        ptdf_min = minimum(ptdf)
        ptdf_rank = rank(ptdf)

        # Find reference bus (column with all zeros)
        ref_bus_idx = nothing
        for j in 1:nb
            if maximum(abs.(ptdf[:, j])) < 1e-10
                ref_bus_idx = j
                break
            end
        end
        ref_bus = ref_bus_idx !== nothing ? bus_ids[ref_bus_idx] : nothing

        println("\nPTDF properties:")
        println("  Max value: $ptdf_max")
        println("  Min value: $ptdf_min")
        println("  Rank: $ptdf_rank (expected: $(nb - 1))")
        println("  Reference bus: $ref_bus (idx $ref_bus_idx)")

        # Sample flow comparisons
        println("\nSample flow comparisons (first 5 branches, pu):")
        for l in 1:min(5, nbr)
            br_id = branch_ids[l]
            println(
                "  Branch $br_id: predicted=$(round(flow_predicted[l], digits=8)), actual=$(round(flow_actual[l], digits=8)), diff=$(round(flow_diff[l], sigdigits=3))",
            )
        end

        # --- Pass condition ---
        dims_correct = ptdf_rows == nbr && ptdf_cols == nb
        rank_correct = ptdf_rank == nb - 1
        row_api_match = row1_diff < 1e-12

        if flows_match && dims_correct
            results["status"] = "pass"
        else
            push!(results["errors"], "Flow match=$flows_match, dims_correct=$dims_correct")
        end

        results["details"] = Dict(
            "ptdf_dimensions" => "$ptdf_rows x $ptdf_cols",
            "expected_dimensions" => "$nbr x $nb",
            "dimensions_correct" => dims_correct,
            "max_flow_error_pu" => max_diff,
            "mean_flow_error_pu" => mean_diff,
            "rms_flow_error_pu" => rms_diff,
            "tolerance" => tolerance,
            "flows_match" => flows_match,
            "has_phase_shifters" => has_phase_shifters,
            "n_phase_shifters" => n_phase_shifters,
            "phase_correction_applied" => false,
            "ptdf_max" => ptdf_max,
            "ptdf_min" => ptdf_min,
            "ptdf_rank" => ptdf_rank,
            "expected_rank" => nb - 1,
            "rank_correct" => rank_correct,
            "reference_bus" => ref_bus,
            "ref_bus_ptdf_col_max" =>
                ref_bus_idx !== nothing ? maximum(abs.(ptdf[:, ref_bus_idx])) : NaN,
            "single_row_api_match" => row_api_match,
            "single_row_max_diff" => row1_diff,
            "api_method" => "calc_basic_ptdf_matrix (native, documented public API)",
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
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
    println("\n--- RESULT ---")
    println("status: $(result["status"])")
    println("wall_clock_seconds: $(result["wall_clock_seconds"])")
    println("errors: $(result["errors"])")
    for (k, v) in result["details"]
        println("  $k: $v")
    end
end

#=
Test B-9: PTDF Matrix Extraction and Validation
Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: PTDF accessible via native API, internal matrix extraction, or
    unit-injection. Flow predictions match DCPF results within 1e-6.
Tool: PowerModels.jl v0.21.5
Solver: N/A (direct solve via compute_dc_pf)
Depends on: A-1 (DCPF)
=#

using PowerModels, JSON
using LinearAlgebra

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

    t0 = time()
    try
        # ---- Step 1: Solve DCPF (same as A-1) ----
        data = PowerModels.parse_file(network_file)

        pf_result = PowerModels.compute_dc_pf(data)
        if !pf_result["termination_status"]
            push!(results["errors"], "DCPF did not converge")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        pf_sol = pf_result["solution"]
        PowerModels.update_data!(data, pf_sol)
        branch_flows_dict = PowerModels.calc_branch_flow_dc(data)

        # ---- Step 2: Compute PTDF matrix via native API ----
        basic_data = PowerModels.make_basic_network(deepcopy(data))
        ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data)

        nbr, nb = size(ptdf)
        results["details"]["ptdf_rows"] = nbr
        results["details"]["ptdf_cols"] = nb
        results["details"]["expected_rows"] = length(data["branch"])
        results["details"]["expected_cols"] = length(data["bus"])
        results["details"]["dimensions_correct"] =
            (nbr == length(data["branch"])) && (nb == length(data["bus"]))
        results["details"]["ptdf_api"] = "PowerModels.calc_basic_ptdf_matrix(make_basic_network(data))"
        results["details"]["native_api"] = true

        # ---- Step 3: Understand bus/branch ordering in basic network ----
        # make_basic_network renumbers buses to contiguous 1:N
        basic_bus_ids = sort(parse.(Int, collect(keys(basic_data["bus"]))))
        basic_branch_ids = sort(parse.(Int, collect(keys(basic_data["branch"]))))

        results["details"]["basic_bus_ids_range"] = [minimum(basic_bus_ids), maximum(basic_bus_ids)]
        results["details"]["basic_branch_ids_range"] = [
            minimum(basic_branch_ids), maximum(basic_branch_ids)
        ]

        # Map from original bus IDs to basic bus IDs
        # In basic network, buses are renumbered starting from 1
        # Check if basic network has a mapping
        orig_bus_ids = sort(parse.(Int, collect(keys(data["bus"]))))
        results["details"]["original_bus_ids_range"] = [
            minimum(orig_bus_ids), maximum(orig_bus_ids)
        ]

        # Build bus index mapping for basic network
        bus_to_idx = Dict(id => i for (i, id) in enumerate(basic_bus_ids))

        # ---- Step 4: Compute net bus injections (P_inj = gen - load) ----
        # Use basic_data which has contiguous numbering
        p_inj = zeros(nb)
        for (_, gen) in basic_data["gen"]
            bus = gen["gen_bus"]
            if haskey(bus_to_idx, bus)
                p_inj[bus_to_idx[bus]] += gen["pg"]
            end
        end
        for (_, load) in basic_data["load"]
            bus = load["load_bus"]
            if haskey(bus_to_idx, bus)
                p_inj[bus_to_idx[bus]] -= load["pd"]
            end
        end

        results["details"]["total_net_injection"] = round(sum(p_inj); digits=6)

        # ---- Step 5: Predict flows using PTDF ----
        # flow_predicted = PTDF * P_inj
        flow_predicted = ptdf * p_inj

        # ---- Step 6: Extract actual DCPF flows from basic_data ----
        # After update_data!, basic_data should have the solved flows
        # But we need to ensure basic_data has the solved values
        # Re-solve on basic_data to be precise
        basic_data_fresh = PowerModels.make_basic_network(PowerModels.parse_file(network_file))
        pf_basic = PowerModels.compute_dc_pf(basic_data_fresh)
        PowerModels.update_data!(basic_data_fresh, pf_basic["solution"])
        basic_flows = PowerModels.calc_branch_flow_dc(basic_data_fresh)

        # Extract actual flows in basic branch ordering
        flow_actual = zeros(nbr)
        for (l, br_id) in enumerate(basic_branch_ids)
            br = basic_flows["branch"][string(br_id)]
            flow_actual[l] = br["pf"]
        end

        # ---- Step 7: Compare predicted vs actual ----
        flow_diff = abs.(flow_predicted .- flow_actual)
        max_diff = maximum(flow_diff)
        mean_diff = sum(flow_diff) / nbr
        rms_diff = sqrt(sum(flow_diff .^ 2) / nbr)

        results["details"]["max_flow_diff"] = max_diff
        results["details"]["mean_flow_diff"] = mean_diff
        results["details"]["rms_flow_diff"] = rms_diff
        results["details"]["tolerance"] = 1e-6
        results["details"]["flows_match"] = max_diff < 1e-6

        # Sample comparisons
        sample_comparisons = Dict{String,Dict{String,Float64}}()
        for l in 1:min(5, nbr)
            sample_comparisons[string(basic_branch_ids[l])] = Dict(
                "predicted" => round(flow_predicted[l]; digits=8),
                "actual" => round(flow_actual[l]; digits=8),
                "diff" => round(flow_diff[l]; digits=10),
            )
        end
        results["details"]["sample_comparisons"] = sample_comparisons

        # ---- Step 8: Additional PTDF properties ----
        # PTDF row sum should be 0 for each branch (columns sum to 0 relative to ref bus)
        # Actually, PTDF columns at reference bus should be all zeros
        ref_bus = nothing
        for (id, bus) in basic_data_fresh["bus"]
            if bus["bus_type"] == 3
                ref_bus = parse(Int, id)
                break
            end
        end
        if ref_bus !== nothing && haskey(bus_to_idx, ref_bus)
            ref_col = bus_to_idx[ref_bus]
            ref_col_max = maximum(abs.(ptdf[:, ref_col]))
            results["details"]["ref_bus"] = ref_bus
            results["details"]["ref_bus_col_index"] = ref_col
            results["details"]["ref_bus_ptdf_col_max"] = ref_col_max
            results["details"]["ref_bus_col_zeros"] = ref_col_max < 1e-10
        end

        # PTDF matrix rank
        ptdf_rank = rank(ptdf)
        results["details"]["ptdf_rank"] = ptdf_rank
        results["details"]["expected_rank"] = nb - 1  # buses minus ref bus

        # Max/min PTDF values
        results["details"]["ptdf_max"] = maximum(ptdf)
        results["details"]["ptdf_min"] = minimum(ptdf)

        # Also verify single-row API
        ptdf_row1 = PowerModels.calc_basic_ptdf_row(basic_data_fresh, 1)
        row1_match = maximum(abs.(ptdf_row1 .- ptdf[1, :])) < 1e-10
        results["details"]["single_row_api_available"] = true
        results["details"]["single_row_matches_full_matrix"] = row1_match

        # ---- Pass condition ----
        if max_diff < 1e-6
            results["status"] = "pass"
        else
            push!(
                results["errors"],
                "Flow predictions do not match within tolerance. " *
                "Max diff: $max_diff (tolerance: 1e-6)",
            )
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        push!(results["errors"], sprint(showerror, e, catch_backtrace()))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

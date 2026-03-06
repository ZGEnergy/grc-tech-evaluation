
#= Test B-9: PTDF Extraction — compute and verify PTDF matrix =#

using PowerModels, JSON, LinearAlgebra, SparseArrays
PowerModels.silence()

function run_test(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        data = PowerModels.parse_file(network_file)
        basic_data = PowerModels.make_basic_network(data)

        # Extract PTDF matrix
        ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data)
        ptdf_size = size(ptdf)
        n_branches = length(basic_data["branch"])
        n_buses = length(basic_data["bus"])

        # Verify dimensions
        @assert ptdf_size == (n_branches, n_buses) "PTDF size $(ptdf_size) != expected ($n_branches, $n_buses)"

        # Compute DCPF to get bus angles
        theta = PowerModels.compute_basic_dc_pf(basic_data)

        # Compute branch flows from angles using branch susceptance matrix
        B_branch = PowerModels.calc_basic_branch_susceptance_matrix(basic_data)
        dcpf_flows = Vector(B_branch * theta)

        # Compute flows from PTDF * injections
        injections = real(PowerModels.calc_basic_bus_injection(basic_data))
        ptdf_flows = Vector(ptdf * injections)

        # Note: compute_basic_dc_pf solves theta = -B_inv * injections,
        # so B_branch * theta = -(PTDF * injections). The sign convention
        # means dcpf_flows = -ptdf_flows. We verify this relationship.
        flow_diffs = abs.(ptdf_flows .+ dcpf_flows)  # should be ~0 if ptdf = -dcpf
        max_diff = maximum(flow_diffs)
        mean_diff = sum(flow_diffs) / length(flow_diffs)

        # Verify ref bus column is zero (PTDF property)
        ref_bus = PowerModels.reference_bus(basic_data)
        ref_col = ptdf[:, ref_bus["index"]]
        max_ref_col = maximum(abs.(ref_col))

        results["details"] = Dict(
            "ptdf_dimensions" => [ptdf_size[1], ptdf_size[2]],
            "expected_dimensions" => [n_branches, n_buses],
            "dimensions_correct" => ptdf_size == (n_branches, n_buses),
            "max_flow_diff_ptdf_vs_dcpf" => max_diff,
            "mean_flow_diff" => mean_diff,
            "flow_match_within_1e6" => max_diff < 1e-6,
            "ref_bus_index" => ref_bus["index"],
            "max_ref_bus_column_value" => max_ref_col,
            "ref_column_is_zero" => max_ref_col < 1e-10,
            "sample_ptdf_values" => Dict(
                "row1_col1" => round(ptdf[1, 1]; digits=6),
                "row1_col2" => round(ptdf[1, 2]; digits=6),
                "row1_coln" => round(ptdf[1, end]; digits=6),
            ),
            "sample_flows_dcpf" => round.(dcpf_flows[1:min(5, length(dcpf_flows))]; digits=6),
            "sample_flows_ptdf" => round.(ptdf_flows[1:min(5, length(ptdf_flows))]; digits=6),
            "sign_convention" => "compute_basic_dc_pf uses theta=-B_inv*inj, so B_branch*theta = -(PTDF*inj); verified ptdf_flows = -dcpf_flows",
            "approach" => "make_basic_network + calc_basic_ptdf_matrix (native API)",
            "api_call" => "PowerModels.calc_basic_ptdf_matrix(basic_data)",
        )

        # Pass criteria: dimensions correct AND flow match within 1e-6
        if ptdf_size == (n_branches, n_buses) && max_diff < 1e-6
            results["status"] = "pass"
        else
            push!(results["errors"], "Flow mismatch: max_diff=$(max_diff)")
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
    finally
        results["wall_clock_seconds"] = time() - t0
    end
    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run_test()
    println(JSON.json(result, 2))
end

#= Test C-9: PTDF matrix at MEDIUM (10000 buses)
   Dense matrix: 12706 branches x 10000 buses. May be slow/memory-intensive.
=#
using PowerModels, JSON, LinearAlgebra
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
        "test_id" => "C-9",
        "test_name" => "ptdf_scale",
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

        # Make basic network
        t_basic = time()
        basic_data = PowerModels.make_basic_network(data)
        basic_time = time() - t_basic
        results["details"]["make_basic_network_seconds"] = round(basic_time; digits=4)

        n_branches = length(basic_data["branch"])
        n_buses = length(basic_data["bus"])
        results["details"]["basic_branches"] = n_branches
        results["details"]["basic_buses"] = n_buses

        # Estimate memory for dense PTDF matrix
        estimated_memory_mb = n_branches * n_buses * 8 / 1024^2  # Float64 = 8 bytes
        results["details"]["estimated_dense_matrix_mb"] = round(estimated_memory_mb; digits=2)

        # Compute PTDF matrix
        GC.gc()
        mem_before = Base.gc_live_bytes() / 1024^2

        t_ptdf = time()
        ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data)
        ptdf_time = time() - t_ptdf

        GC.gc()
        mem_after = Base.gc_live_bytes() / 1024^2
        peak_memory = mem_after - mem_before

        results["details"]["ptdf_compute_seconds"] = round(ptdf_time; digits=4)
        results["details"]["peak_memory_mb"] = round(peak_memory; digits=2)
        results["details"]["ptdf_dimensions"] = [size(ptdf, 1), size(ptdf, 2)]
        results["details"]["actual_matrix_mb"] = round(sizeof(ptdf) / 1024^2; digits=2)

        # Matrix density analysis
        n_nonzero = count(!iszero, ptdf)
        total_elements = length(ptdf)
        density = n_nonzero / total_elements
        results["details"]["matrix_density"] = round(density; digits=6)
        results["details"]["nonzero_elements"] = n_nonzero
        results["details"]["total_elements"] = total_elements

        # Verify ref bus column is zero
        ref_bus = PowerModels.reference_bus(basic_data)
        ref_col = ptdf[:, ref_bus["index"]]
        max_ref_col = maximum(abs.(ref_col))
        results["details"]["ref_bus_column_max"] = max_ref_col
        results["details"]["ref_column_is_zero"] = max_ref_col < 1e-10

        # Verify PTDF against DCPF
        injections = real(PowerModels.calc_basic_bus_injection(basic_data))
        ptdf_flows = Vector(ptdf * injections)
        theta = PowerModels.compute_basic_dc_pf(basic_data)
        B_branch = PowerModels.calc_basic_branch_susceptance_matrix(basic_data)
        dcpf_flows = Vector(B_branch * theta)

        flow_diffs = abs.(ptdf_flows .+ dcpf_flows)
        max_diff = maximum(flow_diffs)
        results["details"]["ptdf_vs_dcpf_max_diff"] = max_diff
        results["details"]["ptdf_verified"] = max_diff < 1e-4

        results["details"]["method"] = "calc_basic_ptdf_matrix(make_basic_network(data))"
        results["status"] = "pass"

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

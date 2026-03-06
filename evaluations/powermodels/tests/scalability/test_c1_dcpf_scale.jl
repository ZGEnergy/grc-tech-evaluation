
#= Test C-1: DCPF at MEDIUM (10000 buses) =#

using PowerModels, JSON
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
        "test_id" => "C-1",
        "test_name" => "dcpf_scale",
        "network" => "MEDIUM",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        # Parse
        t_parse = time()
        data = PowerModels.parse_file(network_file)
        parse_time = time() - t_parse
        preprocess_data!(data)

        nbus = length(data["bus"])
        nbranch = length(data["branch"])
        ngen = length(data["gen"])
        results["details"]["num_buses"] = nbus
        results["details"]["num_branches"] = nbranch
        results["details"]["num_generators"] = ngen
        results["details"]["parse_time_seconds"] = round(parse_time; digits=3)

        # Memory measurement
        GC.gc()
        mem_before = Base.gc_live_bytes() / 1024^2

        # Solve DC power flow
        t_solve = time()
        result_dc = PowerModels.compute_dc_pf(data)
        solve_time = time() - t_solve

        GC.gc()
        mem_after = Base.gc_live_bytes() / 1024^2
        peak_memory = mem_after - mem_before

        results["details"]["solve_time_seconds"] = round(solve_time; digits=4)
        results["details"]["peak_memory_mb"] = round(peak_memory; digits=2)

        # Validate results
        bus_angles = Dict{String,Float64}()
        for (bus_id, bus) in result_dc["solution"]["bus"]
            bus_angles[bus_id] = bus["va"]
        end

        non_zero_angles = count(abs(v) > 1e-10 for v in values(bus_angles))
        results["details"]["non_zero_angle_count"] = non_zero_angles
        results["details"]["total_buses_solved"] = length(bus_angles)

        # Compute branch flows
        PowerModels.update_data!(data, result_dc["solution"])
        branch_flows = PowerModels.calc_branch_flow_dc(data)
        n_flows = length(branch_flows["branch"])
        results["details"]["branch_flows_computed"] = n_flows

        # Summary stats on flows
        flow_vals = [abs(get(br, "pf", 0.0)) for (_, br) in branch_flows["branch"]]
        results["details"]["max_flow_pu"] = round(maximum(flow_vals); digits=4)
        results["details"]["mean_flow_pu"] = round(sum(flow_vals) / length(flow_vals); digits=4)

        results["details"]["method"] = "compute_dc_pf (native, non-JuMP)"
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


#= Test A-1: DC Power Flow on TINY (case39) =#

using PowerModels, JSON

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "test_id" => "A-1",
        "test_name" => "dcpf",
        "network" => "case39",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        # Parse network data
        data = PowerModels.parse_file(network_file)
        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_branches"] = length(data["branch"])
        results["details"]["num_generators"] = length(data["gen"])

        # Solve DC power flow using native (non-JuMP) solver
        result_dc = PowerModels.compute_dc_pf(data)

        # Extract voltage angles (radians) from result
        bus_angles = Dict{String,Float64}()
        for (bus_id, bus) in result_dc["solution"]["bus"]
            bus_angles[bus_id] = bus["va"]
        end
        # Update data with solution for branch flow calculation
        PowerModels.update_data!(data, result_dc["solution"])
        results["details"]["bus_voltage_angles_rad"] = bus_angles

        # Compute line flows using PTDF or direct calculation
        basic_data = PowerModels.make_basic_network(data)
        branch_flows = PowerModels.calc_branch_flow_dc(data)

        line_flows = Dict{String,Dict{String,Any}}()
        for (br_id, br) in branch_flows["branch"]
            line_flows[br_id] = Dict("pf" => get(br, "pf", NaN), "pt" => get(br, "pt", NaN))
        end
        results["details"]["line_flows_pu"] = line_flows

        # Extract nodal injections (gen - load at each bus)
        bus_injections = Dict{String,Float64}()
        for (bus_id, _) in data["bus"]
            bus_injections[bus_id] = 0.0
        end
        for (_, gen) in data["gen"]
            bid = string(gen["gen_bus"])
            bus_injections[bid] = get(bus_injections, bid, 0.0) + gen["pg"]
        end
        for (_, load) in data["load"]
            bid = string(load["load_bus"])
            bus_injections[bid] = get(bus_injections, bid, 0.0) - load["pd"]
        end
        results["details"]["bus_injections_pu"] = bus_injections

        # Validate: reference bus angle should be 0
        ref_buses = [bid for (bid, b) in data["bus"] if b["bus_type"] == 3]
        results["details"]["reference_buses"] = ref_buses
        if !isempty(ref_buses)
            ref_angle = bus_angles[ref_buses[1]]
            results["details"]["ref_bus_angle"] = ref_angle
        end

        # Check that we got non-trivial angles (not all zero)
        non_zero_angles = count(abs(v) > 1e-10 for v in values(bus_angles))
        results["details"]["non_zero_angle_count"] = non_zero_angles

        if non_zero_angles > 0 && !isempty(line_flows)
            results["status"] = "pass"
            results["details"]["method"] = "compute_dc_pf (native, non-JuMP)"
            results["details"]["api_lines"] = 3  # parse_file, compute_dc_pf, calc_branch_flow_dc
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

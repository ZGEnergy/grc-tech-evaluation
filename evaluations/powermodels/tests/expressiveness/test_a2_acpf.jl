#=
Test A-2: Solve ACPF (Newton-Raphson) on TINY (IEEE 39-bus)
Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Converges. Bus voltage magnitudes/angles, line P/Q flows, losses accessible.
Tool: PowerModels.jl v0.21.5
Solver: NLsolve-based native solver (compute_ac_pf)
=#

using PowerModels, JSON

function is_converged(term_status)
    if term_status isa Bool
        return term_status
    end
    s = string(term_status)
    return s in ("LOCALLY_SOLVED", "OPTIMAL", "ALMOST_LOCALLY_SOLVED", "true")
end

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

    # Warm-up run
    try
        _data = PowerModels.parse_file(network_file)
        PowerModels.compute_ac_pf(_data)
    catch
        ;
    end

    t0 = time()
    try
        # Parse network
        data = PowerModels.parse_file(network_file)

        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_branches"] = length(data["branch"])
        results["details"]["num_generators"] = length(data["gen"])

        # Step 1: Try flat start (default) with compute_ac_pf (NLsolve Newton)
        pf_result = PowerModels.compute_ac_pf(data)
        term_status = pf_result["termination_status"]
        results["details"]["termination_status_flat_start"] = string(term_status)
        converged = is_converged(term_status)

        # If flat start fails, try DC warm start
        if !converged
            push!(results["workarounds"], "Flat start failed ($term_status), trying DC warm start")

            data2 = PowerModels.parse_file(network_file)
            dc_result = PowerModels.compute_dc_pf(data2)
            if is_converged(dc_result["termination_status"])
                PowerModels.update_data!(data2, dc_result["solution"])
                # Set warm-start values from DC solution
                for (id, bus) in data2["bus"]
                    bus["vm"] = 1.0  # keep flat voltage magnitude
                    # va already updated from DC solution
                end
                pf_result = PowerModels.compute_ac_pf(data2)
                term_status = pf_result["termination_status"]
                results["details"]["termination_status_dc_warmstart"] = string(term_status)
                converged = is_converged(term_status)
            end
        end

        results["details"]["final_termination_status"] = string(term_status)

        if !converged
            push!(results["errors"], "ACPF did not converge after all attempts: $term_status")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        sol = pf_result["solution"]

        # Extract bus voltage magnitudes and angles
        bus_vm = Dict{String,Float64}()
        bus_va = Dict{String,Float64}()
        for (id, bus) in sol["bus"]
            bus_vm[id] = bus["vm"]
            bus_va[id] = bus["va"]
        end
        results["details"]["bus_vm_sample"] = Dict(
            k => v for (k, v) in Iterators.take(sort(collect(bus_vm); by=x->parse(Int, x[1])), 5)
        )
        results["details"]["bus_va_sample"] = Dict(
            k => v for (k, v) in Iterators.take(sort(collect(bus_va); by=x->parse(Int, x[1])), 5)
        )

        # Compute branch flows
        data_solved = PowerModels.parse_file(network_file)
        PowerModels.update_data!(data_solved, sol)
        branch_flows = PowerModels.calc_branch_flow_ac(data_solved)

        # Extract P/Q flows and compute losses
        line_pq = Dict{String,Dict{String,Float64}}()
        total_p_loss = 0.0
        total_q_loss = 0.0
        for (id, br) in branch_flows["branch"]
            pf = br["pf"]
            pt = br["pt"]
            qf = br["qf"]
            qt = br["qt"]
            p_loss = pf + pt
            q_loss = qf + qt
            total_p_loss += p_loss
            total_q_loss += q_loss
            line_pq[id] = Dict(
                "pf" => pf,
                "pt" => pt,
                "qf" => qf,
                "qt" => qt,
                "p_loss" => round(p_loss; digits=6),
                "q_loss" => round(q_loss; digits=6),
            )
        end
        results["details"]["line_pq_sample"] = Dict(
            k => v for (k, v) in Iterators.take(sort(collect(line_pq); by=x->parse(Int, x[1])), 5)
        )
        results["details"]["total_p_loss_pu"] = round(total_p_loss; digits=6)
        results["details"]["total_q_loss_pu"] = round(total_q_loss; digits=6)

        # Vm range
        vm_vals = collect(values(bus_vm))
        results["details"]["vm_min"] = minimum(vm_vals)
        results["details"]["vm_max"] = maximum(vm_vals)

        results["details"]["num_buses_solved"] = length(bus_vm)
        results["details"]["num_branches_solved"] = length(line_pq)

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

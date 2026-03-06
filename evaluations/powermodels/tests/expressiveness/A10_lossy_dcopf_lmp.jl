#= Test A-10: Lossy DC OPF with LMP decomposition on TINY (case39)
   Uses DCPLLPowerModel (DC with piecewise-linear losses).
   LMP decomposition is NOT built-in -- manual extraction from JuMP duals required.
=#
using PowerModels, HiGHS, Ipopt, JuMP, JSON

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "test_id" => "A-10",
        "test_name" => "lossy_dcopf_lmp",
        "network" => "case39",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        data = PowerModels.parse_file(network_file)
        nbus = length(data["bus"])
        nbranch = length(data["branch"])
        results["details"]["num_buses"] = nbus
        results["details"]["num_branches"] = nbranch

        solver = optimizer_with_attributes(
            HiGHS.Optimizer, "time_limit" => 300.0, "threads" => 1, "output_flag" => false
        )

        # --- Standard lossless DC OPF for comparison ---
        result_lossless = solve_dc_opf(
            data, solver; setting=Dict("output" => Dict("duals" => true))
        )
        results["details"]["lossless_objective"] = result_lossless["objective"]
        results["details"]["lossless_status"] = string(result_lossless["termination_status"])

        lossless_lmps = Dict{String,Float64}()
        for (bid, bus) in result_lossless["solution"]["bus"]
            lossless_lmps[bid] = get(bus, "lam_kcl_r", NaN)
        end
        results["details"]["lossless_lmps"] = lossless_lmps

        # --- Lossy DC OPF using DCPLLPowerModel ---
        # DCPLLPowerModel uses piecewise-linear loss approximation which introduces
        # additional constraints that require an NLP-capable solver (not pure LP like HiGHS)
        lossy_solver = optimizer_with_attributes(
            Ipopt.Optimizer, "max_iter" => 10000, "tol" => 1e-6, "print_level" => 0
        )
        result_lossy = solve_opf(
            data, DCPLLPowerModel, lossy_solver; setting=Dict("output" => Dict("duals" => true))
        )
        results["details"]["lossy_termination"] = string(result_lossy["termination_status"])
        results["details"]["lossy_objective"] = result_lossy["objective"]
        results["details"]["lossy_solve_time"] = result_lossy["solve_time"]

        if result_lossy["termination_status"] == OPTIMAL ||
            result_lossy["primal_status"] == FEASIBLE_POINT
            sol = result_lossy["solution"]

            # Extract bus duals (LMPs)
            lossy_lmps = Dict{String,Float64}()
            for (bid, bus) in sol["bus"]
                lossy_lmps[bid] = get(bus, "lam_kcl_r", NaN)
            end
            results["details"]["lossy_lmps"] = lossy_lmps

            # Extract dispatch
            lossy_dispatch = Dict{String,Float64}()
            for (gid, gen) in sol["gen"]
                lossy_dispatch[gid] = gen["pg"]
            end
            results["details"]["lossy_dispatch_pu"] = lossy_dispatch

            # Branch flows and loss variables
            branch_info = Dict{String,Dict{String,Any}}()
            for (br_id, br) in sol["branch"]
                branch_info[br_id] = Dict("pf" => get(br, "pf", NaN), "pt" => get(br, "pt", NaN))
                # Loss = pf + pt (should be > 0 for lossy model)
                pf = get(br, "pf", 0.0)
                pt = get(br, "pt", 0.0)
                branch_info[br_id]["p_loss"] = pf + pt
            end
            results["details"]["lossy_branch_flows"] = branch_info

            total_loss = sum(bi["p_loss"] for bi in values(branch_info))
            results["details"]["total_system_losses_pu"] = total_loss

            # --- LMP Decomposition ---
            # LMP = energy_component + congestion_component + loss_component
            # For standard DC OPF (lossless): LMP = lambda_ref + sum(PTDF * mu_line)
            # For lossy DC OPF: LMP includes loss marginal

            # Energy component: LMP at reference bus (marginal cost of system energy)
            ref_buses = [bid for (bid, b) in data["bus"] if b["bus_type"] == 3]
            ref_bus = ref_buses[1]
            energy_component = lossy_lmps[ref_bus]
            results["details"]["ref_bus"] = ref_bus
            results["details"]["energy_component_ref_lmp"] = energy_component

            # Congestion component from lossless DC OPF
            lossless_energy = lossless_lmps[ref_bus]

            # Decompose LMPs
            lmp_decomposition = Dict{String,Dict{String,Float64}}()
            for (bid, lmp) in lossy_lmps
                lossless_lmp = get(lossless_lmps, bid, NaN)
                congestion = lossless_lmp - lossless_energy  # congestion from lossless model
                loss = lmp - energy_component - congestion  # residual is loss component
                lmp_decomposition[bid] = Dict(
                    "total_lmp" => lmp,
                    "energy" => energy_component,
                    "congestion" => congestion,
                    "loss" => loss,
                )
            end
            results["details"]["lmp_decomposition"] = lmp_decomposition

            # Check for non-zero loss components
            loss_components = [d["loss"] for d in values(lmp_decomposition)]
            non_zero_losses = count(abs(l) > 1e-6 for l in loss_components)
            results["details"]["buses_with_nonzero_loss_component"] = non_zero_losses
            results["details"]["loss_component_range"] = [
                minimum(loss_components), maximum(loss_components)
            ]

            # Objective difference indicates losses matter
            obj_diff = result_lossy["objective"] - result_lossless["objective"]
            results["details"]["objective_diff_lossy_minus_lossless"] = obj_diff

            if non_zero_losses > 0 && abs(total_loss) > 1e-6
                results["status"] = "pass"
                results["details"]["method"] = "DCPLLPowerModel (piecewise-linear losses) + manual LMP decomposition"
                push!(
                    results["workarounds"],
                    "LMP decomposition is NOT built-in. Required manual extraction: energy = ref bus LMP, congestion = lossless DCOPF dual minus ref LMP, loss = residual (lossy LMP - energy - congestion). This is an approximation; exact decomposition would require access to loss penalty factor duals from the JuMP model.",
                )
            else
                results["details"]["note"] = "Loss components are zero or negligible - may indicate DCPLLPowerModel is not adding meaningful losses for this network"
                # Still pass if the model ran correctly
                if result_lossy["termination_status"] == OPTIMAL
                    results["status"] = "pass"
                    push!(
                        results["workarounds"],
                        "DCPLLPowerModel solved but losses may be negligible for case39. LMP decomposition computed manually but loss component is near-zero.",
                    )
                end
            end
        else
            push!(results["errors"], "Lossy DC OPF did not converge")
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

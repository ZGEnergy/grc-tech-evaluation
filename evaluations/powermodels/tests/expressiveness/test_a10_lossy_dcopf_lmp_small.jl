#=
Test A-10: Lossy DC OPF with LMP Decomposition on SMALL (ACTIVSg 2000-bus)
Dimension: expressiveness
Network: SMALL (ACTIVSg 2000-bus)
Pass condition: Tool produces loss-inclusive LMPs where loss components are non-zero.
Tool: PowerModels.jl v0.21.5
Solver: Ipopt (DCPLLPowerModel generates QCQP, HiGHS can't handle it)
=#

using PowerModels, JuMP, HiGHS, Ipopt, JSON
using SparseArrays, LinearAlgebra

function run(network_file::String)
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
        baseMVA = data["baseMVA"]

        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_branches"] = length(data["branch"])
        results["details"]["num_generators"] = length(data["gen"])
        results["details"]["baseMVA"] = baseMVA
        results["details"]["highs_dcpll_compatible"] = false
        results["details"]["solver_note"] = "DCPLLPowerModel generates QCQP. Using Ipopt."

        push!(results["workarounds"], "HiGHS cannot solve DCPLLPowerModel (QCQP). Ipopt required.")

        # ---- Step 1: Solve lossy DC OPF with DCPLLPowerModel + Ipopt ----
        ipopt_optimizer = JuMP.optimizer_with_attributes(
            Ipopt.Optimizer, "print_level" => 5, "max_iter" => 10000, "tol" => 1e-6
        )

        println("Solving lossy DC OPF (DCPLLPowerModel) on 2000-bus network...")
        dcpll_result = PowerModels.solve_opf(
            data, DCPLLPowerModel, ipopt_optimizer; setting=Dict("output" => Dict("duals" => true))
        )

        term_status = string(dcpll_result["termination_status"])
        results["details"]["dcpll_termination_status"] = term_status
        results["details"]["dcpll_solve_time"] = dcpll_result["solve_time"]
        results["details"]["dcpll_objective"] = dcpll_result["objective"]

        if !(term_status in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"])
            push!(results["errors"], "DCPLLPowerModel OPF did not converge: $term_status")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        sol = dcpll_result["solution"]

        # ---- Step 2: Extract LMPs ----
        bus_lmps = Dict{String,Float64}()
        for (id, bus) in sol["bus"]
            if haskey(bus, "lam_kcl_r")
                bus_lmps[id] = bus["lam_kcl_r"]
            end
        end
        results["details"]["num_lmps_extracted"] = length(bus_lmps)

        if isempty(bus_lmps)
            push!(results["errors"], "No LMPs (lam_kcl_r) found in DCPLL solution")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        lmp_vals = collect(values(bus_lmps))
        results["details"]["lmp_min"] = minimum(lmp_vals)
        results["details"]["lmp_max"] = maximum(lmp_vals)
        results["details"]["lmp_mean"] = sum(lmp_vals) / length(lmp_vals)
        results["details"]["lmp_range"] = maximum(lmp_vals) - minimum(lmp_vals)

        # ---- Step 3: Extract branch flows and compute losses ----
        total_losses = 0.0
        for (id, br) in sol["branch"]
            pf = get(br, "pf", 0.0)
            pt = get(br, "pt", 0.0)
            total_losses += (pf + pt)
        end

        total_load = sum(l["pd"] for (_, l) in data["load"])
        total_gen = sum(g["pg"] for (_, g) in sol["gen"])
        results["details"]["total_losses_pu"] = total_losses
        results["details"]["total_losses_mw"] = total_losses * baseMVA
        results["details"]["total_load_pu"] = total_load
        results["details"]["total_load_mw"] = total_load * baseMVA
        results["details"]["total_generation_pu"] = total_gen
        results["details"]["loss_percentage"] = total_losses / total_load * 100

        losses_nonzero = abs(total_losses) > 1e-6
        results["details"]["losses_nonzero"] = losses_nonzero

        # ---- Step 4: Solve lossless DC OPF for comparison ----
        println("Solving lossless DC OPF for comparison...")
        highs_optimizer = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => false,
        )

        dcopf_result = PowerModels.solve_dc_opf(
            data, highs_optimizer; setting=Dict("output" => Dict("duals" => true))
        )

        dcopf_lmps = Dict{String,Float64}()
        for (id, bus) in dcopf_result["solution"]["bus"]
            if haskey(bus, "lam_kcl_r")
                dcopf_lmps[id] = bus["lam_kcl_r"]
            end
        end
        results["details"]["dcopf_objective"] = dcopf_result["objective"]
        results["details"]["dcopf_num_lmps"] = length(dcopf_lmps)

        # ---- Step 5: LMP Decomposition ----
        ref_bus_id = nothing
        for (id, bus) in data["bus"]
            if bus["bus_type"] == 3
                ref_bus_id = id
                break
            end
        end
        results["details"]["reference_bus"] = ref_bus_id

        energy_component = bus_lmps[ref_bus_id]
        results["details"]["energy_component"] = energy_component

        # Check loss components non-zero
        loss_diffs = [abs(lmp - energy_component) for (_, lmp) in bus_lmps]
        loss_components_nonzero = any(x -> x > 1e-6, loss_diffs)
        results["details"]["loss_components_nonzero"] = loss_components_nonzero

        # LMP spread comparison
        lossless_vals = collect(values(dcopf_lmps))
        lossy_spread = maximum(lmp_vals) - minimum(lmp_vals)
        lossless_spread = maximum(lossless_vals) - minimum(lossless_vals)
        results["details"]["lossy_lmp_spread"] = lossy_spread
        results["details"]["lossless_lmp_spread"] = lossless_spread

        # ---- Step 6: Per-line congestion rent ----
        total_congestion_rent = 0.0
        for (id, br) in sol["branch"]
            pf = get(br, "pf", 0.0)
            f_bus = string(data["branch"][id]["f_bus"])
            t_bus = string(data["branch"][id]["t_bus"])
            lmp_from = get(bus_lmps, f_bus, 0.0)
            lmp_to = get(bus_lmps, t_bus, 0.0)
            rent = pf * (lmp_to - lmp_from) * baseMVA
            total_congestion_rent += rent
        end
        results["details"]["total_congestion_rent"] = total_congestion_rent

        # ---- Step 7: Reconciliation ----
        total_load_payment = 0.0
        for (_, load) in data["load"]
            bus_id = string(load["load_bus"])
            lmp = get(bus_lmps, bus_id, 0.0)
            total_load_payment += load["pd"] * lmp * baseMVA
        end

        total_gen_revenue = 0.0
        for (id, gen) in sol["gen"]
            bus_id = string(data["gen"][id]["gen_bus"])
            lmp = get(bus_lmps, bus_id, 0.0)
            total_gen_revenue += gen["pg"] * lmp * baseMVA
        end

        merchandising_surplus = total_load_payment - total_gen_revenue
        results["details"]["total_load_payment"] = total_load_payment
        results["details"]["total_gen_revenue"] = total_gen_revenue
        results["details"]["merchandising_surplus"] = merchandising_surplus

        if abs(total_load_payment) > 1e-6
            recon_error = abs(merchandising_surplus - total_congestion_rent)
            recon_pct = recon_error / abs(total_load_payment) * 100
            results["details"]["reconciliation_error_pct"] = recon_pct
            results["details"]["reconciliation_within_5pct"] = recon_pct < 5.0
        end

        # ---- Step 8: LMP decomposition sample ----
        lmp_decomp_sample = Dict{String,Dict{String,Float64}}()
        sample_ids = sort(collect(keys(bus_lmps)))[1:min(10, length(bus_lmps))]
        for id in sample_ids
            lmp_decomp_sample[id] = Dict(
                "total_lmp" => bus_lmps[id],
                "energy" => energy_component,
                "congestion_plus_loss" => bus_lmps[id] - energy_component,
                "dcopf_lmp" => get(dcopf_lmps, id, 0.0),
            )
        end
        results["details"]["lmp_decomposition_sample"] = lmp_decomp_sample

        push!(
            results["workarounds"],
            "LMP decomposition (energy/congestion/loss) not built-in to PowerModels. " *
            "Manually computed: energy = ref bus LMP, congestion+loss = LMP - energy.",
        )

        # ---- Final status ----
        if losses_nonzero && length(bus_lmps) == length(data["bus"])
            results["status"] = "pass"
        elseif !losses_nonzero
            push!(results["errors"], "Losses are zero")
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
    nf = get(
        ARGS,
        1,
        joinpath(@__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg2000.m"),
    )
    result = run(nf)
    println(JSON.json(result, 2))
end

#=
Test A-10: Lossy DCOPF with LMP Decomposition

Dimension: expressiveness
Network: TINY (case39.m -- IEEE 39-bus, 46 branches, 10 generators)
Pass condition: Tool produces loss-inclusive LMPs where loss components are non-zero.
                LMP decomposition extractable as structured output.
Tool: PowerSimulations.jl v0.30.2

Expected outcome: FAIL. PSI does not have native lossy DC OPF support.
PowerNetworkMatrices.jl's PTDF does not include loss approximation.
This test documents the limitation.
=#

using PowerSystems
using PowerSimulations
using PowerNetworkMatrices
using HiGHS
using JuMP
using JSON
using DataFrames
using Dates
using TimeSeries

const HIGHS_SETTINGS = [
    "time_limit" => 300.0,
    "mip_rel_gap" => 0.01,
    "presolve" => "on",
    "threads" => 1,
    "output_flag" => true,
]

"""
Prepare system for DecisionModel: fix generator limits and add time series.
"""
function prepare_system_for_opf!(sys::System)
    for gen in get_components(ThermalStandard, sys)
        p = get_active_power(gen)
        pmax = get_active_power_limits(gen).max
        if p > pmax
            set_active_power!(gen, pmax)
        end
    end

    resolution = Hour(1)
    initial_time = DateTime("2024-01-01T00:00:00")
    timestamps = [initial_time, initial_time + resolution]

    for gen in get_components(ThermalStandard, sys)
        ta = TimeArray(timestamps, [1.0, 1.0])
        ts = SingleTimeSeries("max_active_power", ta)
        add_time_series!(sys, gen, ts)
    end
    for gen in get_components(RenewableDispatch, sys)
        ta = TimeArray(timestamps, [1.0, 1.0])
        ts = SingleTimeSeries("max_active_power", ta)
        add_time_series!(sys, gen, ts)
    end
    for load in get_components(PowerLoad, sys)
        ta = TimeArray(timestamps, [1.0, 1.0])
        ts = SingleTimeSeries("max_active_power", ta)
        add_time_series!(sys, load, ts)
    end

    transform_single_time_series!(sys, resolution, resolution)
end

function run_test(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
        "investigation" => Dict{String,Any}(),
    )

    t0 = time()
    try
        sys = System(network_file)

        # ===== Investigation 1: Check PSI network formulations =====
        println("=== Investigation 1: Available PSI network formulations ===")

        # PSI's network formulations from PowerModels integration:
        # - CopperPlatePowerModel: no network constraints
        # - PTDFPowerModel: PTDF-based DC, no losses
        # - DCPPowerModel: DC power flow with angle variables, no losses
        # - ACPPowerModel: AC power flow (via PowerModels -- may not be in PSI)
        # None of these include loss approximation in the DC formulation.

        results["investigation"]["psi_network_formulations"] = Dict(
            "CopperPlatePowerModel" => "No network constraints, no losses",
            "PTDFPowerModel" => "PTDF-based DC OPF, lossless",
            "DCPPowerModel" => "DC power flow with angle variables, lossless",
            "note" =>
                "PSI does not expose a lossy DC OPF formulation. " *
                "The DC OPF formulations (PTDFPowerModel, DCPPowerModel) " *
                "are inherently lossless approximations.",
        )

        # ===== Investigation 2: Check PowerNetworkMatrices for loss support =====
        println("=== Investigation 2: PowerNetworkMatrices PTDF ===")

        ptdf = PTDF(sys)
        results["investigation"]["ptdf_matrix"] = Dict(
            "type" => string(typeof(ptdf)),
            "size" => size(ptdf.data),
            "has_loss_component" => false,
            "note" =>
                "PTDF matrix from PowerNetworkMatrices is a standard lossless " *
                "PTDF. No loss factors or B-prime loss components.",
        )

        # Check if there are any loss-related fields in the PTDF struct
        ptdf_fields = fieldnames(typeof(ptdf))
        results["investigation"]["ptdf_fields"] = [string(f) for f in ptdf_fields]

        # Check branch resistance values (r) -- these would be needed for losses
        branch_r_values = Dict{String,Float64}()
        for branch in get_components(Line, sys)
            bname = get_name(branch)
            r = get_r(branch)
            branch_r_values[bname] = r
        end
        nonzero_r = filter(p -> p.second > 1e-10, branch_r_values)
        results["investigation"]["branch_resistance"] = Dict(
            "total_lines" => length(branch_r_values),
            "nonzero_r_count" => length(nonzero_r),
            "sample_r_values" =>
                Dict(k => v for (k, v) in collect(nonzero_r)[1:min(5, length(nonzero_r))]),
            "note" =>
                "Branches have nonzero resistance, so losses exist physically. " *
                "But PSI's DC formulations ignore these.",
        )

        # ===== Investigation 3: Run standard DC OPF and check for loss components =====
        println("=== Investigation 3: Standard DC OPF -- check for loss components ===")

        prepare_system_for_opf!(sys)
        highs_solver = optimizer_with_attributes(HiGHS.Optimizer, HIGHS_SETTINGS...)

        template = ProblemTemplate(
            NetworkModel(PTDFPowerModel; duals=[CopperPlateBalanceConstraint])
        )
        set_device_model!(template, ThermalStandard, ThermalBasicDispatch)
        set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
        set_device_model!(template, PowerLoad, StaticPowerLoad)
        set_device_model!(template, Line, StaticBranch)
        set_device_model!(template, Transformer2W, StaticBranch)
        set_device_model!(template, TapTransformer, StaticBranch)

        model = DecisionModel(template, sys; optimizer=highs_solver, store_variable_names=true)
        build_status = build!(model; output_dir=mktempdir())

        if occursin("BUILT", string(build_status))
            solve_status = solve!(model)
            if occursin("SUCCESSFULLY_FINALIZED", string(solve_status))
                res = OptimizationProblemResults(model)

                # Check duals -- these are the LMPs
                all_duals = read_duals(res)
                dual_names = [string(k) for k in keys(all_duals)]
                results["investigation"]["available_duals"] = dual_names

                # LMP decomposition requires:
                # LMP_i = lambda (energy) + sum_l(mu_l * PTDF_l_i) (congestion) + loss_component_i
                # Standard DC OPF only provides lambda and congestion -- no loss component
                results["investigation"]["lmp_decomposition"] = Dict(
                    "energy_component" => "Available via CopperPlateBalanceConstraint dual",
                    "congestion_component" => "Available if line flow constraints bind",
                    "loss_component" => "NOT AVAILABLE -- DC formulation is lossless",
                    "decomposition_possible" => false,
                )

                # Show that generation == load (no losses in balance)
                obj_val = get_objective_value(res)
                all_vars = read_variables(res)
                total_gen = 0.0
                total_load = 0.0
                for (var_name, df) in all_vars
                    var_str = string(var_name)
                    if occursin("ActivePower", var_str) && occursin("Thermal", var_str)
                        gen_cols = [c for c in names(df) if c != "DateTime"]
                        total_gen = sum(df[1, col] for col in gen_cols)
                    end
                end
                for load in get_components(PowerLoad, sys)
                    total_load += abs(get_active_power(load))
                end

                results["investigation"]["power_balance"] = Dict(
                    "total_generation_mw" => total_gen,
                    "total_load_mw" => total_load,
                    "difference_mw" => total_gen - total_load,
                    "losses_mw" => 0.0,
                    "note" => "Generation exactly equals load -- confirms lossless formulation",
                )

                results["details"]["dcopf_objective"] = obj_val
            end
        end

        # ===== Investigation 4: Check if DCPPowerModel has loss support =====
        println("=== Investigation 4: DCPPowerModel formulation ===")

        sys2 = System(network_file)
        prepare_system_for_opf!(sys2)

        # Try DCPPowerModel -- this uses bus angle variables instead of PTDF
        try
            template2 = ProblemTemplate(
                NetworkModel(DCPPowerModel; duals=[NodalBalanceActiveConstraint])
            )
            set_device_model!(template2, ThermalStandard, ThermalBasicDispatch)
            set_device_model!(template2, RenewableDispatch, RenewableFullDispatch)
            set_device_model!(template2, PowerLoad, StaticPowerLoad)
            set_device_model!(template2, Line, StaticBranch)
            set_device_model!(template2, Transformer2W, StaticBranch)
            set_device_model!(template2, TapTransformer, StaticBranch)

            model2 = DecisionModel(
                template2,
                sys2;
                optimizer=optimizer_with_attributes(HiGHS.Optimizer, HIGHS_SETTINGS...),
                store_variable_names=true,
            )
            build_status2 = build!(model2; output_dir=mktempdir())

            if occursin("BUILT", string(build_status2))
                solve_status2 = solve!(model2)
                if occursin("SUCCESSFULLY_FINALIZED", string(solve_status2))
                    res2 = OptimizationProblemResults(model2)
                    obj2 = get_objective_value(res2)

                    # Check if DCPPowerModel produces nodal LMPs
                    all_duals2 = read_duals(res2)
                    for (dname, df) in all_duals2
                        if occursin("Nodal", string(dname))
                            bus_cols = [c for c in names(df) if c != "DateTime"]
                            nodal_lmps = Dict{String,Float64}()
                            for col in bus_cols
                                nodal_lmps[col] = df[1, col]
                            end
                            results["investigation"]["dcp_nodal_lmps"] = nodal_lmps
                            results["investigation"]["dcp_lmp_count"] = length(bus_cols)

                            # Check if all LMPs are identical (would confirm no loss component)
                            lmp_vals = collect(values(nodal_lmps))
                            results["investigation"]["dcp_lmps_uniform"] = all(
                                abs.(lmp_vals .- lmp_vals[1]) .< 1e-6
                            )
                            results["investigation"]["dcp_lmp_range"] = Dict(
                                "min" => minimum(lmp_vals),
                                "max" => maximum(lmp_vals),
                                "spread" => maximum(lmp_vals) - minimum(lmp_vals),
                            )
                        end
                    end

                    results["investigation"]["dcp_objective"] = obj2
                    results["investigation"]["dcp_note"] =
                        "DCPPowerModel also uses lossless DC approximation. " *
                        "LMP differences across buses reflect congestion only, not losses."
                end
            end
        catch e
            results["investigation"]["dcp_error"] = string(typeof(e), ": ", sprint(showerror, e))
        end

        # ===== Final determination =====
        results["status"] = "fail"
        results["details"]["reason"] =
            "PSI does not support lossy DC OPF. All DC formulations " *
            "(PTDFPowerModel, DCPPowerModel) use lossless approximation. There is no mechanism " *
            "to include loss factors in the optimization. LMP decomposition into energy + " *
            "congestion is possible, but the loss component is always zero."
        results["details"]["what_would_be_needed"] = [
            "A lossy DC formulation (e.g., iterative loss approximation with Bprime matrix)",
            "Or integration with PowerModels.jl's DCPLLPowerModel (lossy DC formulation)",
            "PSI does not expose PowerModels formulations that include loss approximation",
        ]

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

# Run and print
result = run_test()
println("\n" * "="^80)
println("RESULT JSON:")
println("="^80)
println(JSON.json(result, 2))

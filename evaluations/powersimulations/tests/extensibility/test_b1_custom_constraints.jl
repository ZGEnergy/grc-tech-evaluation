#=
Test B-1: Custom Constraints (flow gate limit + dual extraction)

Dimension: extensibility
Network: TINY (case39.m — IEEE 39-bus)
Pass condition: Achievable through a documented API or extension mechanism.
               No source patching. Dual value of custom constraint extractable.
Tool: PowerSimulations.jl v0.30.2
Solver: HiGHS
=#

using PowerSystems
using PowerSimulations
using HiGHS
using JuMP
using JSON
using DataFrames
using Dates
using TimeSeries

const PSI = PowerSimulations

const HIGHS_SETTINGS = [
    "time_limit" => 300.0,
    "mip_rel_gap" => 0.01,
    "presolve" => "on",
    "threads" => 1,
    "output_flag" => true,
]

"""
Prepare system for DecisionModel: fix generator limits and add time series.
Same boilerplate as A-3.
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

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        # 1. Load and prepare system
        sys = System(network_file)
        n_buses = length(collect(get_components(ACBus, sys)))
        n_branches = length(collect(get_components(Branch, sys)))
        results["details"]["network"] = Dict("buses" => n_buses, "branches" => n_branches)

        prepare_system_for_opf!(sys)

        # 2. Build DCOPF model (same as A-3)
        template = ProblemTemplate(
            NetworkModel(PTDFPowerModel; duals=[CopperPlateBalanceConstraint])
        )
        set_device_model!(template, ThermalStandard, ThermalBasicDispatch)
        set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
        set_device_model!(template, PowerLoad, StaticPowerLoad)
        set_device_model!(template, Line, StaticBranch)
        set_device_model!(template, Transformer2W, StaticBranch)
        set_device_model!(template, TapTransformer, StaticBranch)

        solver = optimizer_with_attributes(HiGHS.Optimizer, HIGHS_SETTINGS...)
        model = DecisionModel(template, sys; optimizer=solver, store_variable_names=true)
        build_status = build!(model; output_dir=mktempdir())
        results["details"]["build_status"] = string(build_status)

        if !occursin("BUILT", string(build_status))
            push!(results["errors"], "Model build failed: $(build_status)")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # 3. Access the JuMP model and add a flow gate constraint
        # The key extensibility test: can we inject custom constraints into PSI's JuMP model?
        jump_model = PSI.get_jump_model(model)
        results["details"]["jump_model_accessible"] = true
        results["details"]["jump_model_type"] = string(typeof(jump_model))

        # Get the optimization container to access PSI's variable containers
        container = PSI.get_optimization_container(model)
        results["details"]["container_accessible"] = true

        # 4. Identify flow variables for the flow gate
        # Flow gate: limit combined flow on lines connecting buses 15-16, 16-17, 16-19
        # These are major transmission corridors in case39
        gate_lines = String[]
        all_lines = collect(get_components(Line, sys))
        for line in all_lines
            from_bus = get_number(get_from(get_arc(line)))
            to_bus = get_number(get_to(get_arc(line)))
            if (from_bus == 15 && to_bus == 16) ||
                (from_bus == 16 && to_bus == 15) ||
                (from_bus == 16 && to_bus == 17) ||
                (from_bus == 17 && to_bus == 16) ||
                (from_bus == 16 && to_bus == 19) ||
                (from_bus == 19 && to_bus == 16)
                push!(gate_lines, get_name(line))
            end
        end

        # Also check TapTransformers
        for branch in get_components(TapTransformer, sys)
            from_bus = get_number(get_from(get_arc(branch)))
            to_bus = get_number(get_to(get_arc(branch)))
            if (from_bus == 15 && to_bus == 16) ||
                (from_bus == 16 && to_bus == 15) ||
                (from_bus == 16 && to_bus == 17) ||
                (from_bus == 17 && to_bus == 16) ||
                (from_bus == 16 && to_bus == 19) ||
                (from_bus == 19 && to_bus == 16)
                push!(gate_lines, get_name(branch))
            end
        end

        results["details"]["gate_lines_identified"] = gate_lines
        results["details"]["gate_line_count"] = length(gate_lines)

        # If no specific lines found for that corridor, use the first 3 lines
        if isempty(gate_lines)
            line_names = [get_name(l) for l in all_lines]
            gate_lines = line_names[1:min(3, length(line_names))]
            results["details"]["gate_fallback"] = "Used first 3 lines as no 15-16/16-17/16-19 corridor found"
        end

        # 5. Find flow variables in the JuMP model
        # PSI stores flow variables with specific naming patterns
        all_jump_vars = JuMP.all_variables(jump_model)
        results["details"]["total_jump_variables"] = length(all_jump_vars)

        # Find flow variables for our gate lines
        gate_flow_vars = JuMP.VariableRef[]
        gate_flow_var_names = String[]
        for var in all_jump_vars
            var_name = JuMP.name(var)
            for line_name in gate_lines
                if occursin("FlowActivePower", var_name) && occursin(line_name, var_name)
                    push!(gate_flow_vars, var)
                    push!(gate_flow_var_names, var_name)
                end
            end
        end

        results["details"]["gate_flow_vars_found"] = length(gate_flow_vars)
        results["details"]["gate_flow_var_names"] = gate_flow_var_names

        # 6. Add flow gate constraint with a BINDING limit
        # First solve without the gate to find the unconstrained total flow
        solve_status_base = solve!(model)
        results["details"]["base_solve_status"] = string(solve_status_base)

        if occursin("SUCCESSFULLY_FINALIZED", string(solve_status_base))
            # Get base flow values
            base_gate_flow = 0.0
            for var in gate_flow_vars
                base_gate_flow += abs(JuMP.value(var))
            end
            results["details"]["base_gate_flow_abs_sum"] = base_gate_flow

            base_obj = JuMP.objective_value(jump_model)
            results["details"]["base_objective"] = base_obj

            # Set the gate limit to 80% of unconstrained flow to make it binding
            gate_limit = 0.8 * base_gate_flow
            if gate_limit < 0.01
                gate_limit = 1.0  # fallback if flow is near zero
            end
            results["details"]["gate_limit_pu"] = gate_limit

            # Add the flow gate constraint (sum of absolute flows <= limit)
            # For PTDF-based DC OPF, flows can be positive or negative
            # Use sum of flows (signed) for a directional gate
            flow_gate_con = @constraint(jump_model, flow_gate, sum(gate_flow_vars) <= gate_limit)
            results["details"]["constraint_added"] = true
            results["details"]["constraint_name"] = "flow_gate"

            # 7. Re-solve with the gate constraint
            t_resolve = time()
            JuMP.optimize!(jump_model)
            resolve_time = time() - t_resolve
            results["details"]["constrained_solve_time_seconds"] = resolve_time

            term_status = JuMP.termination_status(jump_model)
            results["details"]["constrained_termination_status"] = string(term_status)

            if term_status == MOI.OPTIMAL || term_status == MOI.LOCALLY_SOLVED
                constrained_obj = JuMP.objective_value(jump_model)
                results["details"]["constrained_objective"] = constrained_obj
                results["details"]["objective_increase"] = constrained_obj - base_obj

                # 8. Extract dual value of the flow gate constraint
                gate_dual = JuMP.dual(flow_gate_con)
                results["details"]["flow_gate_dual"] = gate_dual
                results["details"]["dual_extractable"] = true
                results["details"]["constraint_binding"] = abs(gate_dual) > 1e-8

                # Constrained flow values
                constrained_gate_flow = sum(JuMP.value(var) for var in gate_flow_vars)
                results["details"]["constrained_gate_flow_sum"] = constrained_gate_flow

                # 9. Produce binding constraint report
                # Check all constraints in the model for binding status
                binding_report = Dict{String,Any}[]

                # Flow gate constraint
                push!(
                    binding_report,
                    Dict(
                        "constraint" => "flow_gate",
                        "type" => "custom",
                        "dual" => gate_dual,
                        "binding" => abs(gate_dual) > 1e-8,
                        "value" => constrained_gate_flow,
                        "limit" => gate_limit,
                    ),
                )

                # System balance constraint (from PSI)
                res = OptimizationProblemResults(model)
                try
                    all_duals = read_duals(res)
                    for (dual_name, df) in all_duals
                        dual_cols = [c for c in names(df) if c != "DateTime"]
                        for col in dual_cols
                            val = df[1, col]
                            push!(
                                binding_report,
                                Dict(
                                    "constraint" => "$(dual_name)__$(col)",
                                    "type" => "psi_native",
                                    "dual" => val,
                                    "binding" => abs(val) > 1e-8,
                                ),
                            )
                        end
                    end
                catch e
                    results["details"]["psi_duals_error"] = string(e)
                end

                results["details"]["binding_report"] = binding_report
                results["details"]["binding_count"] = count(r -> r["binding"], binding_report)
                results["details"]["total_constraints_reported"] = length(binding_report)

                # 10. Also test with a NON-binding constraint (very loose limit)
                # Remove old constraint and add a very loose one
                JuMP.delete(jump_model, flow_gate_con)
                loose_limit = 100.0  # very loose
                flow_gate_loose = @constraint(
                    jump_model, flow_gate_loose, sum(gate_flow_vars) <= loose_limit
                )
                JuMP.optimize!(jump_model)

                loose_term = JuMP.termination_status(jump_model)
                if loose_term == MOI.OPTIMAL || loose_term == MOI.LOCALLY_SOLVED
                    loose_dual = JuMP.dual(flow_gate_loose)
                    results["details"]["loose_gate_dual"] = loose_dual
                    results["details"]["loose_constraint_binding"] = abs(loose_dual) > 1e-8
                    results["details"]["dual_correctly_zero_when_nonbinding"] =
                        abs(loose_dual) < 1e-8
                end

                results["status"] = "pass"
            else
                push!(results["errors"], "Constrained solve failed: $term_status")
            end
        else
            push!(results["errors"], "Base solve failed: $solve_status_base")
        end

        # Document approach
        results["details"]["approach"] = Dict(
            "step1" => "Build standard DCOPF via PSI DecisionModel with PTDFPowerModel",
            "step2" => "Access JuMP model via PSI.get_jump_model(model) — documented internal API",
            "step3" => "Find flow variables by name from JuMP.all_variables()",
            "step4" => "Add @constraint directly to JuMP model",
            "step5" => "Re-solve via JuMP.optimize! and extract dual via JuMP.dual()",
        )
        results["details"]["extension_mechanism"] = "Direct JuMP model access via PSI.get_jump_model()"

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

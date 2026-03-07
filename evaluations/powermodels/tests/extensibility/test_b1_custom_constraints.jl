#=
Test B-1: Add a flow gate limit to DC OPF (custom constraint with dual extraction)
Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Achievable through documented API or extension mechanism.
               No source patching. Dual value extractable and correctly reflects binding status.
Tool: PowerModels.jl v0.21.5
Solver: HiGHS

Approach: Use PowerModels' two-level API:
  1. instantiate_model() to build the JuMP model without solving
  2. Add custom flow gate constraint directly to the JuMP model
  3. optimize_model!() to solve
  4. Extract dual value via JuMP.dual()
=#

using PowerModels, JuMP, HiGHS, JSON

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
        PowerModels.solve_dc_opf(_data, HiGHS.Optimizer)
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

        # Solver settings
        optimizer = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => true,
        )

        # ---- Step 1: Solve base case DC OPF (no flow gate) for comparison ----
        base_result = PowerModels.solve_dc_opf(
            data, optimizer; setting=Dict("output" => Dict("duals" => true))
        )
        base_obj = base_result["objective"]
        results["details"]["base_objective"] = base_obj
        results["details"]["base_termination"] = string(base_result["termination_status"])

        # Get base case branch flows to identify a good flow gate candidate
        base_flows = Dict{String,Float64}()
        for (id, br) in base_result["solution"]["branch"]
            base_flows[id] = br["pf"]
        end

        # Find the branch with largest absolute flow -- good candidate for binding constraint
        max_flow_id = ""
        max_flow_val = 0.0
        for (id, pf) in base_flows
            if abs(pf) > max_flow_val
                max_flow_val = abs(pf)
                max_flow_id = id
            end
        end
        results["details"]["max_flow_branch"] = max_flow_id
        results["details"]["max_flow_value_pu"] = round(max_flow_val; digits=6)

        # Define flow gate: limit branch with largest flow to 80% of base flow
        # This should force the constraint to bind
        gate_branch_id = max_flow_id
        gate_limit = 0.8 * max_flow_val
        results["details"]["flow_gate_branch"] = gate_branch_id
        results["details"]["flow_gate_limit_pu"] = round(gate_limit; digits=6)
        results["details"]["flow_gate_pct_of_base"] = 80.0

        # ---- Step 2: Use two-level API to build model, add constraint, solve ----
        # instantiate_model builds the JuMP model without solving
        pm = PowerModels.instantiate_model(data, PowerModels.DCPPowerModel, PowerModels.build_opf)

        # Access the JuMP model
        jump_model = pm.model

        # Find the branch flow variable for the gate branch
        # In PowerModels DC OPF, branch flow variables are indexed by (branch_id, from_bus, to_bus)
        # Access via pm.var[:it][:pm][:nw][0][:p]
        nw_id = PowerModels.nw_id_default
        p_vars = PowerModels.var(pm, nw_id, :p)

        # Find the correct arc index for our gate branch
        br_data = data["branch"][gate_branch_id]
        f_bus = br_data["f_bus"]
        t_bus = br_data["t_bus"]
        br_idx = parse(Int, gate_branch_id)

        # The p variable is indexed by (branch_id, from_bus, to_bus) for arcs_from
        flow_var = p_vars[(br_idx, f_bus, t_bus)]
        results["details"]["flow_variable_found"] = true
        results["details"]["flow_variable_name"] = string(JuMP.name(flow_var))

        # Add flow gate constraint: -gate_limit <= flow <= gate_limit
        gate_con_upper = @constraint(jump_model, flow_var <= gate_limit)
        gate_con_lower = @constraint(jump_model, flow_var >= -gate_limit)

        results["details"]["constraints_added"] = true
        results["details"]["api_method"] = "instantiate_model + @constraint on pm.model"

        # ---- Step 3: Solve the constrained model ----
        constrained_result = PowerModels.optimize_model!(pm; optimizer=optimizer)

        term_status = string(constrained_result["termination_status"])
        results["details"]["constrained_termination"] = term_status
        results["details"]["constrained_objective"] = constrained_result["objective"]
        results["details"]["constrained_solve_time"] = constrained_result["solve_time"]

        if !(term_status in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"])
            push!(results["errors"], "Constrained DC OPF did not converge: $term_status")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # ---- Step 4: Extract dual value of the flow gate constraint ----
        dual_upper = JuMP.dual(gate_con_upper)
        dual_lower = JuMP.dual(gate_con_lower)

        results["details"]["dual_upper"] = round(dual_upper; digits=6)
        results["details"]["dual_lower"] = round(dual_lower; digits=6)

        # Determine binding status
        constrained_flow = JuMP.value(flow_var)
        results["details"]["constrained_flow_value"] = round(constrained_flow; digits=6)

        upper_binding = abs(constrained_flow - gate_limit) < 1e-4
        lower_binding = abs(constrained_flow - (-gate_limit)) < 1e-4
        binding = upper_binding || lower_binding
        results["details"]["constraint_binding"] = binding
        results["details"]["upper_binding"] = upper_binding
        results["details"]["lower_binding"] = lower_binding

        # A binding constraint should have non-zero dual
        dual_nonzero = abs(dual_upper) > 1e-8 || abs(dual_lower) > 1e-8
        results["details"]["dual_nonzero"] = dual_nonzero

        # Verify objective increased (more constrained = higher cost)
        obj_increase = constrained_result["objective"] - base_obj
        results["details"]["objective_increase"] = round(obj_increase; digits=4)
        results["details"]["objective_increased"] = obj_increase > 1e-6

        # ---- Step 5: Build binding constraint report ----
        report = Dict(
            "flow_gate_definition" => Dict(
                "branch_id" => gate_branch_id,
                "from_bus" => f_bus,
                "to_bus" => t_bus,
                "limit_pu" => round(gate_limit; digits=6),
                "limit_pct_of_base_flow" => 80.0,
            ),
            "base_case" => Dict(
                "objective" => base_obj,
                "flow_on_gate_branch" => round(base_flows[gate_branch_id]; digits=6),
            ),
            "constrained_case" => Dict(
                "objective" => constrained_result["objective"],
                "flow_on_gate_branch" => round(constrained_flow; digits=6),
                "constraint_binding" => binding,
                "dual_upper" => round(dual_upper; digits=6),
                "dual_lower" => round(dual_lower; digits=6),
            ),
            "cost_of_constraint" => round(obj_increase; digits=4),
        )
        results["details"]["binding_constraint_report"] = report

        # Verify pass conditions
        if !binding
            push!(results["errors"], "Flow gate constraint not binding -- test design issue")
        end
        if !dual_nonzero
            push!(results["errors"], "Dual value is zero despite expected binding constraint")
        end

        if binding && dual_nonzero
            results["status"] = "pass"
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

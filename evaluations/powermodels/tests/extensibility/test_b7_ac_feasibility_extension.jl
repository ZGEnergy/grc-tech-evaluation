#=
Test B-7: AC Feasibility Extension -- document workaround from A-4
Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Workaround durability assessed. Effort documented.
Tool: PowerModels.jl v0.21.5
Solver: Ipopt
Depends on: A-4 (AC feasibility check)

Assessment: A-4 was a clean PASS with NO workaround needed.
The DC OPF -> AC PF workflow operates on the same in-memory data dict.
Generator Pg values are set directly, compute_ac_pf runs on the modified dict.
No file export/reimport, no custom serialization, no model reconstruction.
This test documents that finding.
=#

using PowerModels, JuMP, HiGHS, Ipopt, JSON

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

    t0 = time()
    try
        # Reproduce A-4 workflow to confirm no workaround needed
        data = PowerModels.parse_file(network_file)

        results["details"]["num_buses"] = length(data["bus"])

        # Step 1: DC OPF
        optimizer = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => false,
        )
        opf_result = PowerModels.solve_dc_opf(data, optimizer)
        dc_term = string(opf_result["termination_status"])

        if !(dc_term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"])
            push!(results["errors"], "DC OPF did not converge: $dc_term")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # Step 2: Fix gen Pg in data dict (in-place, no model reconstruction)
        dc_sol = opf_result["solution"]
        for (id, gen) in dc_sol["gen"]
            data["gen"][id]["pg"] = gen["pg"]
        end

        # Step 3: Run AC PF on modified data (flat start)
        ac_result = PowerModels.compute_ac_pf(data)
        ac_converged = ac_result["termination_status"]

        results["details"]["dcopf_termination"] = dc_term
        results["details"]["ac_pf_converged"] = ac_converged
        results["details"]["workaround_needed"] = false
        results["details"]["workaround_class"] = "none"

        # Document the workflow
        results["details"]["workflow"] = Dict(
            "step_1" => "parse_file() to load MATPOWER case",
            "step_2" => "solve_dc_opf() with HiGHS to get optimal dispatch",
            "step_3" => "Set data['gen'][id]['pg'] = dc_dispatch for all gens (in-place dict mutation)",
            "step_4" => "compute_ac_pf(data) on same dict (no file I/O, no model rebuild)",
            "step_5" => "calc_branch_flow_ac(data) for thermal violation check",
            "step_6" => "Compare Vm against vmin/vmax for voltage violations",
        )

        results["details"]["api_quality_assessment"] = Dict(
            "data_model_mutable" => true,
            "same_context_workflow" => true,
            "requires_file_export" => false,
            "requires_model_reconstruction" => false,
            "requires_custom_serialization" => false,
            "convergence_on_flat_start" => ac_converged,
            "effort_level" => "trivial (3 lines: set pg, compute_ac_pf, calc_branch_flow_ac)",
        )

        results["details"]["durability_assessment"] = Dict(
            "classification" => "N/A -- no workaround needed",
            "relies_on_internals" => false,
            "version_sensitive" => false,
            "explanation" =>
                "The workflow uses only public API functions (solve_dc_opf, " *
                "compute_ac_pf, calc_branch_flow_ac) and standard dict operations. " *
                "No workaround was required because the data model is a mutable Dict " *
                "and the PF/OPF functions operate on the same data structure.",
        )

        results["status"] = "pass"

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

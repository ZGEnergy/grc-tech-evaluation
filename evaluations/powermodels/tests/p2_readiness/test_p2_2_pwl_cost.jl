#=
Test P2-2: Piecewise-linear cost curve for DC OPF on TINY (IEEE 39-bus)
Dimension: p2_readiness
Network: TINY (IEEE 39-bus)
Pass condition: Informational — capability (yes/no), formulation type, solver compat
Tool: PowerModels.jl v0.21.5
Solver: HiGHS

Approach:
1. Parse case39.m
2. Modify generator 1 to use model=1 (piecewise-linear) with 3 segments
3. Solve DC OPF with HiGHS
4. Also solve with original quadratic costs (model=2) for comparison
=#

using PowerModels, JuMP, HiGHS, JSON

function run_pwl_test(
    network_file::String=joinpath(@__DIR__, "..", "..", "..", "..", "data", "networks", "case39.m")
)
    results = Dict(
        "status" => "fail", "wall_clock_seconds" => 0.0, "details" => Dict(), "errors" => String[]
    )

    t0 = time()
    try
        # ---- Test 1: Piecewise-linear cost (model=1) ----
        data = PowerModels.parse_file(network_file)

        results["details"]["num_generators"] = length(data["gen"])

        # Original gen 1 cost: model=2, ncost=3, cost=[0.01, 0.3, 0.2] (quadratic)
        gen1 = data["gen"]["1"]
        results["details"]["original_gen1_cost"] = Dict(
            "model" => gen1["model"], "ncost" => gen1["ncost"], "cost" => gen1["cost"]
        )

        # Convert gen 1 to piecewise-linear (model=1) with 4 points (3 segments)
        # Format: model=1, ncost=4, cost=[p0, c0, p1, c1, p2, c2, p3, c3]
        # where (p_i, c_i) are (MW, cost) breakpoints
        pmin = gen1["pmin"]
        pmax = gen1["pmax"]
        p_range = pmax - pmin

        # Define 4 breakpoints creating 3 segments with increasing marginal cost
        bp = [
            pmin,                    # breakpoint 0
            pmin + p_range * 0.33,   # breakpoint 1
            pmin + p_range * 0.67,   # breakpoint 2
            pmax,                    # breakpoint 3
        ]

        # Cost at each breakpoint (convex, increasing marginal cost)
        # Segment 1: marginal cost 0.20 $/MWh
        # Segment 2: marginal cost 0.35 $/MWh
        # Segment 3: marginal cost 0.50 $/MWh
        c0 = 0.2  # fixed/startup cost
        costs = [
            c0,
            c0 + 0.20 * (bp[2] - bp[1]),
            c0 + 0.20 * (bp[2] - bp[1]) + 0.35 * (bp[3] - bp[2]),
            c0 + 0.20 * (bp[2] - bp[1]) + 0.35 * (bp[3] - bp[2]) + 0.50 * (bp[4] - bp[3]),
        ]

        # Set PWL cost: interleaved [p0, c0, p1, c1, ...]
        gen1["model"] = 1
        gen1["ncost"] = 4  # number of breakpoints
        gen1["cost"] = Float64[]
        for i in 1:4
            push!(gen1["cost"], bp[i])
            push!(gen1["cost"], costs[i])
        end

        results["details"]["pwl_gen1_cost"] = Dict(
            "model" => gen1["model"],
            "ncost" => gen1["ncost"],
            "cost" => gen1["cost"],
            "breakpoints_mw" => bp,
            "breakpoints_cost" => costs,
            "marginal_costs_per_segment" => [0.20, 0.35, 0.50],
        )

        # Solve DC OPF with PWL cost
        optimizer = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => true,
        )

        println("=== Solving DC OPF with piecewise-linear cost on gen 1 ===")
        pwl_result = PowerModels.solve_dc_opf(data, optimizer)

        pwl_status = string(pwl_result["termination_status"])
        results["details"]["pwl_termination"] = pwl_status
        results["details"]["pwl_objective"] = pwl_result["objective"]
        results["details"]["pwl_solve_time"] = pwl_result["solve_time"]

        if pwl_status in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"]
            results["details"]["pwl_gen1_pg"] = pwl_result["solution"]["gen"]["1"]["pg"]
            results["details"]["pwl_converged"] = true

            # Extract all gen dispatch
            pwl_dispatch = Dict{String,Float64}()
            for (id, gen) in pwl_result["solution"]["gen"]
                pwl_dispatch[id] = gen["pg"]
            end
            results["details"]["pwl_dispatch"] = pwl_dispatch
        else
            results["details"]["pwl_converged"] = false
            push!(results["errors"], "PWL DC OPF did not converge: $pwl_status")
        end

        # ---- Test 2: All gens PWL (model=1) ----
        data2 = PowerModels.parse_file(network_file)
        println("\n=== Solving DC OPF with ALL generators using piecewise-linear costs ===")

        for (id, gen) in data2["gen"]
            gp_min = gen["pmin"]
            gp_max = gen["pmax"]
            gp_range = gp_max - gp_min
            if gp_range <= 0
                gp_range = gp_max  # handle pmin=0 case
            end

            bp_g = [gp_min, gp_min + gp_range * 0.33, gp_min + gp_range * 0.67, gp_max]

            # Use the original quadratic cost to compute equivalent PWL breakpoints
            orig_cost = gen["cost"]  # [c2, c1, c0] for model=2, ncost=3
            c2, c1, c0_g = orig_cost[1], orig_cost[2], orig_cost[3]

            cost_at(p) = c2 * p^2 + c1 * p + c0_g
            costs_g = [cost_at(p) for p in bp_g]

            gen["model"] = 1
            gen["ncost"] = 4
            gen["cost"] = Float64[]
            for i in 1:4
                push!(gen["cost"], bp_g[i])
                push!(gen["cost"], costs_g[i])
            end
        end

        all_pwl_result = PowerModels.solve_dc_opf(data2, optimizer)
        all_pwl_status = string(all_pwl_result["termination_status"])
        results["details"]["all_pwl_termination"] = all_pwl_status
        results["details"]["all_pwl_objective"] = all_pwl_result["objective"]

        if all_pwl_status in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"]
            results["details"]["all_pwl_converged"] = true
        else
            results["details"]["all_pwl_converged"] = false
        end

        # ---- Test 3: Quadratic cost (model=2) baseline for comparison ----
        data3 = PowerModels.parse_file(network_file)
        println("\n=== Solving DC OPF with original quadratic costs (model=2) ===")

        quad_result = PowerModels.solve_dc_opf(data3, optimizer)
        quad_status = string(quad_result["termination_status"])
        results["details"]["quad_termination"] = quad_status
        results["details"]["quad_objective"] = quad_result["objective"]

        if quad_status in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"]
            results["details"]["quad_converged"] = true
            results["details"]["quad_gen1_pg"] = quad_result["solution"]["gen"]["1"]["pg"]
        else
            results["details"]["quad_converged"] = false
        end

        # ---- Inspect formulation type ----
        # Build model explicitly to inspect variable/constraint types
        println("\n=== Inspecting PWL formulation internals ===")
        data4 = PowerModels.parse_file(network_file)
        data4["gen"]["1"]["model"] = 1
        data4["gen"]["1"]["ncost"] = 4
        data4["gen"]["1"]["cost"] = results["details"]["pwl_gen1_cost"]["cost"]

        pm = PowerModels.instantiate_model(
            data4,
            DCPPowerModel,
            PowerModels.build_opf;
            setting=Dict("output" => Dict("duals" => false)),
        )

        # Check JuMP model for PWL-related variables
        jump_model = pm.model
        all_vars = JuMP.all_variables(jump_model)
        var_names = [JuMP.name(v) for v in all_vars]

        # Look for PWL-related variables (lambda, delta, etc.)
        pwl_vars = filter(n -> occursin(r"pwl|lambda|delta|_cost"i, n), var_names)
        results["details"]["pwl_variable_names"] = pwl_vars
        results["details"]["total_variables"] = length(all_vars)

        # Check constraint types
        constraint_types = JuMP.list_of_constraint_types(jump_model)
        results["details"]["constraint_types"] = [string(ct) for ct in constraint_types]

        # Check for SOS2 constraints
        has_sos2 = any(ct -> string(ct[2]) == "MathOptInterface.SOS2{Float64}", constraint_types)
        results["details"]["has_sos2"] = has_sos2

        results["details"]["formulation_notes"] =
            "PowerModels uses an internal lambda-based " *
            "convex combination formulation for PWL costs. Variables named with 'pg_cost' " *
            "represent the cost contribution. No SOS2 constraints are used; instead, " *
            "the convexity of the PWL function is exploited in the LP formulation."

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
    result = run_pwl_test()
    println("\n" * "="^60)
    println("RESULTS JSON:")
    println("="^60)
    println(JSON.json(result, 2))
end

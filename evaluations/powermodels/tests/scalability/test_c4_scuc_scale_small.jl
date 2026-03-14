#=
Test C-4: SCUC Scale — SMALL (ACTIVSg 2000-bus)

Dimension: scalability
Network: SMALL (ACTIVSg 2000, 2000 buses, 544 generators)
Pass condition: Wall-clock time per solver, MIP gap at termination, peak memory
Tool: PowerModels.jl v0.21.5
Solver: HiGHS, SCIP (MILP)

Depends on: A-5 (SCUC on TINY) — qualified_pass via user-assembled JuMP MILP
  A-5 established that PowerModels does NOT natively support SCUC. The entire
  UC formulation must be user-assembled as a JuMP MILP. This test scales
  that approach to the 2000-bus ACTIVSg network.

Network characteristics:
  - 2000 buses, 3206 branches, 544 generators
  - System load: ~67.1 GW, capacity: ~96.3 GW (ratio 1.43x)
  - Generators have polynomial cost models from MATPOWER data
  - No Modified Tiny augmentation — use native MATPOWER costs and generate
    synthetic 24-hour load profile by scaling base load

Implementation approach:
  Same user-assembled JuMP MILP as A-5, scaled to 2000-bus:
  1. Parse case_ACTIVSg2000.m via PowerModels.parse_file
  2. Generate 24-hour load profile by scaling base load with hourly multipliers
  3. Assign UC parameters (min up/down, ramp rates, startup costs) based on
     generator size as a proxy for technology type
  4. Build custom JuMP MILP with commitment, startup/shutdown, power balance,
     DC power flow, and thermal limits
  5. Solve with HiGHS (primary) and SCIP (secondary)

Timeout: 30 minutes (1800s) per solver
=#

using PowerModels
using HiGHS
using SCIP
using JuMP

PowerModels.silence()

# 24-hour load shape multipliers (typical summer day, from representative profile)
const LOAD_MULTIPLIERS = [
    0.75,
    0.72,
    0.70,
    0.68,
    0.70,
    0.75,  # H1-H6: overnight trough
    0.82,
    0.90,
    0.95,
    0.97,
    0.98,
    1.00,  # H7-H12: morning ramp
    0.99,
    0.97,
    0.96,
    0.95,
    0.96,
    1.00,  # H13-H18: afternoon
    0.98,
    0.95,
    0.90,
    0.85,
    0.80,
    0.77,  # H19-H24: evening decline
]

# Technology classification by capacity (proxy for fuel type)
function classify_generator(pmax_mw::Float64)
    if pmax_mw < 50.0
        return "peaker"     # small units: gas CT, peaker
    elseif pmax_mw < 200.0
        return "mid"        # mid-range: gas CC, small coal
    elseif pmax_mw < 500.0
        return "baseload"   # large units: large coal, nuclear
    else
        return "nuclear"    # very large: nuclear
    end
end

# UC parameters by technology class
const UC_PARAMS = Dict(
    "peaker" => (min_up=2, min_down=1, ramp_frac=1.0, startup_cost_per_mw=15.0, no_load_frac=0.10),
    "mid" => (min_up=4, min_down=3, ramp_frac=0.50, startup_cost_per_mw=25.0, no_load_frac=0.15),
    "baseload" =>
        (min_up=8, min_down=6, ramp_frac=0.30, startup_cost_per_mw=40.0, no_load_frac=0.20),
    "nuclear" =>
        (min_up=24, min_down=24, ramp_frac=0.10, startup_cost_per_mw=100.0, no_load_frac=0.25),
)

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024  # kB to MB
        end
    end
    return nothing
end

function run(
    network_file::String="../../data/networks/case_ACTIVSg2000.m";
    timeseries_dir::Union{String,Nothing}=nothing,
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        # ==================================================================
        # 1. Load network data
        # ==================================================================
        data = PowerModels.parse_file(network_file)
        base_mva = data["baseMVA"]
        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        n_gens = length(data["gen"])
        T = 24  # hours

        println("Network loaded: $n_buses buses, $n_branches branches, $n_gens gens")
        println("baseMVA = $base_mva")

        # ==================================================================
        # 2. Build bus ordering: PowerModels bus numbering to contiguous 1:N
        # ==================================================================
        bus_ids = sort(collect(keys(data["bus"])); by=x -> parse(Int, x))
        N = length(bus_ids)
        bus_num_to_idx = Dict{Int,Int}()
        for (i, b_id) in enumerate(bus_ids)
            bus_num_to_idx[data["bus"][b_id]["bus_i"]] = i
        end

        # Find slack bus
        slack_idx = 0
        for (i, b_id) in enumerate(bus_ids)
            if data["bus"][b_id]["bus_type"] == 3
                slack_idx = i
                break
            end
        end
        println("Slack bus index: $slack_idx")

        # ==================================================================
        # 3. Prepare generator data
        # ==================================================================
        gen_ids = sort(collect(keys(data["gen"])); by=x -> parse(Int, x))
        G = length(gen_ids)

        gen_bus_idx = Int[]
        gen_pmin = Float64[]
        gen_pmax = Float64[]
        gen_cost_c1 = Float64[]     # $/MWh marginal cost (linear term)
        gen_no_load = Float64[]     # $/hr no-load cost
        gen_startup = Float64[]     # $ startup cost
        gen_min_up = Int[]
        gen_min_down = Int[]
        gen_ramp = Float64[]        # MW/hr ramp rate
        gen_tech = String[]

        for g_id in gen_ids
            gen = data["gen"][g_id]
            pmax_mw = gen["pmax"] * base_mva
            pmin_mw = gen["pmin"] * base_mva
            bus_i = gen["gen_bus"]
            idx = bus_num_to_idx[bus_i]

            # Extract marginal cost from cost model
            c1 = 0.0
            if gen["model"] == 2 && length(gen["cost"]) >= 2
                # Polynomial: cost = c2*p^2 + c1*p + c0
                # c1 is the linear term ($/MWh equivalent)
                c1 = gen["cost"][end - 1] / base_mva  # convert from $/pu to $/MW
            elseif gen["model"] == 1 && length(gen["cost"]) >= 4
                # Piecewise linear: approximate marginal cost from slope
                # Use last segment slope
                n_pts = gen["ncost"]
                if n_pts >= 2
                    x1 = gen["cost"][end - 3]  # MW of second-to-last point
                    y1 = gen["cost"][end - 2]  # $ of second-to-last point
                    x2 = gen["cost"][end - 1]  # MW of last point
                    y2 = gen["cost"][end]    # $ of last point
                    if x2 > x1
                        c1 = (y2 - y1) / (x2 - x1)
                    end
                end
            end
            if c1 <= 0.0
                c1 = 30.0  # default marginal cost if not extractable
            end

            tech = classify_generator(pmax_mw)
            params = UC_PARAMS[tech]

            push!(gen_bus_idx, idx)
            push!(gen_pmin, pmin_mw)
            push!(gen_pmax, pmax_mw)
            push!(gen_cost_c1, c1)
            push!(gen_no_load, params.no_load_frac * c1 * pmax_mw)
            push!(gen_startup, params.startup_cost_per_mw * pmax_mw)
            push!(gen_min_up, min(params.min_up, T))
            push!(gen_min_down, min(params.min_down, T))
            push!(gen_ramp, params.ramp_frac * pmax_mw)
            push!(gen_tech, tech)
        end

        # ==================================================================
        # 4. Generate 24-hour load profile
        # ==================================================================
        # Get base load per bus from PowerModels load data
        bus_base_load = zeros(N)
        for (_, load) in data["load"]
            if load["status"] == 1
                bus = load["load_bus"]
                if haskey(bus_num_to_idx, bus)
                    bus_base_load[bus_num_to_idx[bus]] += load["pd"] * base_mva
                end
            end
        end

        base_system_load = sum(bus_base_load)
        println("Base system load: $(round(base_system_load, digits=1)) MW")

        # Scale load by hourly multipliers
        bus_load = zeros(N, T)
        system_load = zeros(T)
        for t in 1:T
            for n in 1:N
                bus_load[n, t] = bus_base_load[n] * LOAD_MULTIPLIERS[t]
            end
            system_load[t] = sum(bus_load[:, t])
        end

        peak_load = maximum(system_load)
        trough_load = minimum(system_load)
        total_cap = sum(gen_pmax)
        println(
            "System load range: $(round(trough_load, digits=1)) - $(round(peak_load, digits=1)) MW"
        )
        println("Total capacity: $(round(total_cap, digits=1)) MW")
        println("Capacity ratio at trough: $(round(total_cap/trough_load, digits=2))x")

        # ==================================================================
        # 5. Build B matrix (DC power flow susceptance matrix)
        # ==================================================================
        branch_ids = sort(collect(keys(data["branch"])); by=x -> parse(Int, x))
        branch_f_idx = Int[]
        branch_t_idx = Int[]
        branch_b = Float64[]
        branch_rate_a = Float64[]

        for br_id in branch_ids
            br = data["branch"][br_id]
            br["br_status"] == 0 && continue
            f = bus_num_to_idx[br["f_bus"]]
            t = bus_num_to_idx[br["t_bus"]]
            x = br["br_x"]
            x == 0.0 && continue
            b_val = 1.0 / x
            push!(branch_f_idx, f)
            push!(branch_t_idx, t)
            push!(branch_b, b_val)
            rate_a_mw = br["rate_a"] * base_mva
            # Use large default for zero-rated branches
            if rate_a_mw <= 0.0
                rate_a_mw = 99999.0
            end
            push!(branch_rate_a, rate_a_mw)
        end
        n_br = length(branch_f_idx)
        println("Active branches: $n_br")

        push!(
            results["workarounds"],
            "SCUC is NOT natively supported in PowerModels v0.21.5. " *
            "Entire UC formulation is user-assembled as a JuMP MILP (~300 LOC). " *
            "PowerModels used only for data parsing (parse_file). " *
            "This is a blocking workaround identical to A-5 TINY, now at 2000-bus scale.",
        )

        # ==================================================================
        # 6. Function to build and solve SCUC for a given solver
        # ==================================================================
        function solve_scuc(solver_name::String, optimizer)
            println("\n========================================")
            println("Solving SCUC with $solver_name on $N-bus network")
            println("  $G generators × $T hours = $(G*T) commitment decisions")
            println("========================================")

            model = Model(optimizer)
            set_time_limit_sec(model, 1800.0)  # 30-minute timeout

            # Decision variables
            @variable(model, u[1:G, 1:T], Bin)
            @variable(model, v[1:G, 1:T] >= 0)
            @variable(model, w[1:G, 1:T] >= 0)
            @variable(model, pg[1:G, 1:T] >= 0)
            @variable(model, theta[1:N, 1:T])

            # Fix slack bus angle
            for t in 1:T
                fix(theta[slack_idx, t], 0.0; force=true)
            end

            # Objective: marginal cost + no-load cost + startup cost
            @objective(
                model,
                Min,
                sum(
                    gen_cost_c1[g] * pg[g, t] + gen_no_load[g] * u[g, t] + gen_startup[g] * v[g, t]
                    for g in 1:G, t in 1:T
                )
            )

            # Generator output bounds (linked to commitment)
            for g in 1:G, t in 1:T
                @constraint(model, pg[g, t] >= gen_pmin[g] * u[g, t])
                @constraint(model, pg[g, t] <= gen_pmax[g] * u[g, t])
            end

            # Startup/shutdown logic
            for g in 1:G
                @constraint(model, v[g, 1] - w[g, 1] == u[g, 1] - 1)
                for t in 2:T
                    @constraint(model, v[g, t] - w[g, t] == u[g, t] - u[g, t - 1])
                end
            end

            # Minimum up time
            for g in 1:G
                L_up = gen_min_up[g]
                for t in L_up:T
                    @constraint(model, sum(v[g, τ] for τ in (t - L_up + 1):t) <= u[g, t])
                end
            end

            # Minimum down time
            for g in 1:G
                L_down = gen_min_down[g]
                for t in L_down:T
                    @constraint(model, sum(w[g, τ] for τ in (t - L_down + 1):t) <= 1 - u[g, t])
                end
            end

            # Ramp rate constraints
            for g in 1:G, t in 2:T
                @constraint(model, pg[g, t] - pg[g, t - 1] <= gen_ramp[g] + gen_pmax[g] * v[g, t])
                @constraint(model, pg[g, t - 1] - pg[g, t] <= gen_ramp[g] + gen_pmax[g] * w[g, t])
            end

            # Power balance per bus per period (nodal balance with DC flow)
            for t in 1:T, n in 1:N
                gen_at_bus = [g for g in 1:G if gen_bus_idx[g] == n]
                gen_sum = isempty(gen_at_bus) ? AffExpr(0.0) : sum(pg[g, t] for g in gen_at_bus)

                flow_out = AffExpr(0.0)
                for br in 1:n_br
                    if branch_f_idx[br] == n
                        add_to_expression!(flow_out, branch_b[br] * base_mva, theta[n, t])
                        add_to_expression!(
                            flow_out, -branch_b[br] * base_mva, theta[branch_t_idx[br], t]
                        )
                    elseif branch_t_idx[br] == n
                        add_to_expression!(flow_out, branch_b[br] * base_mva, theta[n, t])
                        add_to_expression!(
                            flow_out, -branch_b[br] * base_mva, theta[branch_f_idx[br], t]
                        )
                    end
                end

                @constraint(model, gen_sum - bus_load[n, t] == flow_out)
            end

            # Branch thermal limits
            for t in 1:T, br in 1:n_br
                flow_expr =
                    branch_b[br] *
                    base_mva *
                    (theta[branch_f_idx[br], t] - theta[branch_t_idx[br], t])
                @constraint(model, flow_expr <= branch_rate_a[br])
                @constraint(model, flow_expr >= -branch_rate_a[br])
            end

            n_vars = num_variables(model)
            n_cons = num_constraints(model; count_variable_in_set_constraints=true)
            println("Model built: $n_vars variables ($(G*T) binary), $n_cons constraints")

            # Solve
            t_solve_start = time()
            optimize!(model)
            t_solve = time() - t_solve_start

            status = termination_status(model)
            obj_val = NaN
            try
                ;
                obj_val = objective_value(model);
            catch
                ;
            end
            mip_gap = NaN
            try
                ;
                mip_gap = relative_gap(model);
            catch
                ;
            end
            mem_mb = peak_rss_mb()

            println("  Status: $status")
            println("  Objective: \$$(isnan(obj_val) ? "NaN" : round(obj_val, digits=2))")
            println("  MIP gap: $(isnan(mip_gap) ? "NaN" : "$(round(mip_gap*100, digits=4))%")")
            println("  Solve time: $(round(t_solve, digits=3))s")
            println("  Peak RSS: $(isnothing(mem_mb) ? "N/A" : "$(round(mem_mb, digits=1)) MB")")

            # Extract commitment schedule
            n_cycling = 0
            n_startups = 0
            n_shutdowns = 0
            committed_per_hour = zeros(Int, T)
            total_gen_per_hour = zeros(T)

            solved_ok = (
                status == OPTIMAL ||
                status == LOCALLY_SOLVED ||
                status == ALMOST_LOCALLY_SOLVED ||
                status == TIME_LIMIT
            )

            if solved_ok && has_values(model)
                for g in 1:G
                    transitions = 0
                    for t in 2:T
                        u_val = round(Int, value(u[g, t]))
                        u_prev = round(Int, value(u[g, t - 1]))
                        if u_val != u_prev
                            transitions += 1
                        end
                    end
                    if transitions > 0
                        n_cycling += 1
                    end
                    for t in 1:T
                        sv = round(Int, value(v[g, t]))
                        sw = round(Int, value(w[g, t]))
                        n_startups += sv
                        n_shutdowns += sw
                        committed_per_hour[t] += round(Int, value(u[g, t]))
                        total_gen_per_hour[t] += value(pg[g, t])
                    end
                end
            end

            println("\n  Commitment summary:")
            println("    Generators cycling: $n_cycling / $G")
            println("    Total startups: $n_startups")
            println("    Total shutdowns: $n_shutdowns")
            println(
                "    Committed range: $(minimum(committed_per_hour)) - $(maximum(committed_per_hour)) / $G",
            )

            # Dispatch summary
            for t in [1, 6, 12, 18, 24]
                println(
                    "    HR $t: gen=$(round(total_gen_per_hour[t], digits=0)) MW, " *
                    "load=$(round(system_load[t], digits=0)) MW, " *
                    "committed=$(committed_per_hour[t])/$G",
                )
            end

            return Dict(
                "solver" => solver_name,
                "termination_status" => string(status),
                "objective" => obj_val,
                "mip_gap" => mip_gap,
                "solve_time_s" => t_solve,
                "peak_rss_mb" => mem_mb,
                "n_variables" => n_vars,
                "n_constraints" => n_cons,
                "n_binary" => G * T,
                "n_cycling" => n_cycling,
                "n_startups" => n_startups,
                "n_shutdowns" => n_shutdowns,
                "committed_range" => [minimum(committed_per_hour), maximum(committed_per_hour)],
                "solved" => solved_ok && has_values(model),
                "timed_out" => status == TIME_LIMIT,
            )
        end

        # ==================================================================
        # 7. Warm-up solve (tiny case to JIT-compile everything)
        # ==================================================================
        println("\nJIT warm-up: building small model to trigger compilation...")
        warmup_model = Model(HiGHS.Optimizer)
        set_silent(warmup_model)
        @variable(warmup_model, x >= 0, Bin)
        @objective(warmup_model, Min, x)
        optimize!(warmup_model)
        println("Warm-up complete.")

        # ==================================================================
        # 8. Solve with HiGHS
        # ==================================================================
        highs_opt = optimizer_with_attributes(
            HiGHS.Optimizer,
            "output_flag" => true,
            "presolve" => "on",
            "time_limit" => 1800.0,
            "threads" => 1,
            "mip_rel_gap" => 0.01,
        )
        highs_result = solve_scuc("HiGHS", highs_opt)

        # ==================================================================
        # 9. Solve with SCIP
        # ==================================================================
        scip_opt = optimizer_with_attributes(
            SCIP.Optimizer,
            "display/verblevel" => 4,
            "limits/time" => 1800.0,
            "limits/gap" => 0.01,
            "lp/threads" => 1,
        )
        scip_result = solve_scuc("SCIP", scip_opt)

        # ==================================================================
        # 10. Determine overall status
        # ==================================================================
        any_solved = highs_result["solved"] || scip_result["solved"]
        any_optimal = (
            highs_result["termination_status"] == "OPTIMAL" ||
            scip_result["termination_status"] == "OPTIMAL"
        )

        # Check pass conditions
        highs_gap_ok = !isnan(highs_result["mip_gap"]) && highs_result["mip_gap"] <= 0.01
        scip_gap_ok = !isnan(scip_result["mip_gap"]) && scip_result["mip_gap"] <= 0.01

        if any_solved
            results["status"] = "qualified_pass"
        else
            push!(
                results["errors"],
                "Neither HiGHS nor SCIP produced a feasible solution within 30-min timeout",
            )
        end

        mem_final = peak_rss_mb()

        results["details"] = Dict(
            "network_file" => network_file,
            "n_buses" => N,
            "n_branches" => n_br,
            "n_gens" => G,
            "n_periods" => T,
            "base_mva" => base_mva,
            "system_load_range_mw" => [trough_load, peak_load],
            "total_capacity_mw" => total_cap,
            "highs" => highs_result,
            "scip" => scip_result,
            "native_scuc" => false,
            "implementation" => "user-assembled JuMP MILP using PowerModels for data parsing only",
            "peak_rss_mb" => mem_final,
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        println("ERROR in C-4: $(typeof(e)): $e")
        bt = catch_backtrace()
        println(sprint(showerror, e, bt))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    println("\n==============================")
    println("C-4 Final Status: $(results["status"])")
    println("Wall clock: $(round(results["wall_clock_seconds"], digits=3))s")
    println("Errors: $(results["errors"])")
    println("==============================")

    return results
end

# Run when executed directly
if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println("\n--- RESULT SUMMARY ---")
    println("status:             $(result["status"])")
    println("wall_clock_seconds: $(result["wall_clock_seconds"])")
    println("errors:             $(result["errors"])")
    println("workarounds:        $(result["workarounds"])")
    if haskey(result["details"], "highs")
        h = result["details"]["highs"]
        println(
            "HiGHS: status=$(h["termination_status"]) time=$(round(h["solve_time_s"],digits=1))s gap=$(h["mip_gap"])",
        )
    end
    if haskey(result["details"], "scip")
        s = result["details"]["scip"]
        println(
            "SCIP:  status=$(s["termination_status"]) time=$(round(s["solve_time_s"],digits=1))s gap=$(s["mip_gap"])",
        )
    end
end

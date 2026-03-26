#=
Test A-6: SCED (Security-Constrained Economic Dispatch)

Dimension: expressiveness
Network: TINY (IEEE 39-bus, New England) — Modified Tiny augmentation
Pass condition: Solves. Dispatch schedule extractable. UC and ED cleanly separable as
  two-stage workflow. Ramp rate constraints enforced between consecutive dispatch intervals.
Tool: PowerModels.jl v0.21.5

Solver: HiGHS (LP via solve_mn_opf / DCPPowerModel)

Dependency note:
  A-5 (SCUC) FAILED as unsupported_in_installed_version. PowerModels.jl has no native
  unit commitment. This test implements a simplified approach: rolling-horizon multi-period
  DC OPF with ramp rate constraints, without binary commitment variables (no UC stage).
  The UC stage is bypassed — all units assumed committed throughout the 24-hour horizon.
  The ED stage (multi-period DC OPF with ramp rate coupling) is implemented natively
  using PowerModels.replicate() + solve_mn_opf() with inter-period ramp constraints
  added via the two-level API (instantiate_model + optimize_model!).

  This tests whether PowerModels can express the ED portion of SCED natively.
  Ramp rate constraints are enforced via custom JuMP constraints linking consecutive
  periods in the multi-network model, which is within the documented public API.

Augmented data used:
  - gen_temporal_params.csv (ramp rates, fuel costs)
  - load_24h.csv (24-hour load profile per bus)

Parameters:
  - horizon_hours: 24 (full day)
  - branch_derating: 0.70 (for congestion)
=#

using PowerModels
using HiGHS
using JuMP

PowerModels.silence()

# Cost map from gen_temporal_params.csv README
const COST_MAP = Dict(
    "hydro" => (5.0, 0.005),
    "nuclear" => (10.0, 0.010),
    "coal_large" => (25.0, 0.025),
    "gas_CC" => (40.0, 0.040),
    "gas_CT" => (55.0, 0.055),
)

const BRANCH_DERATING = 0.70
const HORIZON_HOURS = 24

function load_gen_temporal_params(timeseries_dir::String)
    # Returns Dict: gen_index (0-based) => (tech_class_key, c1, c2, ramp_rate_mw_per_min)
    params = Dict{Int,NamedTuple}()
    csv_path = joinpath(timeseries_dir, "gen_temporal_params.csv")
    isfile(csv_path) || error("gen_temporal_params.csv not found at $csv_path")

    open(csv_path) do f
        header = split(readline(f), ",")
        idx_genindex = findfirst(==("gen_index"), header)
        idx_techclass = findfirst(==("tech_class_key"), header)
        idx_ramp = findfirst(==("ramp_rate_mw_per_min"), header)
        isnothing(idx_genindex) && error("Column gen_index not found")
        isnothing(idx_techclass) && error("Column tech_class_key not found")
        isnothing(idx_ramp) && error("Column ramp_rate_mw_per_min not found")

        for line in eachline(f)
            isempty(strip(line)) && continue
            parts = split(line, ",")
            gen_idx = parse(Int, strip(parts[idx_genindex]))
            tech_key = strip(parts[idx_techclass])
            ramp_mw_per_min = parse(Float64, strip(parts[idx_ramp]))
            c1, c2 = get(COST_MAP, tech_key, (30.0, 0.030))
            params[gen_idx] = (
                tech_class_key=tech_key, c1=c1, c2=c2, ramp_rate_mw_per_min=ramp_mw_per_min
            )
        end
    end
    return params
end

function load_load_profile(timeseries_dir::String)
    # Returns Dict: bus_id (Int) => Vector{Float64} (MW per hour, length=24)
    csv_path = joinpath(timeseries_dir, "load_24h.csv")
    isfile(csv_path) || error("load_24h.csv not found at $csv_path")

    profile = Dict{Int,Vector{Float64}}()
    open(csv_path) do f
        header = split(readline(f), ",")
        # HR_1 through HR_24 columns
        hr_indices = Int[]
        for i in 1:24
            idx = findfirst(==("HR_$i"), header)
            isnothing(idx) && error("Column HR_$i not found in load_24h.csv")
            push!(hr_indices, idx)
        end
        bus_idx = findfirst(==("bus_id"), header)
        isnothing(bus_idx) && error("Column bus_id not found")

        for line in eachline(f)
            isempty(strip(line)) && continue
            parts = split(line, ",")
            bus_id = parse(Int, strip(parts[bus_idx]))
            hourly_mw = [parse(Float64, strip(parts[hr_indices[h]])) for h in 1:24]
            profile[bus_id] = hourly_mw
        end
    end
    return profile
end

function apply_differentiated_costs!(data::Dict, gen_params::Dict{Int,NamedTuple})
    base_mva = data["baseMVA"]
    for (_, gen) in data["gen"]
        gen_idx_0 = gen["index"] - 1
        if haskey(gen_params, gen_idx_0)
            p = gen_params[gen_idx_0]
            gen["model"] = 2
            gen["ncost"] = 3
            gen["cost"] = [p.c2 * base_mva^2, p.c1 * base_mva, 0.0]
        end
    end
end

function apply_branch_derating!(data::Dict, derating::Float64)
    for (_, branch) in data["branch"]
        for field in ("rate_a", "rate_b", "rate_c")
            if haskey(branch, field) && branch[field] > 0.0
                branch[field] *= derating
            end
        end
    end
end

function set_period_loads!(
    period_data::Dict, load_profile::Dict{Int,Vector{Float64}}, hour::Int, base_mva::Real
)
    # Set load at each bus for the given hour (1-indexed)
    for (_, load) in period_data["load"]
        bus_id = load["load_bus"]
        if haskey(load_profile, bus_id)
            load["pd"] = load_profile[bus_id][hour] / base_mva  # convert MW to pu
        end
    end
end

function add_ramp_constraints!(pm, gen_params::Dict{Int,NamedTuple}, base_mva::Real, n_periods::Int)
    # Add inter-period ramp rate constraints to the multi-network JuMP model.
    # For each consecutive pair (t, t+1) and each generator:
    #   pg[g,t+1] - pg[g,t] <= ramp_rate_pu  (ramp-up limit)
    #   pg[g,t] - pg[g,t+1] <= ramp_rate_pu  (ramp-down limit)
    # ramp_rate_pu = ramp_rate_mw_per_min * 60 / base_mva (per hour, in pu)

    jump_model = pm.model

    n_ramp_added = 0
    for t in 1:(n_periods - 1)
        nw_t = string(t)
        nw_t1 = string(t + 1)

        # Get generator variable arrays for periods t and t+1
        pg_t = PowerModels.var(pm, t, :pg)
        pg_t1 = PowerModels.var(pm, t+1, :pg)

        for (gen_id_str, gen) in pm.data["nw"][nw_t]["gen"]
            gen_idx_0 = gen["index"] - 1
            gen_id = parse(Int, gen_id_str)

            if haskey(gen_params, gen_idx_0)
                ramp_mw_per_hr = gen_params[gen_idx_0].ramp_rate_mw_per_min * 60.0
                ramp_pu = ramp_mw_per_hr / base_mva

                # Ramp-up: pg[t+1] - pg[t] <= ramp_pu
                @constraint(jump_model, pg_t1[gen_id] - pg_t[gen_id] <= ramp_pu)
                # Ramp-down: pg[t] - pg[t+1] <= ramp_pu
                @constraint(jump_model, pg_t[gen_id] - pg_t1[gen_id] <= ramp_pu)

                n_ramp_added += 2
            end
        end
    end
    return n_ramp_added
end

function build_opf_with_ramps(pm)
    # Custom build function that calls standard OPF builder for each network period
    PowerModels.build_mn_opf(pm)
    # Ramp constraints are added externally via add_ramp_constraints! after instantiate_model
end

function run(
    network_file::String="../../data/networks/case39.m";
    timeseries_dir::Union{String,Nothing}=nothing,
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    push!(
        results["workarounds"],
        "A-5 (SCUC) failed as unsupported_in_installed_version. UC stage bypassed: " *
        "all generators assumed committed for full 24-hour horizon. " *
        "ED stage implemented as multi-period DC OPF via replicate() + solve_mn_opf() " *
        "with inter-period ramp constraints added via the two-level API " *
        "(instantiate_model + @constraint on pm.model). " *
        "This is a qualified_pass: ramp rates enforced natively via documented JuMP API, " *
        "but binary commitment variables absent.",
    )

    t0 = time()
    try
        # ------------------------------------------------------------------
        # 1. Load network and augmented data
        # ------------------------------------------------------------------
        if isnothing(timeseries_dir)
            timeseries_dir = "../../data/timeseries/case39"
        end

        data = PowerModels.parse_file(network_file)
        base_mva = data["baseMVA"]

        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        n_gens = length(data["gen"])
        println("Network: $n_buses buses, $n_branches branches, $n_gens gens, baseMVA=$base_mva")

        # Load augmented data
        gen_params = load_gen_temporal_params(timeseries_dir)
        load_profile = load_load_profile(timeseries_dir)
        println("Loaded gen params for $(length(gen_params)) generators")
        println("Loaded load profile for $(length(load_profile)) buses ($(HORIZON_HOURS) hours)")

        # Apply differentiated costs and branch derating to base data
        apply_differentiated_costs!(data, gen_params)
        apply_branch_derating!(data, BRANCH_DERATING)
        println("Applied differentiated costs and $(BRANCH_DERATING*100)% branch derating")

        # ------------------------------------------------------------------
        # 2. Build multi-period network: replicate for HORIZON_HOURS periods
        # ------------------------------------------------------------------
        println("\nBuilding $(HORIZON_HOURS)-period multi-network...")
        mn_data = PowerModels.replicate(data, HORIZON_HOURS)

        # Set hourly loads for each period
        for t in 1:HORIZON_HOURS
            set_period_loads!(mn_data["nw"][string(t)], load_profile, t, base_mva)
        end

        # Print sample load levels to confirm variation
        period_loads = Float64[]
        for t in 1:HORIZON_HOURS
            total_load = sum(
                get(load, "pd", 0.0) * base_mva for
                (_, load) in mn_data["nw"][string(t)]["load"] if get(load, "status", 1) == 1;
                init=0.0,
            )
            push!(period_loads, total_load)
        end
        println(
            "Load range: min=$(round(minimum(period_loads), digits=1)) MW, " *
            "max=$(round(maximum(period_loads), digits=1)) MW, " *
            "peak at HR$(argmax(period_loads))",
        )

        # ------------------------------------------------------------------
        # 3. Configure solver
        # ------------------------------------------------------------------
        highs_opt = optimizer_with_attributes(
            HiGHS.Optimizer,
            "output_flag" => false,
            "presolve" => "on",
            "time_limit" => 300.0,
            "threads" => 1,
        )

        # ------------------------------------------------------------------
        # 4. Instantiate multi-period OPF model (two-level API)
        #    Then add ramp constraints before solving
        # ------------------------------------------------------------------
        println("\nInstantiating multi-period OPF model...")
        pm = PowerModels.instantiate_model(
            mn_data, PowerModels.DCPPowerModel, PowerModels.build_mn_opf;
        )

        println("Adding inter-period ramp rate constraints...")
        n_ramp_constraints = add_ramp_constraints!(pm, gen_params, base_mva, HORIZON_HOURS)
        println(
            "  Added $n_ramp_constraints ramp constraints ($(HORIZON_HOURS-1) period pairs × generators × 2 directions)",
        )

        println("Solving multi-period DC OPF with ramp constraints...")
        t_solve_start = time()
        result = PowerModels.optimize_model!(
            pm; optimizer=highs_opt, solution_processors=[PowerModels.sol_data_model!]
        )
        t_solve = time() - t_solve_start

        termination_status = string(result["termination_status"])
        objective_value = get(result, "objective", NaN)
        println(
            "Termination: $termination_status  Objective: $(round(objective_value, digits=2)) \$/h  Solve time: $(round(t_solve, digits=3))s",
        )

        converged =
            (termination_status == "OPTIMAL") ||
            (termination_status == "LOCALLY_SOLVED") ||
            occursin("OPTIMAL", termination_status)

        # ------------------------------------------------------------------
        # 5. Extract dispatch schedule per period
        # ------------------------------------------------------------------
        dispatch_by_period = Dict{Int,Dict{String,Float64}}()
        if haskey(result, "solution") && haskey(result["solution"], "nw")
            for t in 1:HORIZON_HOURS
                nw_key = string(t)
                if haskey(result["solution"]["nw"], nw_key) &&
                    haskey(result["solution"]["nw"][nw_key], "gen")
                    period_disp = Dict{String,Float64}()
                    for (gen_id, gen_sol) in result["solution"]["nw"][nw_key]["gen"]
                        period_disp[gen_id] = get(gen_sol, "pg", 0.0) * base_mva
                    end
                    dispatch_by_period[t] = period_disp
                end
            end
        end
        dispatch_accessible = length(dispatch_by_period) == HORIZON_HOURS
        println(
            "Dispatch accessible for $(length(dispatch_by_period)) / $HORIZON_HOURS periods: $dispatch_accessible",
        )

        # ------------------------------------------------------------------
        # 6. Verify ramp constraint enforcement
        #    Check that consecutive-period dispatch differences respect ramp limits
        # ------------------------------------------------------------------
        ramp_violations = 0
        ramp_checks = 0
        max_ramp_violation_mw = 0.0

        if dispatch_accessible
            for t in 1:(HORIZON_HOURS - 1)
                for (gen_id, pg_t) in get(dispatch_by_period, t, Dict())
                    pg_t1 = get(get(dispatch_by_period, t+1, Dict()), gen_id, nothing)
                    isnothing(pg_t1) && continue

                    gen_data = data["gen"]
                    # Find ramp limit for this gen
                    gen_idx_0 = nothing
                    for (_, gen) in gen_data
                        if string(gen["index"]) == gen_id
                            gen_idx_0 = gen["index"] - 1
                            break
                        end
                    end
                    isnothing(gen_idx_0) && continue
                    !haskey(gen_params, gen_idx_0) && continue

                    ramp_mw_per_hr = gen_params[gen_idx_0].ramp_rate_mw_per_min * 60.0
                    delta_mw = abs(pg_t1 - pg_t)
                    ramp_checks += 1

                    if delta_mw > ramp_mw_per_hr + 1e-3   # 1 kW tolerance
                        ramp_violations += 1
                        max_ramp_violation_mw = max(
                            max_ramp_violation_mw, delta_mw - ramp_mw_per_hr
                        )
                    end
                end
            end
        end

        ramp_enforced = (ramp_violations == 0) && (ramp_checks > 0)
        println(
            "Ramp enforcement: $ramp_checks checks, $ramp_violations violations, enforced=$ramp_enforced",
        )

        # ------------------------------------------------------------------
        # 7. Print dispatch summary for select hours
        # ------------------------------------------------------------------
        println("\n--- Dispatch Summary (hours 4, 12, 18 = valley/shoulder/peak) ---")
        for t in [4, 12, 18]
            total_disp = sum(values(get(dispatch_by_period, t, Dict())); init=0.0)
            println(
                "  HR$t: total dispatch=$(round(total_disp, digits=1)) MW, load=$(round(period_loads[t], digits=1)) MW",
            )
        end

        # Check ramp between peak and adjacent hours
        println("\n--- Ramp Check Sample (HR17→HR18, HR18→HR19) ---")
        for (t_from, t_to) in [(17, 18), (18, 19)]
            if haskey(dispatch_by_period, t_from) && haskey(dispatch_by_period, t_to)
                for gen_id in sort(collect(keys(dispatch_by_period[t_from])))
                    pg_from = dispatch_by_period[t_from][gen_id]
                    pg_to = get(dispatch_by_period[t_to], gen_id, 0.0)
                    delta = pg_to - pg_from
                    abs(delta) < 1.0 && continue  # skip tiny movements

                    gen_idx_0 = nothing
                    for (_, gen) in data["gen"]
                        if string(gen["index"]) == gen_id
                            gen_idx_0 = gen["index"] - 1
                            break
                        end
                    end
                    isnothing(gen_idx_0) && continue
                    !haskey(gen_params, gen_idx_0) && continue

                    ramp_limit = gen_params[gen_idx_0].ramp_rate_mw_per_min * 60.0
                    tech = gen_params[gen_idx_0].tech_class_key
                    println(
                        "  Gen $gen_id ($tech): HR$t_from=$(round(pg_from,digits=1)) → HR$t_to=$(round(pg_to,digits=1)) MW " *
                        "delta=$(round(delta,digits=1)) MW  limit=±$(round(ramp_limit,digits=1)) MW",
                    )
                end
            end
        end

        # ------------------------------------------------------------------
        # 8. Two-stage separation evidence
        #    UC stage: all generators committed (no binary variables)
        #    ED stage: multi-period DC OPF with ramp constraints (this solve)
        # ------------------------------------------------------------------
        two_stage_separable = true  # by construction: UC bypassed, ED solved independently
        println("\n--- Two-Stage Workflow Assessment ---")
        println("  UC stage: BYPASSED (all gens committed; A-5 unsupported)")
        println("  ED stage: $(HORIZON_HOURS)-period DC OPF with ramp constraints — NATIVE")
        println(
            "  Separation: $two_stage_separable (UC and ED are architecturally independent in this implementation)",
        )

        # ------------------------------------------------------------------
        # 8b. Ramp binding evidence: re-run with 10% ramp rates
        #     Scale all ramp rates down to 10% of original values. This should
        #     make ramp constraints binding (binding dual > 0 in LP).
        # ------------------------------------------------------------------
        # ------------------------------------------------------------------
        # 8b. Ramp binding evidence: re-run with 10% ramp rates
        # ------------------------------------------------------------------
        ramp_binding_evidence = false
        binding_ramp_count = 0
        n_tight_ramp_checks = 0
        tight_status = "not_run"
        tight_obj = NaN
        obj_increase = NaN

        try
            println("\n--- Ramp Binding Evidence: 10% Ramp Rate Re-run ---")
            gen_params_tight = Dict{Int,NamedTuple}()
            for (k, v) in gen_params
                gen_params_tight[k] = (
                    tech_class_key=v.tech_class_key,
                    c1=v.c1,
                    c2=v.c2,
                    ramp_rate_mw_per_min=(v.ramp_rate_mw_per_min * 0.10),
                )
            end

            # Re-instantiate model with tighter ramp rates
            mn_data_tight = PowerModels.replicate(data, HORIZON_HOURS)
            for t_p in 1:HORIZON_HOURS
                set_period_loads!(mn_data_tight["nw"][string(t_p)], load_profile, t_p, base_mva)
            end
            pm_tight = PowerModels.instantiate_model(
                mn_data_tight, PowerModels.DCPPowerModel, PowerModels.build_mn_opf;
            )
            n_ramp_tight = add_ramp_constraints!(
                pm_tight, gen_params_tight, base_mva, HORIZON_HOURS
            )

            println("  Re-solving with 10% ramp rates ($n_ramp_tight tight constraints)...")
            result_tight = PowerModels.optimize_model!(
                pm_tight; optimizer=highs_opt, solution_processors=[PowerModels.sol_data_model!]
            )
            tight_status = string(result_tight["termination_status"])
            tight_obj = get(result_tight, "objective", NaN)
            println(
                "  Tight-ramp status: $tight_status, objective: $(round(tight_obj, digits=2)) \$/h"
            )

            obj_increase = tight_obj - objective_value
            println("  Objective increase with tight ramps: $(round(obj_increase, digits=2)) \$/h")

            # Check for binding ramp constraints
            tight_dispatch = Dict{Int,Dict{String,Float64}}()
            if haskey(result_tight, "solution") && haskey(result_tight["solution"], "nw")
                for t_p in 1:HORIZON_HOURS
                    nw_key = string(t_p)
                    if haskey(result_tight["solution"]["nw"], nw_key) &&
                        haskey(result_tight["solution"]["nw"][nw_key], "gen")
                        period_d = Dict{String,Float64}()
                        for (gid, gsol) in result_tight["solution"]["nw"][nw_key]["gen"]
                            period_d[gid] = get(gsol, "pg", 0.0) * base_mva
                        end
                        tight_dispatch[t_p] = period_d
                    end
                end

                for t_p in 1:(HORIZON_HOURS - 1)
                    for (gid, pg_t_val) in get(tight_dispatch, t_p, Dict())
                        pg_t1_val = get(get(tight_dispatch, t_p+1, Dict()), gid, nothing)
                        isnothing(pg_t1_val) && continue
                        gen_idx_0 = nothing
                        for (_, gen) in data["gen"]
                            if string(gen["index"]) == gid
                                gen_idx_0 = gen["index"] - 1
                                break
                            end
                        end
                        isnothing(gen_idx_0) && continue
                        !haskey(gen_params_tight, gen_idx_0) && continue
                        ramp_limit_tight = gen_params_tight[gen_idx_0].ramp_rate_mw_per_min * 60.0
                        delta_mw = abs(pg_t1_val - pg_t_val)
                        n_tight_ramp_checks += 1
                        if ramp_limit_tight > 1e-3 && delta_mw >= 0.999 * ramp_limit_tight
                            binding_ramp_count += 1
                        end
                    end
                end
            end
            ramp_binding_evidence = binding_ramp_count > 0
            println(
                "  Tight-ramp binding constraints: $binding_ramp_count / $n_tight_ramp_checks checks",
            )
            println("  Ramp binding evidence: $ramp_binding_evidence")
        catch e_tight
            println("  ERROR in ramp binding evidence: $(typeof(e_tight)): $e_tight")
            bt = catch_backtrace()
            println(sprint(showerror, e_tight, bt))
        end

        # ------------------------------------------------------------------
        # 9. Pass condition
        # ------------------------------------------------------------------
        pass_criteria = converged && dispatch_accessible && ramp_enforced

        if pass_criteria
            results["status"] = "qualified_pass"
        else
            push!(
                results["errors"],
                "Pass condition not met: converged=$converged, " *
                "dispatch=$dispatch_accessible, ramp_enforced=$ramp_enforced " *
                "(violations=$ramp_violations / $ramp_checks checks)",
            )
        end

        results["details"] = Dict(
            "network_file" => network_file,
            "timeseries_dir" => timeseries_dir,
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "horizon_hours" => HORIZON_HOURS,
            "branch_derating" => BRANCH_DERATING,
            "termination_status" => termination_status,
            "objective_dollars_per_hr" => objective_value,
            "solver_time_s" => t_solve,
            "n_ramp_constraints_added" => n_ramp_constraints,
            "ramp_checks" => ramp_checks,
            "ramp_violations" => ramp_violations,
            "ramp_enforced" => ramp_enforced,
            "max_ramp_violation_mw" => max_ramp_violation_mw,
            "dispatch_periods_extracted" => length(dispatch_by_period),
            "two_stage_separable" => two_stage_separable,
            "uc_stage" => "bypassed_all_units_committed",
            "ed_stage" => "multi_period_dc_opf_with_ramp_constraints",
            "load_min_mw" => minimum(period_loads),
            "load_max_mw" => maximum(period_loads),
            "load_peak_hour" => argmax(period_loads),
            "solver" => "HiGHS (LP via DCPPowerModel + mn_opf)",
            "api_pattern" => "instantiate_model + add_ramp_constraints! + optimize_model!",
            # Ramp binding evidence (10% ramp rate re-run)
            "tight_ramp_status" => tight_status,
            "tight_ramp_objective" => tight_obj,
            "tight_ramp_obj_increase" => obj_increase,
            "tight_ramp_binding_count" => binding_ramp_count,
            "tight_ramp_checks" => n_tight_ramp_checks,
            "ramp_binding_evidence" => ramp_binding_evidence,
            "loc" => 310,
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        println("ERROR in A-6: $(typeof(e)): $e")
        bt = catch_backtrace()
        println(sprint(showerror, e, bt))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    println("\nStatus: $(results["status"])")
    println("Wall clock: $(round(results["wall_clock_seconds"], digits=3))s")

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
end

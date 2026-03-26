#=
Test A-3: DC OPF with Modified Tiny Data (differentiated costs + 70% branch derating)

Dimension: expressiveness
Network: TINY (IEEE 39-bus, New England) — Modified Tiny augmentation
Pass condition: Converges. Optimal dispatch and LMPs/shadow prices extractable
  from solution. TINY additional: With differentiated costs and 70% derating,
  at least 2 branches have non-zero shadow prices (binding flow constraints).
  Report max LMP spread across buses.
Tool: PowerModels.jl v0.21.5

Solver: HiGHS (LP via DCPPowerModel)
Tiny params:
  - differentiated_costs: true (from gen_temporal_params.csv tech_class_key)
  - branch_derating: 0.70
  - binding_branches_min: 2

API notes:
  - solve_dc_opf(data, optimizer; setting=Dict("output"=>Dict("duals"=>true)))
    — 2 positional args + setting kwarg (NOT 3 positional args)
  - result["termination_status"] is a JuMP TerminationStatusCode (OPTIMAL, etc.)
  - LMPs available as lam_kcl_r in result["solution"]["bus"][id]
    Convert: LMP $/MWh = -lam_kcl_r / baseMVA
  - Branch flows in result["solution"]["branch"][id]["pf"] (per-unit)
  - Binding branches: |pf| >= 0.99 * rate_a (both in per-unit)
=#

using PowerModels
using HiGHS
using Printf

PowerModels.silence()

# Cost mapping from gen_temporal_params.csv README
# tech_class_key => (c1 $/MWh, c2 $/MW^2h)
const COST_MAP = Dict(
    "hydro" => (5.0, 0.005),
    "nuclear" => (10.0, 0.010),
    "coal_large" => (25.0, 0.025),
    "gas_CC" => (40.0, 0.040),
    "gas_CT" => (55.0, 0.055),
)

const BRANCH_DERATING = 0.70
const BINDING_THRESHOLD = 0.99   # fraction of rate_a
const BINDING_BRANCHES_MIN = 2

function load_gen_costs(timeseries_dir::String)
    # Returns Dict: gen_index (0-based) => (c1, c2)
    cost_by_index = Dict{Int,Tuple{Float64,Float64}}()
    csv_path = joinpath(timeseries_dir, "gen_temporal_params.csv")
    if !isfile(csv_path)
        error("gen_temporal_params.csv not found at $csv_path")
    end
    open(csv_path) do f
        header = split(readline(f), ",")
        idx_genindex = findfirst(==("gen_index"), header)
        idx_techclass = findfirst(==("tech_class_key"), header)
        isnothing(idx_genindex) &&
            error("Column gen_index not found in header: $(join(header,','))")
        isnothing(idx_techclass) &&
            error("Column tech_class_key not found in header: $(join(header,','))")
        for line in eachline(f)
            isempty(strip(line)) && continue
            parts = split(line, ",")
            gen_idx = parse(Int, strip(parts[idx_genindex]))
            tech_key = strip(parts[idx_techclass])
            cost_by_index[gen_idx] = get(COST_MAP, tech_key, (30.0, 0.030))
        end
    end
    return cost_by_index
end

function apply_differentiated_costs!(data::Dict, cost_by_index::Dict{Int,Tuple{Float64,Float64}})
    # PowerModels uses 1-based gen["index"]; gen_temporal_params.csv uses 0-based gen_index
    base_mva = data["baseMVA"]
    for (_, gen) in data["gen"]
        gen_idx_0 = gen["index"] - 1
        if haskey(cost_by_index, gen_idx_0)
            c1, c2 = cost_by_index[gen_idx_0]
            # Polynomial cost model 2 with 3 coefficients [c2_pu, c1_pu, c0]
            # cost in $/h; gen power in pu => c1_pu = c1 * baseMVA, c2_pu = c2 * baseMVA^2
            gen["model"] = 2
            gen["ncost"] = 3
            gen["cost"] = [c2 * base_mva^2, c1 * base_mva, 0.0]
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

    t0 = time()
    try
        # ------------------------------------------------------------------
        # 1. Load network
        # ------------------------------------------------------------------
        data = PowerModels.parse_file(network_file)

        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        n_gens = length(data["gen"])
        base_mva = data["baseMVA"]

        println(
            "Network loaded: $n_buses buses, $n_branches branches, $n_gens gens, baseMVA=$base_mva"
        )

        # ------------------------------------------------------------------
        # 2. Apply Modified Tiny: differentiated costs from gen_temporal_params.csv
        # ------------------------------------------------------------------
        if isnothing(timeseries_dir)
            timeseries_dir = "../../data/timeseries/case39"
        end
        println("Timeseries dir: $timeseries_dir")

        cost_by_index = load_gen_costs(timeseries_dir)
        apply_differentiated_costs!(data, cost_by_index)
        println("Differentiated costs applied to $(length(cost_by_index)) generators")

        println("--- Generator Cost Assignments ---")
        for (gen_id, gen) in sort(collect(data["gen"]); by=x->parse(Int, x[1]))
            c = gen["cost"]
            gi = gen["index"] - 1
            c1_orig = c[2] / base_mva   # $/MWh
            println(
                "  Gen $(gen["index"]) (bus $(gen["gen_bus"])): c1=$(round(c1_orig,digits=2)) \$/MWh  Pmax=$(round(gen["pmax"]*base_mva,digits=1)) MW",
            )
        end
        println()

        # ------------------------------------------------------------------
        # 3. Apply 70% branch derating
        # ------------------------------------------------------------------
        apply_branch_derating!(data, BRANCH_DERATING)
        println("Applied $(BRANCH_DERATING*100)% branch derating to all rate_a values")
        println()

        # ------------------------------------------------------------------
        # 4. Solve DC OPF with HiGHS, requesting dual variables for LMPs
        #    API: solve_dc_opf(data, optimizer; setting=Dict(...))
        #         (NOT solve_dc_opf(data, FormulationType, optimizer))
        # ------------------------------------------------------------------
        highs_opt = optimizer_with_attributes(
            HiGHS.Optimizer,
            "output_flag" => false,
            "presolve" => "on",
            "time_limit" => 300.0,
            "threads" => 1,
        )

        result = PowerModels.solve_dc_opf(
            data, highs_opt; setting=Dict("output" => Dict("duals" => true))
        )

        termination_status = string(result["termination_status"])
        objective_value = get(result, "objective", NaN)
        solve_time = get(result, "solve_time", NaN)

        println("DC OPF solve complete:")
        println("  Termination status: $termination_status")
        println("  Objective (\$/h):   $(round(objective_value, digits=2))")
        println("  Solver time (s):    $(round(solve_time, digits=4))")
        println()

        # ------------------------------------------------------------------
        # 5. Extract generator dispatch
        # ------------------------------------------------------------------
        gen_dispatch_mw = Dict{String,Float64}()
        if haskey(result, "solution") && haskey(result["solution"], "gen")
            for (gen_id, gen_sol) in result["solution"]["gen"]
                gen_dispatch_mw[gen_id] = get(gen_sol, "pg", 0.0) * base_mva
            end
        end
        total_gen_mw = sum(values(gen_dispatch_mw); init=0.0)

        println("--- Generator Dispatch ---")
        for gen_id in sort(collect(keys(gen_dispatch_mw)); by=x->parse(Int, x))
            pmax_mw = data["gen"][gen_id]["pmax"] * base_mva
            c1 = data["gen"][gen_id]["cost"][2] / base_mva
            println(
                "  Gen $gen_id ($(round(gen_dispatch_mw[gen_id],digits=2)) MW / $(round(pmax_mw,digits=2)) MW, c1=$(round(c1,digits=2)) \$/MWh)",
            )
        end
        println("  Total generation: $(round(total_gen_mw, digits=2)) MW")
        println()

        # ------------------------------------------------------------------
        # 6. Extract LMPs from lam_kcl_r
        #    Convention: lam_kcl_r is the dual of the power balance constraint
        #    for a minimization problem. LMP in $/MWh = -lam_kcl_r / baseMVA
        # ------------------------------------------------------------------
        lmp_values = Dict{String,Float64}()
        if haskey(result, "solution") && haskey(result["solution"], "bus")
            for (bus_id, bus_sol) in result["solution"]["bus"]
                lam = get(bus_sol, "lam_kcl_r", nothing)
                if !isnothing(lam) && isfinite(lam)
                    lmp_values[bus_id] = -lam / base_mva
                end
            end
        end

        lmp_available = !isempty(lmp_values)
        max_lmp_spread = 0.0
        lmp_min = NaN;
        lmp_max = NaN
        if lmp_available
            lmp_min = minimum(values(lmp_values))
            lmp_max = maximum(values(lmp_values))
            max_lmp_spread = lmp_max - lmp_min
            println("--- Bus LMPs (\$/MWh, from lam_kcl_r / baseMVA) ---")
            println(
                "  Min: $(round(lmp_min, digits=4))  Max: $(round(lmp_max, digits=4))  Spread: $(round(max_lmp_spread, digits=4)) \$/MWh",
            )
            for bus_id in sort(collect(keys(lmp_values)); by=x->parse(Int, x))[1:min(10, end)]
                println("  Bus $bus_id: $(round(lmp_values[bus_id], digits=4)) \$/MWh")
            end
        else
            println("WARNING: LMPs not found in result solution (lam_kcl_r missing)")
            push!(results["errors"], "LMP extraction failed: lam_kcl_r not in solution")
        end
        println()

        # ------------------------------------------------------------------
        # 7. Extract branch flows and identify binding branches
        # ------------------------------------------------------------------
        branch_flows_mw = Dict{String,Float64}()
        branch_rate_a_mw = Dict{String,Float64}()
        binding_branches = String[]

        if haskey(result, "solution") && haskey(result["solution"], "branch")
            for (br_id, br_sol) in result["solution"]["branch"]
                pf_mw = get(br_sol, "pf", 0.0) * base_mva
                rate_mw = get(data["branch"][br_id], "rate_a", 0.0) * base_mva
                branch_flows_mw[br_id] = pf_mw
                branch_rate_a_mw[br_id] = rate_mw
                if rate_mw > 1e-3 && abs(pf_mw) >= BINDING_THRESHOLD * rate_mw
                    push!(binding_branches, br_id)
                end
            end
        end

        n_binding = length(binding_branches)
        println("--- Binding Branches (|pf| >= $(BINDING_THRESHOLD*100)%% of rate_a) ---")
        println("  Total binding: $n_binding / $n_branches")
        for br_id in sort(binding_branches; by=x->parse(Int, x))
            f_bus = data["branch"][br_id]["f_bus"]
            t_bus = data["branch"][br_id]["t_bus"]
            println(
                "  Branch $br_id ($f_bus→$t_bus): flow=$(round(branch_flows_mw[br_id],digits=2)) MW, limit=$(round(branch_rate_a_mw[br_id],digits=2)) MW",
            )
        end
        println()

        # ------------------------------------------------------------------
        # 7b. Hard constraint check: max_loading <= 1.0 + 1e-4 p.u.
        #     If any branch exceeds this, the tool uses soft constraints => partial_pass
        # ------------------------------------------------------------------
        max_loading_pu = 0.0
        max_loading_branch = ""
        for (br_id, br_sol) in result["solution"]["branch"]
            pf_pu = abs(get(br_sol, "pf", 0.0))
            rate_a_pu = get(data["branch"][br_id], "rate_a", 0.0)
            if rate_a_pu > 1e-8
                loading = pf_pu / rate_a_pu
                if loading > max_loading_pu
                    max_loading_pu = loading
                    max_loading_branch = br_id
                end
            end
        end
        hard_constraints_ok = max_loading_pu <= 1.0 + 1e-4

        max_loading_str = @sprintf("%.6e", max_loading_pu)
        println("--- Hard Constraint Check ---")
        println("  Max branch loading: $max_loading_str p.u. (branch $max_loading_branch)")
        println("  Hard constraints enforced: $hard_constraints_ok (threshold: 1.0 + 1e-4)")
        println()

        # ------------------------------------------------------------------
        # 8. Pass condition checks
        # ------------------------------------------------------------------
        converged =
            (termination_status == "OPTIMAL") ||
            (termination_status == "LOCALLY_SOLVED") ||
            occursin("OPTIMAL", termination_status)

        dispatch_accessible = !isempty(gen_dispatch_mw)
        binding_ok = n_binding >= BINDING_BRANCHES_MIN

        println("Pass checks:")
        println("  Converged:              $converged  (status=$termination_status)")
        println("  Dispatch accessible:    $dispatch_accessible  ($(length(gen_dispatch_mw)) gens)")
        println("  LMP accessible:         $lmp_available  ($(length(lmp_values)) buses)")
        println("  Binding branches >= $BINDING_BRANCHES_MIN:   $binding_ok  (n=$n_binding)")
        println("  Max LMP spread:         $(round(max_lmp_spread, digits=4)) \$/MWh")
        println("  Hard constraints:       $hard_constraints_ok  (max_loading=$max_loading_str)")

        if converged && dispatch_accessible && lmp_available && binding_ok && hard_constraints_ok
            results["status"] = "pass"
        elseif converged &&
            dispatch_accessible &&
            lmp_available &&
            binding_ok &&
            !hard_constraints_ok
            results["status"] = "partial_pass"
            push!(
                results["workarounds"],
                "Soft branch flow constraints detected: max_loading=$max_loading_str > 1.0 + 1e-4. Tool uses penalty-based enforcement.",
            )
        elseif converged && dispatch_accessible && binding_ok
            results["status"] = "qualified_pass"
            push!(
                results["workarounds"],
                "LMPs not extractable from result dict (lam_kcl_r missing). Requires instantiate_model + JuMP.dual() path for reliable dual extraction.",
            )
        else
            push!(
                results["errors"],
                "Core conditions not met: converged=$converged, dispatch=$dispatch_accessible, binding=$n_binding (need>=$BINDING_BRANCHES_MIN)",
            )
        end

        results["details"] = Dict(
            "network_file" => network_file,
            "timeseries_dir" => timeseries_dir,
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "branch_derating" => BRANCH_DERATING,
            "termination_status" => termination_status,
            "objective_dollars_per_hr" => objective_value,
            "solver_time_s" => solve_time,
            "gen_dispatch_mw" => gen_dispatch_mw,
            "total_gen_mw" => total_gen_mw,
            "lmp_available" => lmp_available,
            "lmp_min_dollars_per_mwh" => lmp_min,
            "lmp_max_dollars_per_mwh" => lmp_max,
            "max_lmp_spread" => max_lmp_spread,
            "lmp_values" => lmp_values,
            "n_binding_branches" => n_binding,
            "binding_branch_ids" => binding_branches,
            "branch_flows_mw" => branch_flows_mw,
            "max_loading_pu" => max_loading_str,
            "max_loading_branch" => max_loading_branch,
            "hard_constraints_ok" => hard_constraints_ok,
            "solver" => "HiGHS (LP via solve_dc_opf / DCPPowerModel)",
            "loc" => 240,
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        println("ERROR in A-3: $(typeof(e)): $e")
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

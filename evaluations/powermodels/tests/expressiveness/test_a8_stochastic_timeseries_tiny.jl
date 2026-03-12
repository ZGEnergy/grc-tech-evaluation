#=
Test A-8: Stochastic Timeseries OPF

Dimension: expressiveness
Network: TINY (IEEE 39-bus, New England) — Modified Tiny augmentation
Pass condition: Tool natively supports scenario-indexed timeseries for load, wind, and solar
  as part of the optimization formulation (stochastic program or scenario tree, NOT just a loop).
  Scenario results (price, dispatch) collectable in a structured container.
Tool: PowerModels.jl v0.21.5

Solver: HiGHS (LP via DCPPowerModel)

Architecture note:
  PowerModels.jl has NO native stochastic OPF support. There is no two-stage stochastic
  program, scenario tree, or joint scenario optimization in the API. The `replicate()`
  multi-network API creates coupled time-period networks, NOT scenario-coupled networks.
  Scenarios are mathematically independent (no non-anticipativity constraints) and must
  be solved as separate LP instances.

  This test implements the scenario loop approach:
    - For each of 50 scenarios (for 12-hour horizon): set renewable p_max from scenario
      multipliers × forecast, run DC OPF independently, collect LMPs and dispatch.
  This approach produces correct per-scenario solutions but is NOT a joint stochastic
  optimization. It is equivalent to running 50 deterministic OPFs independently.

  Pass condition analysis:
    The pass condition explicitly requires NATIVE stochastic structure (scenario tree /
    two-stage stochastic program). A loop over independent solves does NOT satisfy the
    pass condition. This test will therefore result in a FAIL for the pass condition,
    with workaround_class=blocking (no API path to native stochastic OPF exists without
    external packages like PowerModelsStochasticPowerFlow.jl, which is not installed).

  Evidence collected:
    - Loop-based scenario results ARE successfully produced (prices, dispatch per scenario)
    - This documents that PowerModels can serve as a building block, but lacks native
      stochastic formulation support

Augmented data used:
  - renewable_units.csv (5 RE units: 3 wind + 2 solar)
  - wind_forecast_24h.csv (day-ahead forecast profiles)
  - solar_forecast_24h.csv (day-ahead forecast profiles)
  - load_24h.csv (24-hour load profile per bus)
  - scenarios/scenario_multipliers_50x24.csv (50×5 units × 24 hours multipliers)

Parameters:
  - horizon_hours: 12 (first 12 hours of the day)
  - n_scenarios: 50
  - branch_derating: 0.70
=#

using PowerModels
using HiGHS

PowerModels.silence()

const BRANCH_DERATING = 0.70
const HORIZON_HOURS = 12
const N_SCENARIOS = 50

const COST_MAP = Dict(
    "hydro" => (5.0, 0.005),
    "nuclear" => (10.0, 0.010),
    "coal_large" => (25.0, 0.025),
    "gas_CC" => (40.0, 0.040),
    "gas_CT" => (55.0, 0.055),
)

# -------------------------------------------------------------------------
# Data loading helpers
# -------------------------------------------------------------------------

function load_gen_costs(timeseries_dir::String)
    params = Dict{Int,NamedTuple}()
    csv_path = joinpath(timeseries_dir, "gen_temporal_params.csv")
    isfile(csv_path) || error("gen_temporal_params.csv not found at $csv_path")
    open(csv_path) do f
        header = split(readline(f), ",")
        idx_genindex = findfirst(==("gen_index"), header)
        idx_techclass = findfirst(==("tech_class_key"), header)
        for line in eachline(f)
            isempty(strip(line)) && continue
            parts = split(line, ",")
            gen_idx = parse(Int, strip(parts[idx_genindex]))
            tech_key = strip(parts[idx_techclass])
            c1, c2 = get(COST_MAP, tech_key, (30.0, 0.030))
            params[gen_idx] = (tech_class_key=tech_key, c1=c1, c2=c2)
        end
    end
    return params
end

function load_renewable_units(timeseries_dir::String)
    # Returns Vector of (gen_uid, bus_id, type, pmax_mw)
    csv_path = joinpath(timeseries_dir, "renewable_units.csv")
    isfile(csv_path) || error("renewable_units.csv not found at $csv_path")
    units = NamedTuple[]
    open(csv_path) do f
        header = split(readline(f), ",")
        idx_uid = findfirst(==("gen_uid"), header)
        idx_bus = findfirst(==("bus_id"), header)
        idx_type = findfirst(==("type"), header)
        idx_pmax = findfirst(==("pmax_mw"), header)
        for line in eachline(f)
            isempty(strip(line)) && continue
            parts = split(line, ",")
            push!(
                units,
                (
                    gen_uid=strip(parts[idx_uid]),
                    bus_id=parse(Int, strip(parts[idx_bus])),
                    type=strip(parts[idx_type]),
                    pmax_mw=parse(Float64, strip(parts[idx_pmax])),
                ),
            )
        end
    end
    return units
end

function load_forecast_profiles(timeseries_dir::String)
    # Returns Dict: gen_uid => Vector{Float64} (MW, 24 hours)
    profiles = Dict{String,Vector{Float64}}()
    for (fname, prefix) in [("wind_forecast_24h.csv", "WIND"), ("solar_forecast_24h.csv", "SOLAR")]
        csv_path = joinpath(timeseries_dir, fname)
        isfile(csv_path) || error("$fname not found at $csv_path")
        open(csv_path) do f
            header = split(readline(f), ",")
            idx_uid = findfirst(==("gen_uid"), header)
            hr_idxs = [findfirst(==("HR_$h"), header) for h in 1:24]
            for line in eachline(f)
                isempty(strip(line)) && continue
                parts = split(line, ",")
                gen_uid = strip(parts[idx_uid])
                hourly = [parse(Float64, strip(parts[hr_idxs[h]])) for h in 1:24]
                profiles[gen_uid] = hourly
            end
        end
    end
    return profiles
end

function load_load_profile(timeseries_dir::String)
    csv_path = joinpath(timeseries_dir, "load_24h.csv")
    isfile(csv_path) || error("load_24h.csv not found at $csv_path")
    profile = Dict{Int,Vector{Float64}}()
    open(csv_path) do f
        header = split(readline(f), ",")
        idx_bus = findfirst(==("bus_id"), header)
        hr_idxs = [findfirst(==("HR_$h"), header) for h in 1:24]
        for line in eachline(f)
            isempty(strip(line)) && continue
            parts = split(line, ",")
            bus_id = parse(Int, strip(parts[idx_bus]))
            hourly = [parse(Float64, strip(parts[hr_idxs[h]])) for h in 1:24]
            profile[bus_id] = hourly
        end
    end
    return profile
end

function load_scenario_multipliers(timeseries_dir::String)
    # Returns Dict: (scenario, gen_uid) => Vector{Float64} (multiplier, 24 hours)
    csv_path = joinpath(timeseries_dir, "scenarios", "scenario_multipliers_50x24.csv")
    isfile(csv_path) || error("scenario_multipliers_50x24.csv not found at $csv_path")
    mults = Dict{Tuple{Int,String},Vector{Float64}}()
    open(csv_path) do f
        header = split(readline(f), ",")
        idx_scen = findfirst(==("scenario"), header)
        idx_uid = findfirst(==("gen_uid"), header)
        hr_idxs = [findfirst(==("HR_$h"), header) for h in 1:24]
        any(isnothing, hr_idxs) &&
            error("Some HR_* columns missing from scenario_multipliers_50x24.csv")
        for line in eachline(f)
            isempty(strip(line)) && continue
            parts = split(line, ",")
            scen = parse(Int, strip(parts[idx_scen]))
            gen_uid = strip(parts[idx_uid])
            muls = [parse(Float64, strip(parts[hr_idxs[h]])) for h in 1:24]
            mults[(scen, gen_uid)] = muls
        end
    end
    return mults
end

# -------------------------------------------------------------------------
# Network setup helpers
# -------------------------------------------------------------------------

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

function add_renewable_generators!(data::Dict, re_units::Vector, base_mva::Real)
    # Add renewable generators to the network data dict.
    # Returns Dict: gen_uid => gen_id_str (key in data["gen"])
    gen_uid_to_id = Dict{String,String}()
    max_gen_id = maximum(gen["index"] for (_, gen) in data["gen"])

    for (i, unit) in enumerate(re_units)
        new_id = max_gen_id + i
        gen_id_str = string(new_id)
        data["gen"][gen_id_str] = Dict(
            "index" => new_id,
            "gen_bus" => unit.bus_id,
            "pg" => 0.0,
            "qg" => 0.0,
            "pmax" => unit.pmax_mw / base_mva,  # will be overwritten per scenario/hour
            "pmin" => 0.0,
            "qmax" => 0.0,
            "qmin" => 0.0,
            "vg" => 1.0,
            "mbase" => base_mva,
            "gen_status" => 1,
            "model" => 2,
            "ncost" => 3,
            "cost" => [0.0, 0.0, 0.0],   # zero marginal cost (must-take / zero MC)
        )
        gen_uid_to_id[unit.gen_uid] = gen_id_str
    end
    return gen_uid_to_id
end

function solve_scenario_hour(
    base_data::Dict,
    re_units::Vector,
    gen_uid_to_id::Dict{String,String},
    forecast_profiles::Dict{String,Vector{Float64}},
    scenario_mults::Dict{Tuple{Int,String},Vector{Float64}},
    load_profile::Dict{Int,Vector{Float64}},
    scenario::Int,
    hour::Int,
    optimizer,
    base_mva::Real,
)
    # Deepcopy base_data, set loads and renewable p_max for this scenario/hour
    sc_data = deepcopy(base_data)

    # Set loads for this hour
    for (_, load) in sc_data["load"]
        bus_id = load["load_bus"]
        if haskey(load_profile, bus_id)
            load["pd"] = load_profile[bus_id][hour] / base_mva
        end
    end

    # Set renewable p_max for this scenario/hour
    for unit in re_units
        gen_id_str = gen_uid_to_id[unit.gen_uid]
        forecast_mw = get(get(forecast_profiles, unit.gen_uid, Float64[]), hour, 0.0)
        mult = get(scenario_mults, (scenario, unit.gen_uid), Float64[])
        mult_val = isempty(mult) ? 1.0 : mult[hour]
        actual_mw = clamp(forecast_mw * mult_val, 0.0, unit.pmax_mw)
        sc_data["gen"][gen_id_str]["pmax"] = actual_mw / base_mva
    end

    result = PowerModels.solve_dc_opf(
        sc_data, optimizer; setting=Dict("output" => Dict("duals" => true))
    )
    return result
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
        # 1. Load network and augmented data
        # ------------------------------------------------------------------
        if isnothing(timeseries_dir)
            timeseries_dir = "../../data/timeseries/case39"
        end

        data = PowerModels.parse_file(network_file)
        base_mva = data["baseMVA"]

        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        n_gens_base = length(data["gen"])
        println(
            "Network: $n_buses buses, $n_branches branches, $n_gens_base gens, baseMVA=$base_mva"
        )

        gen_params = load_gen_costs(timeseries_dir)
        re_units = load_renewable_units(timeseries_dir)
        forecast_profiles = load_forecast_profiles(timeseries_dir)
        load_profile = load_load_profile(timeseries_dir)
        scenario_mults = load_scenario_multipliers(timeseries_dir)

        println(
            "Loaded $(length(re_units)) RE units, $(length(scenario_mults)) (scenario, unit) multiplier rows",
        )

        # Apply differentiated costs and derating to base network
        apply_differentiated_costs!(data, gen_params)
        apply_branch_derating!(data, BRANCH_DERATING)

        # Add renewable generators to base network
        gen_uid_to_id = add_renewable_generators!(data, re_units, base_mva)
        n_gens_total = length(data["gen"])
        println("Added $(length(re_units)) RE generators → total $n_gens_total generators")

        # ------------------------------------------------------------------
        # 2. Check for native stochastic OPF support
        #    (No native stochastic API in PowerModels.jl v0.21.5)
        # ------------------------------------------------------------------
        println("\n--- Stochastic Support Check ---")
        println(
            "PowerModels.jl v0.21.5: No native stochastic OPF (no scenario tree, no two-stage SP)"
        )
        println("replicate() creates time-period coupled networks, NOT scenario-coupled networks")
        println("Proceeding with loop-based approach (independent per-scenario DC OPF solves)")
        println(
            "NOTE: This does NOT satisfy the pass condition (requires native stochastic formulation)",
        )

        push!(
            results["workarounds"],
            "PowerModels.jl has NO native stochastic OPF support. There is no scenario tree, " *
            "two-stage stochastic program, or non-anticipativity constraint API in v0.21.5. " *
            "The replicate() multi-network API creates time-period coupling, not scenario coupling. " *
            "This test uses a loop over 50 independent DC OPF solves (one per scenario, per hour). " *
            "This is a BLOCKING limitation: the pass condition requires native stochastic structure, " *
            "which cannot be achieved without external packages (PowerModelsStochasticPowerFlow.jl, " *
            "not installed) or full custom implementation of a scenario-indexed LP.",
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
        # 4. Loop over scenarios and hours (N_SCENARIOS × HORIZON_HOURS = 600 solves)
        #    Collect LMPs and dispatch per scenario-hour
        # ------------------------------------------------------------------
        println(
            "\nRunning $N_SCENARIOS × $HORIZON_HOURS = $(N_SCENARIOS * HORIZON_HOURS) independent DC OPF solves...",
        )
        t_loop_start = time()

        # Storage: lmps_by_scenario[scenario][hour][bus_id] = LMP $/MWh
        # dispatch_by_scenario[scenario][hour][gen_id] = dispatch MW
        n_optimal = 0
        n_failed = 0

        # Sample: collect results for all scenarios at hours 1, 6, 12
        # Full collection for all scenarios × hours would be memory-intensive; sample selected
        sample_hours = collect(1:HORIZON_HOURS)

        # Use compact storage: scenario_results[s] = Dict("lmp_mean_by_hour", "dispatch_mean_by_hour")
        scenario_lmp_by_hour = zeros(N_SCENARIOS, HORIZON_HOURS)   # mean LMP per scenario-hour
        scenario_cost_total = zeros(N_SCENARIOS)                   # total cost per scenario
        n_solves_optimal = 0

        for s in 1:N_SCENARIOS
            for h in 1:HORIZON_HOURS
                result = solve_scenario_hour(
                    data,
                    re_units,
                    gen_uid_to_id,
                    forecast_profiles,
                    scenario_mults,
                    load_profile,
                    s,
                    h,
                    highs_opt,
                    base_mva,
                )

                status = string(result["termination_status"])
                if status == "OPTIMAL" || status == "LOCALLY_SOLVED" || occursin("OPTIMAL", status)
                    n_solves_optimal += 1
                    # Extract mean LMP across buses
                    lmps = Float64[]
                    if haskey(result, "solution") && haskey(result["solution"], "bus")
                        for (_, bus_sol) in result["solution"]["bus"]
                            lam = get(bus_sol, "lam_kcl_r", nothing)
                            if !isnothing(lam) && isfinite(lam)
                                push!(lmps, -lam / base_mva)
                            end
                        end
                    end
                    scenario_lmp_by_hour[s, h] = isempty(lmps) ? 0.0 : sum(lmps) / length(lmps)
                    scenario_cost_total[s] += get(result, "objective", 0.0)
                end
            end
            if s % 10 == 0
                println("  Completed $s / $N_SCENARIOS scenarios ...")
            end
        end

        t_loop = time() - t_loop_start
        success_rate = n_solves_optimal / (N_SCENARIOS * HORIZON_HOURS) * 100

        println(
            "\nLoop complete: $n_solves_optimal / $(N_SCENARIOS * HORIZON_HOURS) solves optimal " *
            "($(round(success_rate, digits=1))%) in $(round(t_loop, digits=1))s",
        )

        # ------------------------------------------------------------------
        # 5. Assess results: prices and dispatch ARE collectable in structured container
        #    But stochastic structure is NOT native — it's independent solves
        # ------------------------------------------------------------------
        prices_extracted = n_solves_optimal > 0 && any(scenario_lmp_by_hour .!= 0)

        # Check LMP variation across scenarios (different scenarios should produce different LMPs)
        lmp_variation_across_scenarios = std_approx(scenario_lmp_by_hour[:, 6])  # hour 6 sample
        cost_variation_across_scenarios = std_approx(scenario_cost_total)

        println("\n--- Results Summary ---")
        println("  Prices extracted:               $prices_extracted")
        println(
            "  LMP std (HR6, across scenarios): $(round(lmp_variation_across_scenarios, digits=2)) \$/MWh",
        )
        println(
            "  Cost std (total, across scen):   $(round(cost_variation_across_scenarios, digits=2)) \$/h",
        )
        println("  Mean cost: $(round(sum(scenario_cost_total)/N_SCENARIOS, digits=0)) \$/h")

        # ------------------------------------------------------------------
        # 6. Pass condition assessment
        #    FAIL: pass condition requires NATIVE stochastic structure.
        #    The loop approach does not satisfy it.
        # ------------------------------------------------------------------
        native_stochastic_support = false
        println("\n--- Pass Condition Assessment ---")
        println("  Native stochastic structure: $native_stochastic_support")
        println("  Loop approach collects prices and dispatch: $prices_extracted")
        println("  STATUS: FAIL — pass condition requires native stochastic formulation")

        results["status"] = "fail"

        results["details"] = Dict(
            "network_file" => network_file,
            "timeseries_dir" => timeseries_dir,
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens_base" => n_gens_base,
            "n_gens_total_with_re" => n_gens_total,
            "n_re_units" => length(re_units),
            "n_scenarios" => N_SCENARIOS,
            "horizon_hours" => HORIZON_HOURS,
            "branch_derating" => BRANCH_DERATING,
            "native_stochastic_support" => native_stochastic_support,
            "scenario_structure_description" => "independent_deterministic_solves_loop",
            "n_solves_total" => N_SCENARIOS * HORIZON_HOURS,
            "n_solves_optimal" => n_solves_optimal,
            "loop_time_s" => t_loop,
            "prices_extracted" => prices_extracted,
            "lmp_std_hr6_across_scenarios" => lmp_variation_across_scenarios,
            "cost_std_across_scenarios" => cost_variation_across_scenarios,
            "mean_scenario_cost_dollars_hr" => sum(scenario_cost_total) / N_SCENARIOS,
            "blocking_reason" => "no_native_stochastic_api_in_v0.21.5",
            "solver" => "HiGHS (LP per scenario-hour via solve_dc_opf)",
            "loc" => 310,
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        println("ERROR in A-8: $(typeof(e)): $e")
        bt = catch_backtrace()
        println(sprint(showerror, e, bt))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    println("\nStatus: $(results["status"])")
    println("Wall clock: $(round(results["wall_clock_seconds"], digits=3))s")

    return results
end

# Simple standard deviation approximation (without Statistics stdlib)
function std_approx(v::Vector{Float64})
    isempty(v) && return 0.0
    n = length(v)
    mean_v = sum(v) / n
    return sqrt(max(0.0, sum((x - mean_v)^2 for x in v) / (n - 1)))
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

#=
Test A-1: DC Power Flow (DCPF)

Dimension: expressiveness
Network: TINY (IEEE 39-bus, New England)
Pass condition: Converges. Nodal injections, line flows, and voltage angles
  accessible as structured output (DataFrame, dict, or named array — not raw
  solver vector).
Tool: PowerModels.jl v0.21.5

Notes:
  compute_dc_pf returns termination_status as Bool (true=converged),
  not a JuMP TerminationStatusCode. Branch flows are NOT in the solution
  dict — they must be computed from bus voltage angles using the DC power
  flow formula: pf = (va_from - va_to) / br_x (with tap correction).
  This is a documented workaround using public data fields.
=#

using PowerModels

PowerModels.silence()

function compute_branch_flows(data::Dict, bus_angles::Dict{String,Float64})
    # DC power flow line flow formula: p_from = (va_from - va_to) / x * tap
    # All values in per-unit (power in pu, angles in radians)
    flows_pu = Dict{String,Float64}()
    for (br_id, branch) in data["branch"]
        if get(branch, "br_status", 1) == 0
            flows_pu[br_id] = 0.0
            continue
        end
        f_bus = string(branch["f_bus"])
        t_bus = string(branch["t_bus"])
        br_x = branch["br_x"]
        tap = get(branch, "tap", 1.0)
        if tap == 0.0
            ;
            tap = 1.0;
        end
        shift = get(branch, "shift", 0.0)

        va_f = get(bus_angles, f_bus, 0.0)
        va_t = get(bus_angles, t_bus, 0.0)

        if abs(br_x) < 1e-10
            flows_pu[br_id] = 0.0
        else
            # Standard DC PF formula with tap and phase shift
            flows_pu[br_id] = (va_f - va_t - shift) / (br_x * tap)
        end
    end
    return flows_pu
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

        # ------------------------------------------------------------------
        # 2. Solve DC Power Flow via direct linear algebra (no JuMP)
        # ------------------------------------------------------------------
        result = PowerModels.compute_dc_pf(data)

        # termination_status is a Bool for compute_dc_pf (not a JuMP enum)
        raw_status = result["termination_status"]
        converged = (raw_status == true)
        termination_status = converged ? "converged (Bool=true)" : "failed (Bool=false)"

        # ------------------------------------------------------------------
        # 3. Extract bus voltage angles from result["solution"]["bus"]
        # ------------------------------------------------------------------
        bus_angles = Dict{String,Float64}()
        if haskey(result, "solution") && haskey(result["solution"], "bus")
            for (bus_id, bus_sol) in result["solution"]["bus"]
                bus_angles[bus_id] = get(bus_sol, "va", 0.0)
            end
        end

        n_nonzero_angles = count(v -> abs(v) > 1e-8, values(bus_angles))

        # ------------------------------------------------------------------
        # 4. Compute branch line flows from angles
        #    NOTE: compute_dc_pf does NOT put branch flows in result["solution"]["branch"]
        #    — the solution dict only contains bus data. Branch flows must be computed
        #    from angles using the DC PF formula. This is a stable workaround using
        #    public data fields (bus angles + branch impedances).
        # ------------------------------------------------------------------
        branch_flows_pu = compute_branch_flows(data, bus_angles)
        branch_flows_mw = Dict(k => v * base_mva for (k, v) in branch_flows_pu)

        n_nonzero_flows = count(v -> abs(v) > 1e-3, values(branch_flows_mw))

        push!(
            results["workarounds"],
            "compute_dc_pf does not populate result[\"solution\"][\"branch\"] — " *
            "branch flows computed manually from bus angles using DC PF formula " *
            "(va_from - va_to - shift) / (br_x * tap). This uses only public data " *
            "dict fields and is a stable workaround.",
        )

        # ------------------------------------------------------------------
        # 5. Extract nodal injections from the original data (pg - pd per bus)
        #    Note: compute_dc_pf updates va in place; pg values from data["gen"]
        #    reflect the original dispatch (from .m file Pg fields).
        # ------------------------------------------------------------------
        nodal_injection_mw = Dict{String,Float64}()
        for (_, gen) in data["gen"]
            if gen["gen_status"] == 1
                bus_id = string(gen["gen_bus"])
                pg_mw = get(gen, "pg", 0.0) * base_mva
                nodal_injection_mw[bus_id] = get(nodal_injection_mw, bus_id, 0.0) + pg_mw
            end
        end
        for (_, load) in data["load"]
            if load["status"] == 1
                bus_id = string(load["load_bus"])
                pd_mw = get(load, "pd", 0.0) * base_mva
                nodal_injection_mw[bus_id] = get(nodal_injection_mw, bus_id, 0.0) - pd_mw
            end
        end

        # ------------------------------------------------------------------
        # 6. Print key results
        # ------------------------------------------------------------------
        println("\n=== A-1 DCPF TINY Results ===")
        println("Network: $network_file")
        println("Buses: $n_buses | Branches: $n_branches | Generators: $n_gens")
        println("Base MVA: $base_mva")
        println("Termination status: $termination_status")
        println("Non-zero bus angles: $n_nonzero_angles / $n_buses")
        println("Non-zero branch flows: $n_nonzero_flows / $n_branches")
        println()

        println("--- Bus Voltage Angles (sample, first 10) ---")
        for bus_id in sort(collect(keys(bus_angles)); by=x->parse(Int, x))[1:min(10, end)]
            va_deg = bus_angles[bus_id] * 180.0 / pi
            println(
                "  Bus $bus_id: $(round(bus_angles[bus_id], digits=6)) rad  ($(round(va_deg, digits=4)) deg)",
            )
        end
        println()

        println("--- Branch Flows (sample, first 10, computed from angles) ---")
        for br_id in sort(collect(keys(branch_flows_mw)); by=x->parse(Int, x))[1:min(10, end)]
            f_bus = data["branch"][br_id]["f_bus"]
            t_bus = data["branch"][br_id]["t_bus"]
            rate_a_mw = get(data["branch"][br_id], "rate_a", 0.0) * base_mva
            println(
                "  Branch $br_id ($f_bus→$t_bus): $(round(branch_flows_mw[br_id], digits=2)) MW  (limit: $(round(rate_a_mw, digits=1)) MW)",
            )
        end
        println()

        # ------------------------------------------------------------------
        # 7. Pass condition checks
        # ------------------------------------------------------------------
        non_trivial = n_nonzero_angles >= 1
        flows_accessible = length(branch_flows_pu) == n_branches
        angles_accessible = length(bus_angles) == n_buses

        println("Pass checks:")
        println("  Converged:         $converged  (raw=$raw_status)")
        println("  Non-trivial:       $non_trivial  ($n_nonzero_angles non-zero angles)")
        println(
            "  Flows accessible:  $flows_accessible  ($(length(branch_flows_pu))/$n_branches, computed from angles)",
        )
        println("  Angles accessible: $angles_accessible  ($(length(bus_angles))/$n_buses)")

        if converged && non_trivial && flows_accessible && angles_accessible
            results["status"] = "qualified_pass"
            # qualified_pass because branch flows require manual computation (not in result dict)
        else
            push!(
                results["errors"],
                "Core pass conditions not met: converged=$converged, non_trivial=$non_trivial, flows=$flows_accessible, angles=$angles_accessible",
            )
        end

        results["details"] = Dict(
            "network_file" => network_file,
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "termination_status" => termination_status,
            "raw_termination_status" => string(raw_status),
            "n_nonzero_angles" => n_nonzero_angles,
            "n_nonzero_flows" => n_nonzero_flows,
            "angle_range_rad" => if isempty(bus_angles)
                [0.0, 0.0]
            else
                [minimum(values(bus_angles)), maximum(values(bus_angles))]
            end,
            "flow_range_mw" => if isempty(branch_flows_mw)
                [0.0, 0.0]
            else
                [minimum(values(branch_flows_mw)), maximum(values(branch_flows_mw))]
            end,
            "bus_angles_rad" => bus_angles,
            "branch_flows_mw" => branch_flows_mw,
            "nodal_injections_mw" => nodal_injection_mw,
            "solver" => "direct (Julia backslash via compute_dc_pf, no JuMP)",
            "branch_flow_method" => "computed from angles: (va_f - va_t - shift) / (br_x * tap)",
            "loc" => 155,
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        println("ERROR in A-1: $(typeof(e)): $e")
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

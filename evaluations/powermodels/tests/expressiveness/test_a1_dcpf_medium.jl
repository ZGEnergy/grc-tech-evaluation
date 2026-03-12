#=
Test A-1: DC Power Flow (DCPF) — MEDIUM grade assessment
Dimension: expressiveness
Network: MEDIUM (ACTIVSg 10000-bus, case_ACTIVSg10k.m)
Pass condition: Converges. Nodal injections, line flows, and voltage angles
  accessible as structured output (DataFrame, dict, or named array — not raw
  solver vector).
Tool: PowerModels.jl v0.21.5

Preprocessing (per MEDIUM protocol):
  - Zero-reactance fix: branches with br_x=0 → set to 0.0001 pu
  - Zero/Inf RATE_A fix: branches with rate_a=0 or Inf → set to 9999 MVA

Notes:
  compute_dc_pf returns termination_status as Bool (true=converged).
  Branch flows NOT in result["solution"]["branch"] — computed from bus voltage
  angles using DC PF formula: pf = (va_from - va_to - shift) / (br_x * tap).
  This is the same stable workaround used in the TINY assessment.
  Timing: second invocation (JIT warm-up on case39 first).
=#

using PowerModels, JSON

PowerModels.silence()

function is_converged(term_status)
    if term_status isa Bool
        return term_status
    end
    s = string(term_status)
    return s in ("LOCALLY_SOLVED", "OPTIMAL", "true")
end

function apply_medium_preprocessing!(data::Dict)
    base_mva = data["baseMVA"]
    n_x_fixed = 0
    n_rate_fixed = 0
    for (_, branch) in data["branch"]
        if branch["br_x"] == 0.0
            branch["br_x"] = 0.0001
            n_x_fixed += 1
        end
        ra = get(branch, "rate_a", 0.0)
        if ra == 0.0 || isinf(ra)
            branch["rate_a"] = 9999.0 / base_mva   # store in per-unit
            n_rate_fixed += 1
        end
    end
    return (n_x_fixed, n_rate_fixed)
end

function compute_branch_flows(data::Dict, bus_angles::Dict{String,Float64})
    base_mva = data["baseMVA"]
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
            flows_pu[br_id] = (va_f - va_t - shift) / (br_x * tap)
        end
    end
    return flows_pu
end

function run(
    network_file::String=joinpath(
        @__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg10k.m"
    ),
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    # Warm-up on case39 to exclude JIT from timing
    try
        tiny_file = joinpath(dirname(network_file), "case39.m")
        _data = PowerModels.parse_file(tiny_file)
        PowerModels.compute_dc_pf(_data)
    catch
        ;
    end

    t0 = time()
    try
        println("Loading network: $network_file")
        data = PowerModels.parse_file(network_file)

        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        n_gens = length(data["gen"])
        base_mva = data["baseMVA"]

        println(
            "Network loaded: $n_buses buses, $n_branches branches, $n_gens gens, baseMVA=$base_mva"
        )

        # Apply MEDIUM preprocessing
        n_x_fixed, n_rate_fixed = apply_medium_preprocessing!(data)
        println(
            "Preprocessing: $n_x_fixed branches with br_x→0.0001, $n_rate_fixed branches with rate_a→9999 MVA",
        )

        # Solve DC power flow (direct linear algebra, no JuMP)
        println("Solving DCPF...")
        pf_result = PowerModels.compute_dc_pf(data)

        term_status = pf_result["termination_status"]
        converged = is_converged(term_status)
        println("Termination status: $term_status  converged=$converged")

        if !converged
            push!(results["errors"], "DCPF did not converge: $term_status")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # Extract bus voltage angles
        bus_angles = Dict{String,Float64}()
        if haskey(pf_result, "solution") && haskey(pf_result["solution"], "bus")
            for (id, bus_sol) in pf_result["solution"]["bus"]
                bus_angles[id] = get(bus_sol, "va", 0.0)
            end
        end

        n_nonzero_angles = count(v -> abs(v) > 1e-8, values(bus_angles))
        println("Non-zero bus angles: $n_nonzero_angles / $n_buses")

        # Compute branch flows from angles (stable workaround)
        println("Computing branch flows from angles...")
        branch_flows_pu = compute_branch_flows(data, bus_angles)
        branch_flows_mw = Dict(k => v * base_mva for (k, v) in branch_flows_pu)

        n_nonzero_flows = count(v -> abs(v) > 1e-3, values(branch_flows_mw))
        println("Non-zero branch flows: $n_nonzero_flows / $n_branches")

        push!(
            results["workarounds"],
            "compute_dc_pf does not populate result[\"solution\"][\"branch\"]. " *
            "Branch flows computed manually from bus angles using DC PF formula " *
            "(va_from - va_to - shift) / (br_x * tap). Uses only public data dict " *
            "fields — stable workaround (same as TINY assessment).",
        )

        # Compute nodal injections
        nodal_injection_mw = Dict{String,Float64}()
        for (_, gen) in data["gen"]
            if gen["gen_status"] == 1
                bus_id = string(gen["gen_bus"])
                nodal_injection_mw[bus_id] =
                    get(nodal_injection_mw, bus_id, 0.0) + get(gen, "pg", 0.0) * base_mva
            end
        end
        for (_, load) in data["load"]
            if load["status"] == 1
                bus_id = string(load["load_bus"])
                nodal_injection_mw[bus_id] =
                    get(nodal_injection_mw, bus_id, 0.0) - get(load, "pd", 0.0) * base_mva
            end
        end

        # Angle range
        angle_min = minimum(values(bus_angles))
        angle_max = maximum(values(bus_angles))
        flow_min = minimum(values(branch_flows_mw))
        flow_max = maximum(values(branch_flows_mw))

        println(
            "Angle range: $(round(angle_min*180/pi, digits=3)) to $(round(angle_max*180/pi, digits=3)) deg",
        )
        println("Flow range: $(round(flow_min, digits=1)) to $(round(flow_max, digits=1)) MW")

        # Sample outputs
        sorted_buses = sort(collect(keys(bus_angles)); by=x->parse(Int, x))
        sorted_branches = sort(collect(keys(branch_flows_mw)); by=x->parse(Int, x))

        println("\n--- Bus Voltage Angles (first 10) ---")
        for bus_id in sorted_buses[1:min(10, end)]
            va_deg = bus_angles[bus_id] * 180.0 / pi
            println(
                "  Bus $bus_id: $(round(bus_angles[bus_id], digits=6)) rad  ($(round(va_deg, digits=4)) deg)",
            )
        end

        println("\n--- Branch Flows (first 10) ---")
        for br_id in sorted_branches[1:min(10, end)]
            f_bus = data["branch"][br_id]["f_bus"]
            t_bus = data["branch"][br_id]["t_bus"]
            rate_pu = get(data["branch"][br_id], "rate_a", 0.0)
            rate_mw = rate_pu * base_mva
            println(
                "  Branch $br_id ($f_bus→$t_bus): $(round(branch_flows_mw[br_id], digits=2)) MW  (limit: $(round(rate_mw, digits=1)) MW)",
            )
        end

        # Pass conditions
        non_trivial = n_nonzero_angles >= 1
        flows_accessible = length(branch_flows_pu) == n_branches
        angles_accessible = length(bus_angles) == n_buses

        println("\nPass checks:")
        println("  Converged:         $converged")
        println("  Non-trivial:       $non_trivial  ($n_nonzero_angles non-zero angles)")
        println("  Flows accessible:  $flows_accessible  ($(length(branch_flows_pu))/$n_branches)")
        println("  Angles accessible: $angles_accessible  ($(length(bus_angles))/$n_buses)")

        if converged && non_trivial && flows_accessible && angles_accessible
            results["status"] = "qualified_pass"
        else
            push!(
                results["errors"],
                "Core pass conditions not met: converged=$converged, non_trivial=$non_trivial, flows=$flows_accessible, angles=$angles_accessible",
            )
        end

        # Store summary (avoid full dicts — 10k buses is large)
        results["details"] = Dict(
            "network_file" => network_file,
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "n_x_fixed" => n_x_fixed,
            "n_rate_fixed" => n_rate_fixed,
            "termination_status" => string(term_status),
            "n_nonzero_angles" => n_nonzero_angles,
            "n_nonzero_flows" => n_nonzero_flows,
            "angle_range_deg" => [angle_min*180/pi, angle_max*180/pi],
            "flow_range_mw" => [flow_min, flow_max],
            "n_nodal_injections" => length(nodal_injection_mw),
            "solver" => "direct (Julia backslash via compute_dc_pf, no JuMP)",
            "branch_flow_method" => "computed from angles: (va_f - va_t - shift) / (br_x * tap)",
            "loc" => 135,
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        println("ERROR in A-1 MEDIUM: $(typeof(e)): $e")
        bt = catch_backtrace()
        println(sprint(showerror, e, bt))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    println("\nStatus: $(results["status"])")
    println("Wall clock: $(round(results["wall_clock_seconds"], digits=3))s")

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println("\n--- RESULT SUMMARY ---")
    println("status:             $(result["status"])")
    println("wall_clock_seconds: $(result["wall_clock_seconds"])")
    println("errors:             $(result["errors"])")
    println("workarounds:        $(result["workarounds"])")
    open("/tmp/a1_dcpf_medium_result.json", "w") do f
        JSON.print(f, result, 2)
    end
    println("Result written to /tmp/a1_dcpf_medium_result.json")
end

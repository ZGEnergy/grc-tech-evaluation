#=
Test G-FNM-3: DCPF Verification on Cleaned FNM Case

Dimension: fnm_ingestion
Network: LARGE (FNM 27,862-bus main island)
Pass condition: Per pass_conditions.json dcpf section:
  - Bus angle: >=95% of non-excluded buses within 1.0 deg tolerance
  - Branch flow: >=90% of in-service branches within 10% tolerance (floor 1.0 MW)
  - Hard fail: >20% bus or branch failures, or any branch >50% deviation
  - Bus injection power balance must pass
Tool: PowerModels.jl
Ingestion path: matpower_raw (MATPOWER .mat fallback)
Test hash: b318fdf1
=#

using PowerModels
using HiGHS
using JSON
using Printf

PowerModels.silence()

function parse_csv_lines(filepath::String)
    lines = readlines(filepath)
    header = split(lines[1], ',')
    rows = Vector{Dict{String,String}}()
    for i in 2:length(lines)
        line = strip(lines[i])
        isempty(line) && continue
        vals = split(line, ',')
        row = Dict{String,String}()
        for (j, h) in enumerate(header)
            row[strip(h)] = j <= length(vals) ? strip(vals[j]) : ""
        end
        push!(rows, row)
    end
    return rows
end

function apply_preprocessing!(data::Dict)
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
            branch["rate_a"] = 9999.0 / base_mva
            n_rate_fixed += 1
        end
    end
    return (n_x_fixed, n_rate_fixed)
end

function compute_branch_flows_mw(data::Dict, bus_va_rad::Dict{Int,Float64})
    base_mva = data["baseMVA"]
    flows = Dict{String,Float64}()
    for (br_id, branch) in data["branch"]
        if get(branch, "br_status", 1) == 0
            flows[br_id] = 0.0
            continue
        end
        f_bus = Int(branch["f_bus"])
        t_bus = Int(branch["t_bus"])
        br_x = branch["br_x"]
        tap = get(branch, "tap", 1.0)
        if tap == 0.0
            tap = 1.0
        end
        shift = get(branch, "shift", 0.0)
        va_f = get(bus_va_rad, f_bus, 0.0)
        va_t = get(bus_va_rad, t_bus, 0.0)
        if abs(br_x) < 1e-10
            flows[br_id] = 0.0
        else
            pf_pu = (va_f - va_t - shift) / (br_x * tap)
            flows[br_id] = pf_pu * base_mva
        end
    end
    return flows
end

function check_power_balance(data::Dict, bus_va_rad::Dict{Int,Float64})
    # Build net injection per bus (p.u.): gen_pg - load_pd
    base_mva = data["baseMVA"]
    bus_injection = Dict{Int,Float64}()
    bus_types = Dict{Int,Int}()

    for (_, bus) in data["bus"]
        bi = Int(bus["bus_i"])
        bus_injection[bi] = 0.0
        bus_types[bi] = Int(get(bus, "bus_type", 1))
    end

    # Generator injections (already in p.u. in PowerModels internal format)
    for (_, gen) in data["gen"]
        if get(gen, "gen_status", 1) != 0
            bi = Int(gen["gen_bus"])
            bus_injection[bi] = get(bus_injection, bi, 0.0) + gen["pg"]
        end
    end

    # Load withdrawals
    if haskey(data, "load") && !isempty(data["load"])
        for (_, load) in data["load"]
            if get(load, "status", 1) != 0
                bi = Int(load["load_bus"])
                bus_injection[bi] = get(bus_injection, bi, 0.0) - load["pd"]
            end
        end
    end

    # Shunt injections (gs contributes P loss: P_shunt = gs * V^2 ≈ gs for DCPF)
    if haskey(data, "shunt") && !isempty(data["shunt"])
        for (_, shunt) in data["shunt"]
            if get(shunt, "status", 1) != 0
                bi = Int(shunt["shunt_bus"])
                gs = get(shunt, "gs", 0.0)
                bus_injection[bi] = get(bus_injection, bi, 0.0) - gs  # gs consumes P
            end
        end
    end

    # Compute flow-out per bus from branches
    bus_flow_out = Dict{Int,Float64}()
    for bi in keys(bus_injection)
        bus_flow_out[bi] = 0.0
    end

    for (_, branch) in data["branch"]
        if get(branch, "br_status", 1) == 0
            continue
        end
        f_bus = Int(branch["f_bus"])
        t_bus = Int(branch["t_bus"])
        br_x = branch["br_x"]
        tap = get(branch, "tap", 1.0)
        if tap == 0.0
            ;
            tap = 1.0;
        end
        shift = get(branch, "shift", 0.0)
        va_f = get(bus_va_rad, f_bus, 0.0)
        va_t = get(bus_va_rad, t_bus, 0.0)
        if abs(br_x) >= 1e-10
            pf_pu = (va_f - va_t - shift) / (br_x * tap)
            bus_flow_out[f_bus] = get(bus_flow_out, f_bus, 0.0) + pf_pu
            bus_flow_out[t_bus] = get(bus_flow_out, t_bus, 0.0) - pf_pu
        end
    end

    # Mismatch = |injection - flow_out| for non-slack buses
    mismatches = Float64[]
    for (bi, inj) in bus_injection
        bt = get(bus_types, bi, 1)
        bt == 3 && continue  # skip slack
        flow_out = get(bus_flow_out, bi, 0.0)
        push!(mismatches, abs(inj - flow_out))
    end

    max_mm = isempty(mismatches) ? 0.0 : maximum(mismatches)
    mean_mm = isempty(mismatches) ? 0.0 : sum(mismatches) / length(mismatches)
    return (max_mm, mean_mm, length(mismatches))
end

function run(;
    matpower_file::String="/workspace/data/fnm/reference/cleaned/fnm_main_island.m",
    ref_bus_file::String="/workspace/data/fnm/reference/dcpf/buses_dcpf.csv",
    ref_branch_file::String="/workspace/data/fnm/reference/dcpf/branches_dcpf.csv",
    excluded_buses_file::String="/workspace/data/fnm/reference/excluded_buses.json",
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
        # 1. Load network
        println("Loading network: $matpower_file")
        data = PowerModels.parse_file(matpower_file)
        base_mva = data["baseMVA"]
        println("  baseMVA: $base_mva")
        println("  Buses: $(length(data["bus"]))")
        println("  Branches: $(length(data["branch"]))")
        println("  Generators: $(length(data["gen"]))")

        n_x_fixed, n_rate_fixed = apply_preprocessing!(data)
        println("  Preprocessing: $n_x_fixed zero-reactance, $n_rate_fixed rate fixes")

        # 2. Load excluded buses
        excluded_set = Set{Int}()
        if isfile(excluded_buses_file)
            exc_data = JSON.parsefile(excluded_buses_file)
            for bus_entry in exc_data["excluded_buses"]
                push!(excluded_set, bus_entry["bus_number"])
            end
            println("  Excluded buses: $(length(excluded_set))")
        end

        # 3. Solve DCPF using solve_dc_pf with explicit DCPPowerModel
        println("\nSolving DCPF with solve_dc_pf(data, DCPPowerModel, HiGHS)...")
        t_solve = time()
        result_pf = PowerModels.solve_dc_pf(data, HiGHS.Optimizer)
        solve_time = time() - t_solve
        println("  Solve time: $(@sprintf("%.2f", solve_time))s")
        println("  Termination: $(result_pf["termination_status"])")

        # Check trivial solution
        bus_solution = result_pf["solution"]["bus"]
        nonzero_va_count = 0
        for (_, bus_sol) in bus_solution
            if abs(get(bus_sol, "va", 0.0)) > 1e-10
                nonzero_va_count += 1
            end
        end
        println("  Nonzero VA: $nonzero_va_count / $(length(bus_solution))")

        if nonzero_va_count < 100
            push!(results["errors"], "Trivial solution: only $nonzero_va_count nonzero VA buses")
            results["details"]["trivial_solution"] = true
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # Extract bus VA (radians -> degrees)
        bus_va_rad = Dict{Int,Float64}()
        bus_va_deg = Dict{Int,Float64}()
        for (bus_id_str, bus_sol) in bus_solution
            bus_i = Int(data["bus"][bus_id_str]["bus_i"])
            va_rad = get(bus_sol, "va", 0.0)
            bus_va_rad[bus_i] = va_rad
            bus_va_deg[bus_i] = rad2deg(va_rad)
        end

        # 4. Power balance check
        println("\n=== Power Balance Check ===")
        max_mm, mean_mm, n_checked = check_power_balance(data, bus_va_rad)
        println("  Buses checked (excl. slack): $n_checked")
        println("  Max mismatch: $(@sprintf("%.6e", max_mm)) p.u.")
        println("  Mean mismatch: $(@sprintf("%.6e", mean_mm)) p.u.")
        balance_ok = max_mm < 1e-4
        println("  Balance check (<1e-4 p.u.): $(balance_ok ? "PASS" : "FAIL")")

        # Compute branch flows
        branch_flows_mw = compute_branch_flows_mw(data, bus_va_rad)

        # 5. Load reference data
        println("\nLoading reference data...")
        ref_buses = parse_csv_lines(ref_bus_file)
        ref_branches = parse_csv_lines(ref_branch_file)
        println("  Reference buses: $(length(ref_buses))")
        println("  Reference branches: $(length(ref_branches))")

        # 6. Bus angle comparison
        println("\n=== Bus Angle Comparison ===")
        n_non_excluded = 0
        n_bus_pass = 0
        n_bus_fail = 0
        bus_deviations = Float64[]
        failing_bus_devs = Dict{Int,Float64}()

        for row in ref_buses
            bus_num = parse(Int, row["bus_number"])
            bus_num in excluded_set && continue
            n_non_excluded += 1
            ref_va = parse(Float64, row["va_deg"])
            tool_va = get(bus_va_deg, bus_num, nothing)

            if tool_va === nothing
                n_bus_fail += 1
                continue
            end

            dev = abs(tool_va - ref_va)
            push!(bus_deviations, dev)

            if dev < 1.0
                n_bus_pass += 1
            else
                n_bus_fail += 1
                failing_bus_devs[bus_num] = dev
            end
        end

        bus_pass_frac = n_non_excluded > 0 ? n_bus_pass / n_non_excluded : 0.0
        println("  Non-excluded: $n_non_excluded")
        println("  Passing (<1.0 deg): $n_bus_pass ($(@sprintf("%.2f", 100*bus_pass_frac))%)")
        println("  Failing: $n_bus_fail")

        if !isempty(bus_deviations)
            sorted_bd = sort(bus_deviations)
            mean_dev = sum(sorted_bd) / length(sorted_bd)
            median_dev = sorted_bd[div(length(sorted_bd), 2) + 1]
            max_dev = sorted_bd[end]
            p95_idx = max(1, Int(ceil(0.95 * length(sorted_bd))))
            p95_dev = sorted_bd[p95_idx]
            println("  Mean dev: $(@sprintf("%.6e", mean_dev)) deg")
            println("  Median dev: $(@sprintf("%.6e", median_dev)) deg")
            println("  Max dev: $(@sprintf("%.6e", max_dev)) deg")
            println("  P95 dev: $(@sprintf("%.6e", p95_dev)) deg")
        end

        # 7. Branch flow comparison
        println("\n=== Branch Flow Comparison ===")
        branch_lookup = Dict{Tuple{Int,Int},Vector{String}}()
        for (br_id, branch) in data["branch"]
            f = Int(branch["f_bus"])
            t = Int(branch["t_bus"])
            key = (min(f, t), max(f, t))
            if !haskey(branch_lookup, key)
                branch_lookup[key] = String[]
            end
            push!(branch_lookup[key], br_id)
        end

        n_in_service = 0
        n_branch_pass = 0
        n_branch_fail = 0
        branch_dev_pcts = Float64[]
        worst_dev_pct = 0.0
        worst_info = ""

        for row in ref_branches
            status = parse(Int, row["status"])
            status == 0 && continue
            n_in_service += 1
            ref_pf = parse(Float64, row["pf_mw"])
            f_bus = parse(Int, row["from_bus"])
            t_bus = parse(Int, row["to_bus"])

            key = (min(f_bus, t_bus), max(f_bus, t_bus))
            br_ids = get(branch_lookup, key, String[])

            if isempty(br_ids)
                n_branch_fail += 1
                push!(branch_dev_pcts, 100.0)
                continue
            end

            best_pct = Inf
            for br_id in br_ids
                tool_pf = get(branch_flows_mw, br_id, 0.0)
                dev1 = abs(tool_pf - ref_pf)
                dev2 = abs(-tool_pf - ref_pf)
                dev = min(dev1, dev2)
                base = max(abs(ref_pf), 1.0)
                pct = (dev / base) * 100.0
                if pct < best_pct
                    best_pct = pct
                end
            end

            push!(branch_dev_pcts, best_pct)
            if best_pct < 10.0
                n_branch_pass += 1
            else
                n_branch_fail += 1
            end
            if best_pct > worst_dev_pct
                worst_dev_pct = best_pct
                worst_info = "($f_bus,$t_bus): $(@sprintf("%.2f", best_pct))%"
            end
        end

        branch_pass_frac = n_in_service > 0 ? n_branch_pass / n_in_service : 0.0
        println("  In-service: $n_in_service")
        println("  Passing (<10%): $n_branch_pass ($(@sprintf("%.2f", 100*branch_pass_frac))%)")
        println("  Failing: $n_branch_fail")
        println("  Worst: $worst_info")

        if !isempty(branch_dev_pcts)
            sorted_bp = sort(branch_dev_pcts)
            println("  Mean dev: $(@sprintf("%.6e", sum(sorted_bp)/length(sorted_bp)))%")
            println("  Median dev: $(@sprintf("%.6e", sorted_bp[div(length(sorted_bp),2)+1]))%")
            println("  Max dev: $(@sprintf("%.6e", sorted_bp[end]))%")
            p95_idx = max(1, Int(ceil(0.95 * length(sorted_bp))))
            println("  P95 dev: $(@sprintf("%.6e", sorted_bp[p95_idx]))%")
        end

        # 8. Hard-fail checks
        hard_fail = false
        hard_fail_reasons = String[]

        bus_fail_frac = n_non_excluded > 0 ? n_bus_fail / n_non_excluded : 0.0
        if bus_fail_frac > 0.2
            hard_fail = true
            push!(hard_fail_reasons, "Bus fail frac $(@sprintf("%.1f", bus_fail_frac*100))% > 20%")
        end

        branch_fail_frac = n_in_service > 0 ? n_branch_fail / n_in_service : 0.0
        if branch_fail_frac > 0.2
            hard_fail = true
            push!(
                hard_fail_reasons,
                "Branch fail frac $(@sprintf("%.1f", branch_fail_frac*100))% > 20%",
            )
        end

        if worst_dev_pct > 50.0
            hard_fail = true
            push!(hard_fail_reasons, "Extreme branch dev $(@sprintf("%.1f", worst_dev_pct))% > 50%")
        end

        # 9. Transformer formulation difference analysis (6-step procedure)
        println("\n=== Formulation Difference Analysis ===")

        # Step 1: Identify transformer-connected buses
        xfmr_buses = Set{Int}()
        n_xfmr = 0
        n_off_nominal = 0
        for (_, branch) in data["branch"]
            if get(branch, "transformer", false)
                n_xfmr += 1
                push!(xfmr_buses, Int(branch["f_bus"]))
                push!(xfmr_buses, Int(branch["t_bus"]))
                tap = get(branch, "tap", 1.0)
                if tap != 0.0 && abs(tap - 1.0) > 1e-6
                    n_off_nominal += 1
                end
            end
        end
        println("  Transformers: $n_xfmr")
        println("  Off-nominal tap: $n_off_nominal / $n_xfmr")
        println("  Transformer-connected buses: $(length(xfmr_buses))")

        # Step 2: Classify failing buses
        n_xfmr_related = 0
        n_non_xfmr = 0
        xfmr_devs = Float64[]
        non_xfmr_devs = Float64[]
        for (bus_num, dev) in failing_bus_devs
            if bus_num in xfmr_buses
                n_xfmr_related += 1
                push!(xfmr_devs, dev)
            else
                n_non_xfmr += 1
                push!(non_xfmr_devs, dev)
            end
        end

        total_failing = n_xfmr_related + n_non_xfmr
        xfmr_pct = total_failing > 0 ? 100.0 * n_xfmr_related / total_failing : 0.0
        formulation_diff = n_xfmr_related > 0 && n_xfmr_related > n_non_xfmr

        println("  Transformer-related failing: $n_xfmr_related ($(@sprintf("%.1f", xfmr_pct))%)")
        println("  Non-transformer failing: $n_non_xfmr")
        if !isempty(xfmr_devs)
            println("  Mean xfmr dev: $(@sprintf("%.6e", sum(xfmr_devs)/length(xfmr_devs))) deg")
        end
        if !isempty(non_xfmr_devs)
            println(
                "  Mean non-xfmr dev: $(@sprintf("%.6e", sum(non_xfmr_devs)/length(non_xfmr_devs))) deg",
            )
        end
        println("  Formulation difference classification: $formulation_diff")

        # 10. Store results (scientific notation for deviations)
        results["details"] = Dict(
            "solve_time_seconds" => round(solve_time; digits=2),
            "termination_status" => string(result_pf["termination_status"]),
            "base_mva" => base_mva,
            "nonzero_va_buses" => nonzero_va_count,
            "power_balance" => Dict(
                "max_mismatch_pu" => @sprintf("%.6e", max_mm),
                "mean_mismatch_pu" => @sprintf("%.6e", mean_mm),
                "buses_checked" => n_checked,
                "pass" => balance_ok,
            ),
            "bus_angle" => Dict(
                "non_excluded_total" => n_non_excluded,
                "passing" => n_bus_pass,
                "failing" => n_bus_fail,
                "pass_fraction" => round(bus_pass_frac; digits=6),
                "mean_dev_deg" => if isempty(bus_deviations)
                    nothing
                else
                    @sprintf("%.6e", sum(bus_deviations) / length(bus_deviations))
                end,
                "max_dev_deg" => if isempty(bus_deviations)
                    nothing
                else
                    @sprintf("%.6e", maximum(bus_deviations))
                end,
                "p95_dev_deg" => if isempty(bus_deviations)
                    nothing
                else
                    @sprintf(
                        "%.6e",
                        sort(bus_deviations)[max(1, Int(ceil(0.95 * length(bus_deviations))))]
                    )
                end,
            ),
            "branch_flow" => Dict(
                "in_service_total" => n_in_service,
                "passing" => n_branch_pass,
                "failing" => n_branch_fail,
                "pass_fraction" => round(branch_pass_frac; digits=6),
                "mean_dev_pct" => if isempty(branch_dev_pcts)
                    nothing
                else
                    @sprintf("%.6e", sum(branch_dev_pcts) / length(branch_dev_pcts))
                end,
                "max_dev_pct" => @sprintf("%.6e", worst_dev_pct),
                "worst_branch" => worst_info,
            ),
            "hard_fail" => hard_fail,
            "hard_fail_reasons" => hard_fail_reasons,
            "formulation_difference" => Dict(
                "detected" => formulation_diff,
                "xfmr_related_outliers" => n_xfmr_related,
                "non_xfmr_outliers" => n_non_xfmr,
                "total_transformers" => n_xfmr,
                "off_nominal_tap_transformers" => n_off_nominal,
                "xfmr_connected_buses" => length(xfmr_buses),
            ),
            "preprocessing" =>
                Dict("zero_reactance_fixes" => n_x_fixed, "rate_fixes" => n_rate_fixed),
        )

        # 11. Determine pass/fail
        if !balance_ok
            results["status"] = "fail"
            push!(
                results["errors"],
                "Power balance check failed: max mismatch $(@sprintf("%.6e", max_mm)) p.u. >= 1e-4",
            )
        elseif hard_fail
            results["status"] = "fail"
            for r in hard_fail_reasons
                push!(results["errors"], "Hard fail: $r")
            end
        elseif bus_pass_frac >= 0.95 && branch_pass_frac >= 0.90
            if formulation_diff
                results["status"] = "qualified_pass"
                push!(
                    results["workarounds"],
                    "Deviations cluster near transformer buses — formulation difference " *
                    "(DCPPowerModel simplified B-matrix vs reference full B-matrix)",
                )
            else
                results["status"] = "pass"
            end
        else
            results["status"] = "fail"
            if bus_pass_frac < 0.95
                push!(
                    results["errors"],
                    "Bus angle pass fraction $(@sprintf("%.1f", bus_pass_frac * 100))% < 95%",
                )
            end
            if branch_pass_frac < 0.90
                push!(
                    results["errors"],
                    "Branch flow pass fraction $(@sprintf("%.1f", branch_pass_frac * 100))% < 90%",
                )
            end
        end

        println("\n=== STATUS: $(results["status"]) ===")

    catch e
        push!(results["errors"], "$(typeof(e)): $(sprint(showerror, e))")
        results["details"]["traceback"] = sprint(io -> Base.showerror(io, e, catch_backtrace()))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    println("JIT warm-up...")
    warmup_data = PowerModels.parse_file("/workspace/data/networks/case39.m")
    PowerModels.solve_dc_pf(warmup_data, HiGHS.Optimizer)
    println("Warm-up complete.\n")

    result = run()
    println("\n=== FINAL RESULTS ===")
    println(JSON.json(result, 2))
end

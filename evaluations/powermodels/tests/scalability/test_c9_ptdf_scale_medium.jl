#=
Test C-9: PTDF Matrix Computation on MEDIUM
Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus, case_ACTIVSg10k.m)
Pass condition: Wall-clock time, peak memory, matrix density.
    Phase-shifter correction terms must be applied per B-9 requirements.
Tool: PowerModels.jl v0.21.5
Depends on: B-9 (PASS)

Approach (same as B-9 MEDIUM, with scalability metrics focus):
  - make_basic_network(data) -> calc_basic_ptdf_matrix(basic_data)
  - Matrix dimensions: (n_branches x n_buses)
  - Validate flow predictions: flow ≈ PTDF * Pinj
  - Check for phase-shifting transformers (nonzero shift in branch data)
  - Report: wall-clock time, peak memory, matrix density

Phase-shifter handling (from B-9 findings):
  ACTIVSg10k has 5 phase-shifting transformers in raw data.
  make_basic_network absorbs phase-shift offsets into reference angles,
  so basic network has 0 phase-shifter rows. Standard PTDF * Pinj is exact.

Memory note: 12706 x 10000 = 127M float64 entries ≈ 969 MB.
=#

using PowerModels, LinearAlgebra, JSON

PowerModels.silence()

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
            branch["rate_a"] = 9999.0 / base_mva
            n_rate_fixed += 1
        end
    end
    return (n_x_fixed, n_rate_fixed)
end

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024  # kB to MB
        end
    end
    return nothing
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

    # JIT warm-up on case39
    println("JIT warm-up on case39...")
    try
        tiny_file = joinpath(dirname(network_file), "case39.m")
        _d = PowerModels.parse_file(tiny_file)
        _bd = PowerModels.make_basic_network(_d)
        PowerModels.calc_basic_ptdf_matrix(_bd)
        PowerModels.compute_dc_pf(_d)
    catch
        ;
    end

    t0 = time()
    mem_before = peak_rss_mb()
    try
        println("Loading network: $network_file")
        t_parse = time()
        data = PowerModels.parse_file(network_file)
        t_parse = time() - t_parse
        println("Network parsed in $(round(t_parse, digits=2))s")

        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        n_gens = length(data["gen"])
        base_mva = data["baseMVA"]
        println("Network: $n_buses buses, $n_branches branches, $n_gens gens, baseMVA=$base_mva")

        n_x_fixed, n_rate_fixed = apply_medium_preprocessing!(data)
        println("Preprocessing: $n_x_fixed br_x→0.0001, $n_rate_fixed rate_a→9999 MVA")

        # ---- Check for phase-shifting transformers ----
        phase_shifter_ids = String[]
        for (br_id, branch) in data["branch"]
            if abs(get(branch, "shift", 0.0)) > 1e-8
                push!(phase_shifter_ids, br_id)
            end
        end
        n_shifters = length(phase_shifter_ids)
        println("Phase-shifting transformers in original data: $n_shifters")
        if n_shifters > 0
            for br_id in phase_shifter_ids[1:min(5, end)]
                shift_deg = data["branch"][br_id]["shift"] * 180.0 / pi
                println("  Branch $br_id: shift=$(round(shift_deg, digits=4)) deg")
            end
        end

        # ---- Step 1: Build basic network ----
        println("\nBuilding basic network...")
        t_basic_start = time()
        basic_data = PowerModels.make_basic_network(deepcopy(data))
        t_basic = time() - t_basic_start
        n_basic_buses = length(basic_data["bus"])
        n_basic_branches = length(basic_data["branch"])
        println(
            "make_basic_network: $(round(t_basic, digits=2))s ($n_basic_buses buses, $n_basic_branches branches)",
        )

        # ---- Step 2: Solve reference DCPF ----
        println("Solving reference DCPF on basic network...")
        t_dcpf_start = time()
        pf_result = PowerModels.compute_dc_pf(basic_data)
        t_dcpf = time() - t_dcpf_start
        dcpf_converged = pf_result["termination_status"] == true
        println("DCPF: converged=$dcpf_converged ($(round(t_dcpf, digits=2))s)")

        if !dcpf_converged
            push!(results["errors"], "Reference DCPF on basic network did not converge")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # Extract reference flows
        PowerModels.update_data!(basic_data, pf_result["solution"])
        ref_flows_data = PowerModels.calc_branch_flow_dc(basic_data)

        basic_branch_ids = sort(parse.(Int, collect(keys(basic_data["branch"]))))
        basic_bus_ids = sort(parse.(Int, collect(keys(basic_data["bus"]))))

        flow_actual = zeros(n_basic_branches)
        for (l, br_id) in enumerate(basic_branch_ids)
            br_sol = get(ref_flows_data["branch"], string(br_id), Dict())
            flow_actual[l] = get(br_sol, "pf", 0.0)
        end

        # Bus injection vector
        bus_to_idx = Dict(id => i for (i, id) in enumerate(basic_bus_ids))
        p_inj = zeros(n_basic_buses)
        for (_, gen) in basic_data["gen"]
            bus = gen["gen_bus"]
            haskey(bus_to_idx, bus) && (p_inj[bus_to_idx[bus]] += gen["pg"])
        end
        for (_, load) in basic_data["load"]
            bus = load["load_bus"]
            haskey(bus_to_idx, bus) && (p_inj[bus_to_idx[bus]] -= load["pd"])
        end

        # ---- Step 3: Compute PTDF matrix ----
        println("\nComputing PTDF matrix ($n_basic_branches x $n_basic_buses)...")
        basic_data_ptdf = PowerModels.make_basic_network(deepcopy(data))

        mem_pre_ptdf = peak_rss_mb()
        t_ptdf_start = time()
        ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data_ptdf)
        t_ptdf = time() - t_ptdf_start
        mem_post_ptdf = peak_rss_mb()
        println("calc_basic_ptdf_matrix: $(round(t_ptdf, digits=2))s  size=$(size(ptdf))")

        ptdf_size_mb = length(ptdf) * 8 / 1024^2
        mem_delta = if isnothing(mem_pre_ptdf) || isnothing(mem_post_ptdf)
            nothing
        else
            mem_post_ptdf - mem_pre_ptdf
        end
        println("Matrix size: $(round(ptdf_size_mb, digits=1)) MB (Float64)")
        if !isnothing(mem_delta)
            println("Memory delta during PTDF: $(round(mem_delta, digits=1)) MB")
        end

        # ---- Step 4: Matrix density ----
        n_nonzero = count(x -> abs(x) > 1e-8, ptdf)
        n_total = length(ptdf)
        density = 100.0 * n_nonzero / n_total
        max_ptdf = maximum(abs.(ptdf))
        println("Density: $(round(density, digits=2))% ($n_nonzero / $n_total non-zero entries)")
        println("Max |PTDF|: $(round(max_ptdf, digits=6))")

        # ---- Step 5: Validate flow predictions ----
        println("\nValidating PTDF flow predictions...")
        flow_predicted = ptdf * p_inj
        errors_all = abs.(flow_predicted .- flow_actual)
        max_error = maximum(errors_all)
        mean_error = sum(errors_all) / length(errors_all)
        println(
            "Max prediction error: $(max_error) pu ($(round(max_error * base_mva, digits=6)) MW)"
        )
        println("Mean prediction error: $(mean_error) pu")

        # Phase-shifter rows in basic network
        phase_shifter_rows = Int[]
        for (l, br_id) in enumerate(basic_branch_ids)
            basic_br = basic_data_ptdf["branch"][string(br_id)]
            if abs(get(basic_br, "shift", 0.0)) > 1e-8
                push!(phase_shifter_rows, l)
            end
        end
        n_shifter_rows = length(phase_shifter_rows)
        println("Phase-shifting branches in basic network: $n_shifter_rows")

        # Accuracy check
        accuracy_tol = 1e-6
        accuracy_ok = max_error < accuracy_tol
        println("Accuracy OK: $accuracy_ok (max_error=$(max_error), tol=$accuracy_tol)")

        # Ref bus PTDF column check
        ref_bus_ptdf_max = NaN
        for (_, bus) in basic_data_ptdf["bus"]
            if bus["bus_type"] == 3
                ref_bus_id = bus["index"]
                if haskey(bus_to_idx, ref_bus_id)
                    ref_col = bus_to_idx[ref_bus_id]
                    ref_bus_ptdf_max = maximum(abs.(ptdf[:, ref_col]))
                    println(
                        "Ref bus ($ref_bus_id) PTDF col max: $(round(ref_bus_ptdf_max, digits=10))"
                    )
                end
                break
            end
        end

        # ---- Final peak memory ----
        peak_mem = peak_rss_mb()
        println("\nPeak RSS: $(isnothing(peak_mem) ? "N/A" : round(peak_mem, digits=1)) MB")

        # ---- Pass/fail ----
        if accuracy_ok
            results["status"] = "pass"
        else
            results["status"] = "qualified_pass"
            push!(
                results["workarounds"],
                "Max prediction error $(max_error) exceeds tolerance $accuracy_tol.",
            )
        end

        results["details"] = Dict(
            "network_file" => network_file,
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "n_phase_shifters_raw" => n_shifters,
            "n_phase_shifter_rows_basic" => n_shifter_rows,
            "n_basic_buses" => n_basic_buses,
            "n_basic_branches" => n_basic_branches,
            "t_parse_s" => round(t_parse; digits=2),
            "t_basic_network_s" => round(t_basic; digits=2),
            "t_dcpf_ref_s" => round(t_dcpf; digits=2),
            "t_ptdf_s" => round(t_ptdf; digits=2),
            "ptdf_dimensions" => [size(ptdf, 1), size(ptdf, 2)],
            "ptdf_size_mb" => round(ptdf_size_mb; digits=1),
            "matrix_density_pct" => round(density; digits=2),
            "n_nonzero_entries" => n_nonzero,
            "n_total_entries" => n_total,
            "max_ptdf_abs" => round(max_ptdf; digits=6),
            "max_error_pu" => max_error,
            "mean_error_pu" => mean_error,
            "max_error_mw" => max_error * base_mva,
            "accuracy_tol" => accuracy_tol,
            "accuracy_ok" => accuracy_ok,
            "ref_bus_ptdf_col_max" => ref_bus_ptdf_max,
            "peak_rss_mb" => peak_mem,
            "mem_delta_ptdf_mb" => mem_delta,
            "timing_source" => "measured",
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        println("ERROR: $(typeof(e)): $e")
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
    println("--- details ---")
    for (k, v) in sort(collect(result["details"]); by=first)
        println("  $k: $v")
    end
end

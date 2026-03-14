#=
Test C-9: PTDF Matrix on MEDIUM (ACTIVSg 10k)

Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus, 12706 branches, 2485 generators)
Pass condition: Completes. Wall-clock, peak memory, matrix density.
Tool: PowerSimulations.jl v0.30.2 (PowerNetworkMatrices.jl v0.12.1)
=#

using PowerSystems
using PowerNetworkMatrices
using JSON
using Logging
using SparseArrays

# Suppress verbose logging
global_logger(ConsoleLogger(stderr, Logging.Error))

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024  # kB to MB
        end
    end
    return nothing
end

function cpu_core_count()
    count = 0
    for line in eachline("/proc/cpuinfo")
        if startswith(line, "processor")
            count += 1
        end
    end
    return count
end

function run(network_file::String="/workspace/data/networks/case_ACTIVSg10k.m")
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    try
        cores = cpu_core_count()
        results["details"]["cpu_cores_available"] = cores

        # Load system
        println(stderr, "Loading MEDIUM (10k bus) system...")
        t_load = time()
        sys = System(network_file)
        elapsed_load = time() - t_load
        println(stderr, "System loaded in $(round(elapsed_load, digits=2))s")

        base_power = get_base_power(sys)
        n_buses = length(collect(get_components(Bus, sys)))
        n_branches = length(collect(get_components(Branch, sys)))

        results["details"]["base_power_mva"] = base_power
        results["details"]["n_buses"] = n_buses
        results["details"]["n_branches"] = n_branches
        results["details"]["load_time_seconds"] = round(elapsed_load; digits=3)

        # Check for phase-shifting transformers
        n_tap_xfmrs = length(collect(get_components(TapTransformer, sys)))
        n_phase_shifters = 0
        phase_shifter_names = String[]
        for xfmr in get_components(TapTransformer, sys)
            # Phase shifters have non-zero phase shift angle
            # In PowerSystems.jl, TapTransformer has a `tap` field
            # PhaseShiftingTransformer is a separate type if it exists
            # Check for non-unity tap ratio as indicator
            tap = get_tap(xfmr)
            if abs(tap - 1.0) > 0.01
                n_phase_shifters += 1
                push!(phase_shifter_names, get_name(xfmr))
            end
        end

        # Also check for PhaseShiftingTransformer type
        n_pst = 0
        pst_names = String[]
        try
            for pst in get_components(PhaseShiftingTransformer, sys)
                n_pst += 1
                push!(pst_names, get_name(pst))
            end
        catch
            ;
        end

        results["details"]["transformers"] = Dict(
            "n_tap_transformers" => n_tap_xfmrs,
            "n_nonunity_tap" => n_phase_shifters,
            "nonunity_tap_names" => phase_shifter_names[1:min(10, length(phase_shifter_names))],
            "n_phase_shifting_transformers" => n_pst,
            "phase_shifting_names" => pst_names[1:min(10, length(pst_names))],
        )

        mem_before_ptdf = peak_rss_mb()
        results["details"]["peak_memory_before_ptdf_mb"] = mem_before_ptdf

        # JIT warm-up: compute PTDF once
        println(stderr, "JIT warm-up PTDF computation...")
        t_warmup = time()
        try
            _ = PTDF(sys)
            elapsed_warmup = time() - t_warmup
            println(stderr, "Warm-up PTDF done in $(round(elapsed_warmup, digits=2))s")
            results["details"]["warmup_seconds"] = round(elapsed_warmup; digits=3)
        catch e
            elapsed_warmup = time() - t_warmup
            println(
                stderr, "Warm-up PTDF error: $(typeof(e)) after $(round(elapsed_warmup, digits=2))s"
            )
            results["details"]["warmup_seconds"] = round(elapsed_warmup; digits=3)
            results["details"]["warmup_error"] = string(typeof(e))
        end

        mem_after_warmup = peak_rss_mb()
        results["details"]["peak_memory_after_warmup_mb"] = mem_after_warmup

        # Timed PTDF computation
        println(stderr, "Timed PTDF computation...")
        t0 = time()
        ptdf = PTDF(sys)
        elapsed = time() - t0
        println(stderr, "PTDF computed in $(round(elapsed, digits=3))s")

        results["wall_clock_seconds"] = round(elapsed; digits=3)
        results["details"]["peak_memory_mb"] = peak_rss_mb()

        # Extract matrix properties
        # PTDF object wraps a matrix — access via get_data or similar
        ptdf_data = nothing
        try
            ptdf_data = get_data(ptdf)
        catch
            try
                ptdf_data = ptdf.data
            catch
                ;
            end
        end

        if ptdf_data !== nothing
            n_rows, n_cols = size(ptdf_data)
            results["details"]["matrix_dimensions"] = Dict(
                "rows" => n_rows,
                "cols" => n_cols,
                "expected_rows_branches" => n_branches,
                "expected_cols_buses" => n_buses,
            )

            # Density analysis
            if ptdf_data isa SparseArrays.AbstractSparseMatrix
                nnz_count = SparseArrays.nnz(ptdf_data)
                total_elements = n_rows * n_cols
                density = nnz_count / total_elements
                results["details"]["matrix_storage"] = Dict(
                    "format" => "sparse",
                    "nnz" => nnz_count,
                    "total_elements" => total_elements,
                    "density" => round(density; digits=6),
                    "density_pct" => round(density * 100.0; digits=4),
                )
            else
                # Dense matrix — compute density from non-zero elements
                total_elements = n_rows * n_cols
                nnz_count = count(x -> abs(x) > 1e-10, ptdf_data)
                density = nnz_count / total_elements
                results["details"]["matrix_storage"] = Dict(
                    "format" => "dense",
                    "nnz_above_1e10" => nnz_count,
                    "total_elements" => total_elements,
                    "density" => round(density; digits=6),
                    "density_pct" => round(density * 100.0; digits=4),
                    "memory_estimate_mb" => round(total_elements * 8 / 1024 / 1024; digits=1),
                )
            end

            # Value range
            vals = vec(collect(ptdf_data))
            results["details"]["value_range"] = Dict(
                "min" => round(minimum(vals); digits=6),
                "max" => round(maximum(vals); digits=6),
                "mean_abs" => round(sum(abs.(vals)) / length(vals); digits=6),
            )

            # Check for expected PTDF properties
            # Row sums should be ~0 for non-radial networks (conservation)
            # Column for slack bus should be ~0
            row_sums = [sum(ptdf_data[i, :]) for i in 1:n_rows]
            results["details"]["row_sum_check"] = Dict(
                "mean_abs_row_sum" => round(sum(abs.(row_sums)) / length(row_sums); digits=8),
                "max_abs_row_sum" => round(maximum(abs.(row_sums)); digits=8),
            )
        else
            results["details"]["matrix_access_error"] = "Could not access PTDF matrix data"
        end

        # Memory delta
        mem_delta = peak_rss_mb() - (mem_before_ptdf !== nothing ? mem_before_ptdf : 0.0)
        results["details"]["memory_delta_mb"] = round(mem_delta; digits=1)

        # Pass checks
        results["details"]["pass_checks"] = Dict(
            "completed" => true,
            "has_matrix_data" => ptdf_data !== nothing,
            "dimensions_plausible" =>
                ptdf_data !== nothing && size(ptdf_data, 1) > 0 && size(ptdf_data, 2) > 0,
        )

        if ptdf_data !== nothing
            results["status"] = "pass"
        else
            push!(results["errors"], "PTDF computed but matrix data not accessible")
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

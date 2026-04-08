#=
Test G-FNM-4: ACPF Convergence (DCPF warm-start + progressive relaxation)

Dimension: fnm_ingestion
Network: LARGE (FNM main island via MATPOWER fallback, 28000 buses)
Pass condition: No hard gate. All outcomes are diagnostic.
  Record relaxation_level_achieved: 0%, 10%, 20%, or infeasible.
Tool: PowerSimulations.jl v0.30.2 (PowerSystems.jl v4.6.2, PowerFlows.jl v0.9.0)
=#

using Logging
using PowerSystems: PowerSystems
using PowerFlows: PowerFlows
using JSON: JSON

const PS = PowerSystems
const PF = PowerFlows

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024  # kB to MB
        end
    end
    return nothing
end

function run_test(;
    matpower_file::String="/workspace/data/fnm/reference/cleaned/fnm_main_island.m",
    acpf_timeout_minutes::Int=30,
)
    results = Dict(
        "status" => "informational",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    # Suppress verbose logging
    logger = ConsoleLogger(stderr, Logging.Error)
    global_logger(logger)

    t0 = time()
    try
        # --- Step 1: Load network and solve DCPF for warm-start ---
        println("Step 1: Loading network and solving DCPF for warm-start...")
        t_load = time()
        sys = PS.System(matpower_file; runchecks=false)
        load_elapsed = time() - t_load
        println("  Network loaded in $(round(load_elapsed, digits=2))s")

        bus_count = length(collect(PS.get_components(PS.ACBus, sys)))
        println("  Bus count: $bus_count")

        println("  Solving DCPF...")
        t_dc = time()
        dc_result = PF.solve_powerflow(PF.DCPowerFlow(), sys)
        dc_elapsed = time() - t_dc
        println("  DCPF solved in $(round(dc_elapsed, digits=2))s")

        # Extract DCPF angles for warm-start diagnostics
        timestep_key = first(keys(dc_result))
        bus_df = dc_result[timestep_key]["bus_results"]

        # Bus angles are in radians
        angles_rad = bus_df.θ
        angles_deg = rad2deg.(angles_rad)
        nonzero_mask = abs.(angles_deg) .> 1e-10

        dcpf_init_mean_deg = mean(abs.(angles_deg[nonzero_mask]))
        dcpf_init_max_abs_deg = maximum(abs.(angles_deg))

        println("  DCPF warm-start angle stats:")
        println("    Mean |angle| (non-zero): $(round(dcpf_init_mean_deg, digits=4)) deg")
        println("    Max |angle|: $(round(dcpf_init_max_abs_deg, digits=4)) deg")
        println("    Non-zero angles: $(count(nonzero_mask)) / $(length(angles_deg))")

        results["details"]["dcpf_init_mean_deg"] = dcpf_init_mean_deg
        results["details"]["dcpf_init_max_abs_deg"] = dcpf_init_max_abs_deg
        results["details"]["dcpf_solve_seconds"] = dc_elapsed

        # Apply DCPF angles as warm-start to the System
        # PowerFlows.solve_powerflow! updates the system in-place after DCPF
        # We need to reload and set angles manually for AC
        println("\n  Setting DCPF angles on System buses for ACPF warm-start...")
        # Build angle map from DCPF results
        angle_map = Dict{Int,Float64}()
        for row in eachrow(bus_df)
            angle_map[row.bus_number] = row.θ  # radians
        end

        # Set bus angles from DCPF solution (VM stays at 1.0 pu for warm-start)
        for bus in PS.get_components(PS.ACBus, sys)
            bus_num = PS.get_number(bus)
            if haskey(angle_map, bus_num)
                PS.set_angle!(bus, angle_map[bus_num])
            end
            # Keep VM at 1.0 pu (default from MATPOWER load or generator setpoint)
        end

        # --- Step 2: ACPF at 0% relaxation ---
        println("\nStep 2: ACPF at 0% relaxation (no branch limit changes)...")
        relaxation_level_achieved = "infeasible"
        acpf_converged = false
        acpf_seconds = 0.0

        t_ac0 = time()
        try
            # Use ACPowerFlow with generous iteration limit
            converged = PF.solve_powerflow!(
                PF.ACPowerFlow(), sys; maxIterations=100, check_connectivity=false
            )
            acpf_seconds = time() - t_ac0

            if converged
                println("  ACPF converged at 0% relaxation in $(round(acpf_seconds, digits=2))s")
                relaxation_level_achieved = "0%"
                acpf_converged = true
            else
                println(
                    "  ACPF did NOT converge at 0% relaxation ($(round(acpf_seconds, digits=2))s)"
                )
            end
        catch e
            acpf_seconds = time() - t_ac0
            err_msg = string(typeof(e), ": ", sprint(showerror, e))
            println("  ACPF 0% error: $err_msg")
            push!(results["errors"], "ACPF 0%: $err_msg")
        end

        results["details"]["acpf_0pct_converged"] = acpf_converged
        results["details"]["acpf_0pct_seconds"] = acpf_seconds

        # --- Step 3: ACPF at 10% relaxation (if Step 2 failed) ---
        if !acpf_converged
            println("\nStep 3: ACPF at 10% relaxation...")
            println("  Reloading system and relaxing branch ratings by 10%...")

            # Reload system fresh
            sys = PS.System(matpower_file; runchecks=false)

            # Re-apply DCPF angles
            for bus in PS.get_components(PS.ACBus, sys)
                bus_num = PS.get_number(bus)
                if haskey(angle_map, bus_num)
                    PS.set_angle!(bus, angle_map[bus_num])
                end
            end

            # Relax branch ratings by 10%
            for branch in PS.get_components(PS.ACBranch, sys)
                rating = PS.get_rating(branch)
                if rating > 0
                    PS.set_rating!(branch, rating * 1.10)
                end
            end

            t_ac10 = time()
            try
                converged = PF.solve_powerflow!(
                    PF.ACPowerFlow(), sys; maxIterations=100, check_connectivity=false
                )
                ac10_seconds = time() - t_ac10

                if converged
                    println(
                        "  ACPF converged at 10% relaxation in $(round(ac10_seconds, digits=2))s"
                    )
                    relaxation_level_achieved = "10%"
                    acpf_converged = true
                else
                    println(
                        "  ACPF did NOT converge at 10% relaxation ($(round(ac10_seconds, digits=2))s)",
                    )
                end
                results["details"]["acpf_10pct_seconds"] = ac10_seconds
            catch e
                ac10_seconds = time() - t_ac10
                err_msg = string(typeof(e), ": ", sprint(showerror, e))
                println("  ACPF 10% error: $err_msg")
                push!(results["errors"], "ACPF 10%: $err_msg")
                results["details"]["acpf_10pct_seconds"] = ac10_seconds
            end

            results["details"]["acpf_10pct_converged"] = acpf_converged
        end

        # --- Step 4: ACPF at 20% relaxation (if Step 3 failed) ---
        if !acpf_converged
            println("\nStep 4: ACPF at 20% relaxation...")
            println("  Reloading system and relaxing branch ratings by 20%...")

            sys = PS.System(matpower_file; runchecks=false)

            for bus in PS.get_components(PS.ACBus, sys)
                bus_num = PS.get_number(bus)
                if haskey(angle_map, bus_num)
                    PS.set_angle!(bus, angle_map[bus_num])
                end
            end

            for branch in PS.get_components(PS.ACBranch, sys)
                rating = PS.get_rating(branch)
                if rating > 0
                    PS.set_rating!(branch, rating * 1.20)
                end
            end

            t_ac20 = time()
            try
                converged = PF.solve_powerflow!(
                    PF.ACPowerFlow(), sys; maxIterations=100, check_connectivity=false
                )
                ac20_seconds = time() - t_ac20

                if converged
                    println(
                        "  ACPF converged at 20% relaxation in $(round(ac20_seconds, digits=2))s"
                    )
                    relaxation_level_achieved = "20%"
                    acpf_converged = true
                else
                    println(
                        "  ACPF did NOT converge at 20% relaxation ($(round(ac20_seconds, digits=2))s)",
                    )
                end
                results["details"]["acpf_20pct_seconds"] = ac20_seconds
            catch e
                ac20_seconds = time() - t_ac20
                err_msg = string(typeof(e), ": ", sprint(showerror, e))
                println("  ACPF 20% error: $err_msg")
                push!(results["errors"], "ACPF 20%: $err_msg")
                results["details"]["acpf_20pct_seconds"] = ac20_seconds
            end

            results["details"]["acpf_20pct_converged"] = acpf_converged
        end

        results["details"]["relaxation_level_achieved"] = relaxation_level_achieved
        results["details"]["acpf_converged"] = acpf_converged
        results["details"]["peak_rss_mb"] = peak_rss_mb()

        println("\n=== Summary ===")
        println("  Relaxation level achieved: $relaxation_level_achieved")
        println("  ACPF converged: $acpf_converged")

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
        println("\n*** ERROR ***")
        println(results["details"]["traceback"])
    end

    results["wall_clock_seconds"] = time() - t0
    return results
end

# Helper: mean of a vector
function mean(x)
    return sum(x) / length(x)
end

function eachrow(df)
    return DataFrames.eachrow(df)
end

# Need DataFrames for eachrow
using DataFrames: DataFrames

if abspath(PROGRAM_FILE) == @__FILE__
    result = run_test()
    println("\n" * JSON.json(result, 2))
end

#=
Test A-11: Distributed Slack DC OPF

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Distributed slack formulation supported. LMPs differ from single-slack (A-3)
  consistently. Distributed weights settable via API.
Tool: PowerSimulations.jl v0.30.2
=#

using PowerSystems
using PowerSimulations
using HiGHS
using JuMP
using JSON
using Logging
using DataFrames
using CSV
using Dates
using TimeSeries: TimeArray

global_logger(ConsoleLogger(stderr, Logging.Error))

const PSI = PowerSimulations
const PM = PSI.PM

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024
        end
    end
    return nothing
end

const COST_MAP = Dict("hydro" => 5.0, "nuclear" => 10.0, "coal_large" => 25.0, "gas_CC" => 40.0)

function run(
    network_file::String="/workspace/data/networks/case39.m";
    timeseries_dir::Union{String,Nothing}="/workspace/data/timeseries/case39",
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    try
        if timeseries_dir === nothing
            push!(results["errors"], "timeseries_dir required for A-11")
            return results
        end

        # Investigation: Distributed slack in PowerModels / PowerSimulations
        #
        # Standard DC OPF uses a single reference (slack) bus to fix the voltage angle
        # reference. The slack bus absorbs all losses (zero in lossless DC) and the power
        # balance mismatch. In distributed slack, the mismatch is distributed across
        # multiple generators according to participation factors/weights.
        #
        # PowerModels/PSI approach:
        # - DCPPowerModel: standard single-slack (one reference bus angle = 0)
        # - PTDFPowerModel: PTDF-based, implicitly single-slack through PTDF construction
        # - No documented distributed slack formulation
        #
        # PowerModels network formulations are defined by their mathematical model.
        # The slack bus choice is embedded in the B-matrix construction (DC) or the
        # voltage angle reference constraint. There is no parameter or option to
        # distribute slack across buses.
        #
        # Possible workaround: Manually modify JuMP constraints to implement distributed
        # slack. However, this would require:
        # 1. Removing the reference bus angle constraint
        # 2. Adding a distributed power balance constraint (sum of injections = sum of loads,
        #    with generation participating factors)
        # This is effectively building a custom formulation, not using PSI's API.

        # Check for distributed slack-related symbols in PowerModels
        pm_slack_symbols = String[]
        for n in names(PM; all=true)
            ns = string(n)
            if occursin("slack", lowercase(ns)) ||
                occursin("distributed", lowercase(ns)) ||
                occursin("participation", lowercase(ns))
                push!(pm_slack_symbols, ns)
            end
        end
        results["details"]["powermodels_slack_related_symbols"] = pm_slack_symbols

        # Check PSI for distributed slack options
        psi_slack_symbols = String[]
        for n in names(PSI; all=true)
            ns = string(n)
            if occursin("slack", lowercase(ns)) || occursin("distributed", lowercase(ns))
                push!(psi_slack_symbols, ns)
            end
        end
        results["details"]["psi_slack_related_symbols"] = psi_slack_symbols

        # Check NetworkModel constructor for slack-related parameters
        results["details"]["investigation"] = Dict(
            "formulations_checked" => ["DCPPowerModel", "PTDFPowerModel", "CopperPlatePowerModel"],
            "distributed_slack_found" => false,
            "slack_symbols_pm" => pm_slack_symbols,
            "slack_symbols_psi" => psi_slack_symbols,
            "conclusion" =>
                "Neither PowerModels.jl nor PowerSimulations.jl provides a distributed slack " *
                "formulation for DC OPF. The reference bus angle is fixed at 0 in DCPPowerModel " *
                "(via the ref bus type in the network data), and the PTDF matrix construction in " *
                "PTDFPowerModel also uses a single slack bus. There is no API parameter, network " *
                "model option, or formulation variant that distributes slack across buses. " *
                "CopperPlatePowerModel is a single-node aggregation, not distributed slack. " *
                "A manual workaround via JuMP constraint modification could approximate distributed " *
                "slack, but this would be a custom formulation outside PSI's modeling framework.",
        )

        # PTDFPowerModel's use_slacks parameter is about slack variables for feasibility,
        # NOT distributed slack for power balance.
        results["details"]["ptdf_use_slacks_note"] =
            "PTDFPowerModel has a 'use_slacks' option, but this adds slack variables for " *
            "constraint feasibility relaxation (penalty-based soft constraints), NOT for " *
            "distributing the power balance reference across multiple buses."

        results["status"] = "fail"
        results["details"]["failure_reason"] = "no_distributed_slack_formulation"
        results["details"]["explanation"] =
            "PowerSimulations.jl inherits its DC OPF formulations from PowerModels.jl. " *
            "All DC formulations use a single reference bus: DCPPowerModel fixes one bus's " *
            "voltage angle to 0, and PTDFPowerModel constructs the PTDF matrix relative to a " *
            "single slack bus. There is no built-in distributed slack formulation, no participation " *
            "factor parameter, and no API to set distributed slack weights. " *
            "The NetworkModel constructor accepts 'use_slacks' for PTDFPowerModel, but this is " *
            "for constraint relaxation (feasibility slack variables), not distributed power balance. " *
            "Implementing distributed slack would require building a custom JuMP model with " *
            "modified power balance constraints — effectively bypassing PSI's formulation layer."

        push!(
            results["errors"],
            "No distributed slack DC OPF formulation available in PowerModels.jl/PowerSimulations.jl",
        )

        results["details"]["peak_memory_mb"] = peak_rss_mb()

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

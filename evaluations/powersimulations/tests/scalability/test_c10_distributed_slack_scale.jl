#=
Test C-10: Distributed Slack DC OPF on MEDIUM

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k-bus)
Pass condition: Completes. Wall-clock, peak memory, LMP comparison vs single-slack.
Tool: PowerSimulations.jl v0.30.2
Status: FAIL (cascaded failure from A-11)

This test is blocked by A-11 (Distributed Slack DC OPF), which found that
PowerSimulations.jl / PowerModels.jl does not support distributed slack formulation.
No code execution is needed — this is a cascaded failure.
=#

using JSON

function run()
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => nothing,
        "details" => Dict{String,Any}(
            "blocked_by" => "A-11",
            "failure_reason" => "cascaded_failure",
            "explanation" =>
                "C-10 (Distributed Slack DC OPF at scale) is blocked by A-11 (Distributed Slack DC OPF " *
                "on TINY). A-11 found that neither PowerSimulations.jl nor PowerModels.jl provides a " *
                "distributed slack formulation for DC OPF. All DC formulations use a single reference bus: " *
                "DCPPowerModel fixes one bus's voltage angle to 0, and PTDFPowerModel constructs the PTDF " *
                "matrix relative to a single slack bus. There is no built-in distributed slack formulation, " *
                "no participation factor parameter, and no API to set distributed slack weights. " *
                "Since the capability does not exist at TINY scale, it cannot be tested at MEDIUM scale.",
            "a11_status" => "fail",
            "a11_finding" => "no_distributed_slack_formulation",
        ),
        "errors" =>
            ["Cascaded failure from A-11: no distributed slack formulation in PSI/PowerModels"],
        "workarounds" => String[],
    )
    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

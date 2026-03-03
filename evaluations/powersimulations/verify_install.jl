"""
Verify PowerSimulations.jl installation by loading IEEE 39-bus case
and running DC power flow via PowerFlows.jl.
"""

using PowerSystems
using PowerFlows
using PowerNetworkMatrices

data_dir = joinpath(@__DIR__, "..", "..", "data", "networks")
case_file = joinpath(data_dir, "case39.m")

# Load system from MATPOWER file
sys = System(case_file)
println("System: $(get_name(sys))")
println("Buses: $(length(collect(get_components(ACBus, sys))))")

# Run DC power flow
result = solve_powerflow(DCPowerFlow(), sys)
println("DC power flow completed: $(result)")

exit(0)

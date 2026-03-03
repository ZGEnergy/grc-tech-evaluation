"""
Verify PowerModels.jl installation by running DC power flow on IEEE 39-bus case.
"""

using PowerModels
using HiGHS

data_dir = joinpath(@__DIR__, "..", "..", "data", "networks")
case_file = joinpath(data_dir, "case39.m")

# Parse MATPOWER case file
data = PowerModels.parse_file(case_file)
println("Network: $(data["name"])")
println("Buses: $(length(data["bus"]))")
println("Branches: $(length(data["branch"]))")

# Run DC power flow
result = PowerModels.solve_dc_pf(data, HiGHS.Optimizer)
println("Status: $(result["termination_status"])")
println("Solve time: $(result["solve_time"])s")

if result["termination_status"] == OPTIMAL
    println("DC power flow completed successfully")
    exit(0)
else
    println("DC power flow failed")
    exit(1)
end

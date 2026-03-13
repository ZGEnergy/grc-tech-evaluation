using PowerModels
using Ipopt
using GLPK
using JuMP: termination_status, LOCALLY_SOLVED, OPTIMAL

@testset "Ipopt: AC OPF on case39" begin
    data = PowerModels.parse_file(joinpath(DATA_DIR, "case39.m"))
    result = PowerModels.solve_ac_opf(data, Ipopt.Optimizer)
    @test result["termination_status"] == LOCALLY_SOLVED
end

@testset "GLPK: DC OPF on case39" begin
    data = PowerModels.parse_file(joinpath(DATA_DIR, "case39.m"))
    result = PowerModels.solve_dc_opf(data, GLPK.Optimizer)
    @test result["termination_status"] == OPTIMAL
end

using PowerModels
using HiGHS

@testset "import PowerModels" begin
    @test isdefined(PowerModels, :parse_file)
    @test isdefined(PowerModels, :solve_dc_pf)
    @test @isdefined OPTIMAL
end

@testset "parse IEEE 39-bus case" begin
    case_file = joinpath(DATA_DIR, "case39.m")
    @test isfile(case_file)

    data = PowerModels.parse_file(case_file)

    @test data isa Dict
    @test haskey(data, "bus")
    @test haskey(data, "branch")
    @test haskey(data, "gen")
    @test length(data["bus"]) == 39
    @test length(data["branch"]) == 46
    @test length(data["gen"]) == 10
end

@testset "solve DC power flow" begin
    case_file = joinpath(DATA_DIR, "case39.m")
    data = PowerModels.parse_file(case_file)

    result = PowerModels.solve_dc_pf(data, HiGHS.Optimizer)

    @test result isa Dict
    @test result["termination_status"] == OPTIMAL
    @test result["solve_time"] >= 0.0
    @test haskey(result, "solution")

    bus_solution = result["solution"]["bus"]
    angles = [bus_solution[b]["va"] for b in keys(bus_solution)]
    @test !all(a == 0.0 for a in angles)
end

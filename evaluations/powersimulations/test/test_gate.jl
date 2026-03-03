using PowerSystems
using PowerFlows
using PowerNetworkMatrices

@testset "import PowerSystems/PowerFlows/PowerNetworkMatrices" begin
    @test isdefined(PowerSystems, :System)
    @test isdefined(PowerSystems, :get_components)
    @test isdefined(PowerSystems, :ACBus)
    @test isdefined(PowerFlows, :solve_powerflow)
    @test isdefined(PowerFlows, :DCPowerFlow)
end

@testset "parse IEEE 39-bus case" begin
    case_file = joinpath(DATA_DIR, "case39.m")
    @test isfile(case_file)

    sys = System(case_file)

    @test sys isa System
    buses = collect(get_components(ACBus, sys))
    @test length(buses) == 39
end

@testset "solve DC power flow" begin
    case_file = joinpath(DATA_DIR, "case39.m")
    sys = System(case_file)

    result = solve_powerflow(DCPowerFlow(), sys)

    @test result isa Dict
    @test !isempty(result)
end

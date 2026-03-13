using Ipopt
using GLPK

@testset "Ipopt available" begin
    @test isdefined(Ipopt, :Optimizer)
end

@testset "GLPK available" begin
    @test isdefined(GLPK, :Optimizer)
end

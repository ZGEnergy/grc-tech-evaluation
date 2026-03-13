using Test

# Shared data directory -- computed relative to this file's location.
# Layout: evaluations/<tool>/test/runtests.jl
#   -> ../../.. -> repo root -> data/networks/
const DATA_DIR = normpath(joinpath(@__DIR__, "..", "..", "..", "data", "networks"))

@testset "PowerModels Gate Tests" begin
    include("test_gate.jl")
end

@testset "PowerModels Solver Tests" begin
    include("test_solvers.jl")
end

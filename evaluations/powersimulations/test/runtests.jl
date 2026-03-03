using Test

# Shared data directory -- computed relative to this file's location.
# Layout: evaluations/<tool>/test/runtests.jl
#   -> ../../.. -> repo root -> data/networks/
const DATA_DIR = normpath(joinpath(@__DIR__, "..", "..", "..", "data", "networks"))

@testset "PowerSimulations Gate Tests" begin
    include("test_gate.jl")
end

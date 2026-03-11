#=
Julia test runner for power-system tool evaluation.

Copy this file into evaluations/<tool>/tests/ to enable test discovery
and execution across dimensions.

Usage:
    julia --project=. tests/runtests.jl                    # run all tests
    julia --project=. tests/runtests.jl expressiveness     # run one dimension
    julia --project=. tests/runtests.jl expressiveness a1  # run one test
=#

using Test
using JSON

# Repository root (3 levels up from evaluations/<tool>/tests/)
const REPO_ROOT = abspath(joinpath(@__DIR__, "..", "..", "..", ".."))
const DATA_DIR = joinpath(REPO_ROOT, "data", "networks")

# Network file paths
const NETWORKS = Dict(
    "TINY" => joinpath(DATA_DIR, "case39.m"),
    "SMALL" => joinpath(DATA_DIR, "case_ACTIVSg2000.m"),
    "MEDIUM" => joinpath(DATA_DIR, "case_ACTIVSg10k.m"),
)
const TIMESERIES = Dict("TINY" => joinpath(dirname(DATA_DIR), "timeseries", "case39"))

# Reference counts for gate validation
const REFERENCE_COUNTS = Dict("TINY" => Dict("buses" => 39, "branches" => 46, "generators" => 10))

"""
    discover_tests(dimension::String="") -> Vector{String}

Find all test files matching the pattern test_*.jl in dimension subdirectories.
If dimension is specified, only search that subdirectory.
"""
function discover_tests(dimension::String="", test_filter::String="")
    test_dir = @__DIR__
    test_files = String[]

    if isempty(dimension)
        # Search all dimension subdirectories
        for entry in readdir(test_dir)
            dim_path = joinpath(test_dir, entry)
            isdir(dim_path) || continue
            for f in readdir(dim_path)
                if startswith(f, "test_") && endswith(f, ".jl")
                    if isempty(test_filter) || contains(lowercase(f), lowercase(test_filter))
                        push!(test_files, joinpath(dim_path, f))
                    end
                end
            end
        end
    else
        dim_path = joinpath(test_dir, dimension)
        if isdir(dim_path)
            for f in readdir(dim_path)
                if startswith(f, "test_") && endswith(f, ".jl")
                    if isempty(test_filter) || contains(lowercase(f), lowercase(test_filter))
                        push!(test_files, joinpath(dim_path, f))
                    end
                end
            end
        else
            @warn "Dimension directory not found: $dim_path"
        end
    end

    sort!(test_files)
    return test_files
end

"""
    run_test_file(path::String) -> Dict

Include and run a test file, capturing its run() output.
"""
function run_test_file(path::String)
    @info "Running: $path"
    try
        include(path)
        # The included file should define a run() function
        if isdefined(Main, :run)
            return Main.run()
        else
            return Dict("status" => "fail", "errors" => ["No run() function defined"])
        end
    catch e
        return Dict("status" => "fail", "errors" => [string(typeof(e), ": ", sprint(showerror, e))])
    end
end

# Parse command-line arguments
dimension_filter = length(ARGS) >= 1 ? ARGS[1] : ""
test_filter = length(ARGS) >= 2 ? ARGS[2] : ""

test_files = discover_tests(dimension_filter, test_filter)

if isempty(test_files)
    @warn "No test files found" dimension=dimension_filter test=test_filter
else
    @info "Found $(length(test_files)) test file(s)"

    @testset "Evaluation Tests" begin
        for tf in test_files
            test_name = basename(tf)
            @testset "$test_name" begin
                result = run_test_file(tf)
                @test result["status"] in ["pass", "qualified_pass"]
                if haskey(result, "errors") && !isempty(result["errors"])
                    @warn "Errors in $test_name" errors=result["errors"]
                end
            end
        end
    end
end

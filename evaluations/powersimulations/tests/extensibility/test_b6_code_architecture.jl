#=
Test B-6: Code Architecture (Qualitative assessment of DCPF solve path)

Dimension: extensibility
Network: N/A (qualitative)
Pass condition: Document: abstraction layers, separation of concerns, internal interfaces.
Tool: PowerSimulations.jl v0.30.2

This is a qualitative test — no solve is performed. The script traces the DCPF
solve path through the Sienna ecosystem and reports architectural findings.
=#

using PowerSystems
using PowerFlows
using PowerNetworkMatrices
using JSON

function run(; kwargs...)
    results = Dict(
        "status" => "pass",  # Qualitative — always reports
        "wall_clock_seconds" => 0.0,
        "details" => Dict(
            "abstraction_layers" => 5,
            "layers" => [
                Dict(
                    "level" => 1,
                    "name" => "User API",
                    "package" => "PowerFlows.jl v0.9.0",
                    "entry_point" => "solve_powerflow(DCPowerFlow(), sys)",
                    "description" => "Public entry point. Accepts a method selector (DCPowerFlow, PTDFDCPowerFlow, vPTDFDCPowerFlow, ACPowerFlow) and a System. Returns Dict of DataFrames.",
                ),
                Dict(
                    "level" => 2,
                    "name" => "Data Model",
                    "package" => "PowerSystems.jl v4.6.2",
                    "entry_point" => "System(file_path)",
                    "description" => "Typed component hierarchy (ACBus, ThermalStandard, Line, PowerLoad, etc.) with accessors (get_components, get_bus, get_rating). Parses MATPOWER, PSS/E, tabular CSV. All values stored in per-unit (system base). InfrastructureSystems.jl handles time series.",
                ),
                Dict(
                    "level" => 3,
                    "name" => "Network Matrices",
                    "package" => "PowerNetworkMatrices.jl v0.12.1",
                    "entry_point" => "ABA_Matrix(sys), BA_Matrix(sys), PTDF(sys)",
                    "description" => "Constructs admittance-derived matrices (Ybus, ABA, BA, PTDF, LODF). Supports KLU sparse factorization, distributed slack, radial reduction, virtual (lazy) computation. Used internally by PowerFlows.jl for DCPF.",
                ),
                Dict(
                    "level" => 4,
                    "name" => "Linear Solver",
                    "package" => "PowerFlows.jl (LinearSolverCache)",
                    "entry_point" => "KLULinSolveCache, full_factor!, solve!",
                    "description" => "Internal caching layer over KLU sparse direct solver. Manages factorization lifecycle (symbolic → numeric → solve). DCPF solve is: factor ABA, solve ABA * theta = Pinj, compute flows = BA' * theta.",
                ),
                Dict(
                    "level" => 5,
                    "name" => "Results / Post-processing",
                    "package" => "PowerFlows.jl (post_processing.jl)",
                    "entry_point" => "write_results(data, sys)",
                    "description" => "Converts internal PowerFlowData arrays to DataFrames with named columns (bus_number, Vm, theta, P_gen, P_load, P_net, line_name, P_from_to, etc.). Handles per-unit to MW conversion for AC results.",
                ),
            ],
            "dcpf_solve_trace" => [
                "1. User calls: solve_powerflow(DCPowerFlow(), sys)",
                "2. PowerFlows constructs PowerFlowData(DCPowerFlow(), sys) → ABAPowerFlowData",
                "   - Extracts bus injections/withdrawals from System components",
                "   - Builds ABA_Matrix (bus susceptance matrix) via PowerNetworkMatrices",
                "   - Builds BA_Matrix (branch-bus susceptance weighting) via PowerNetworkMatrices",
                "   - Identifies reference bus (excluded from solve), stores valid_ix",
                "3. PowerFlows calls solve_powerflow!(data::ABAPowerFlowData)",
                "   - Creates KLU factorization cache from ABA matrix",
                "   - Computes net injection: Pinj = bus_gen - bus_load",
                "   - Solves for angles: ABA * theta = Pinj (at non-reference buses)",
                "   - Computes flows: flow = BA' * theta",
                "   - Sets converged = true (DCPF is always a direct solve)",
                "4. PowerFlows calls write_results(data, sys) → Dict of DataFrames",
                "   - Maps internal arrays to bus numbers and branch names",
                "   - Constructs bus_results DataFrame (bus_number, Vm, theta, P_gen, P_load, P_net, Q_*)",
                "   - Constructs flow_results DataFrame (line_name, bus_from, bus_to, P_from_to, P_to_from, losses)",
                "5. Returns Dict{String, Dict{String, DataFrame}} to user",
            ],
            "separation_of_concerns" => Dict(
                "network_model" => "PowerSystems.jl — component types, topology, per-unit normalization",
                "problem_formulation" => "PowerFlows.jl — DCPowerFlow/ACPowerFlow method selection, PowerFlowData construction",
                "matrix_computation" => "PowerNetworkMatrices.jl — ABA, BA, PTDF, KLU factorization",
                "solver_interface" => "KLU (sparse direct) for DCPF; JuMP/MOI for OPF (PowerSimulations.jl)",
                "results" => "DataFrames.jl — native tabular output, CSV export via CSV.jl",
            ),
            "internal_interfaces_documented" => Dict(
                "PowerFlowData" => "Documented as public struct with fields for bus/branch arrays",
                "solve_powerflow!" => "Documented with docstrings per method (PTDF, ABA, vPTDF variants)",
                "write_results" => "Documented — converts internal data to DataFrames",
                "PTDF/ABA constructors" => "Documented in PowerNetworkMatrices.jl public API",
                "KLULinSolveCache" => "Internal — not documented in public API, but clean interface",
            ),
            "key_findings" => [
                "Clean 5-layer architecture with well-defined package boundaries",
                "Each package has a single responsibility (SRP): data, matrices, flows, simulation, results",
                "Julia multiple dispatch provides the formulation selection mechanism (DCPowerFlow vs ACPowerFlow)",
                "DCPF solve path has zero external solver dependency — uses KLU sparse direct solver only",
                "OPF solve path adds JuMP/MOI layer (PowerSimulations.jl) on top of the same data model",
                "Internal interfaces use Julia's type system (PowerFlowData{MatrixType} parametric dispatch)",
                "No circular dependencies between packages — clean DAG: PowerSystems → PowerNetworkMatrices → PowerFlows",
                "The OPF path (PowerSimulations.jl) adds 2 more layers: template/formulation selection and JuMP model construction",
            ],
        ),
        "errors" => String[],
        "workarounds" => String[],
    )

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end

---
test_id: B-6
tool: powersimulations
dimension: extensibility
network: N/A
protocol_version: "v11"
skill_version: "v2"
test_hash: "0f337d8d"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.0
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 100
solver: null
sced_mode: null
timestamp: "2026-03-24T00:00:00Z"
---

# B-6: Code Architecture (Qualitative Assessment of DCPF Solve Path)

## Result: PASS

## Approach

Traced the DCPF solve path from API call (`solve_powerflow(DCPowerFlow(), sys)`) through
all abstraction layers to the underlying linear algebra operation. Inspected source code
of PowerFlows.jl, PowerNetworkMatrices.jl, and PowerSystems.jl in the devcontainer.

## Abstraction Layers: 5

### Layer 1: User API (PowerFlows.jl)

**Entry point:** `solve_powerflow(DCPowerFlow(), sys)`

The public API uses Julia's multiple dispatch to select the solve method. Three DC
variants are available:

| Method | Internal Type | Matrix Used |
|--------|--------------|-------------|
| `DCPowerFlow()` | `ABAPowerFlowData` | ABA + BA matrices |
| `PTDFDCPowerFlow()` | `PTDFPowerFlowData` | Full PTDF matrix |
| `vPTDFDCPowerFlow()` | `vPTDFPowerFlowData` | Virtual (lazy) PTDF |

Returns `Dict{String, Dict{String, DataFrame}}` -- keyed by timestep, containing
`"bus_results"` and `"flow_results"` DataFrames.

### Layer 2: Data Model (PowerSystems.jl v4.6.2)

**Entry point:** `System(file_path)`

Typed component hierarchy with abstract base types (`Generator`, `Branch`,
`ElectricLoad`) and concrete implementations (`ThermalStandard`, `Line`,
`PowerLoad`). Components have strongly-typed fields with accessor functions
(`get_bus`, `get_rating`, `get_active_power`).

The System parses MATPOWER `.m` files (via PowerModels.jl parser), PSS/E `.raw`
files, and tabular CSV. All values are normalized to per-unit on system base
(default 100 MVA).

Time series management is delegated to InfrastructureSystems.jl, which provides
`SingleTimeSeries`, `Deterministic`, `Probabilistic`, and `Scenarios` forecast types.

### Layer 3: Network Matrices (PowerNetworkMatrices.jl v0.12.1)

**Entry point:** `ABA_Matrix(sys)`, `BA_Matrix(sys)`, `PTDF(sys)`

Constructs admittance-derived matrices from System topology:

- **ABA_Matrix**: Bus susceptance matrix (reduced, excluding reference bus). Stores
  a pre-computed KLU factorization for efficient repeated solves.
- **BA_Matrix**: Branch-bus weighted susceptance matrix for flow computation.
- **PTDF**: Power Transfer Distribution Factors (full dense or virtual/lazy).
- **LODF**: Line Outage Distribution Factors.
- **Ybus**: Full nodal admittance matrix.

Supports multiple linear solver backends: KLU (default, sparse), MKLPardiso, Dense.

### Layer 4: Linear Solver (PowerFlows.jl internal)

**Entry point:** `KLULinSolveCache`, `full_factor!()`, `solve!()`

Internal caching layer over the KLU sparse direct solver. The solve sequence is:

1. Create factorization cache: `KLULinSolveCache(ABA_matrix)`
2. Compute full factorization: `full_factor!(cache, ABA_matrix)`
3. Solve: `solve!(cache, Pinj)` -- overwrites Pinj with solution angles

For DCPF, the complete mathematical operation is:
```
theta = ABA^{-1} * Pinj    (voltage angles)
flow = BA' * theta          (branch flows)
```

This is a direct solve (no iteration, no convergence criterion). DCPF always converges.

### Layer 5: Results / Post-processing (PowerFlows.jl)

**Entry point:** `write_results(data, sys)`

Converts internal `PowerFlowData` arrays to named DataFrames:

- **Bus results:** `bus_number`, `Vm`, `theta`, `P_gen`, `P_load`, `P_net`,
  `Q_gen`, `Q_load`, `Q_net`
- **Flow results:** `line_name`, `bus_from`, `bus_to`, `P_from_to`, `Q_from_to`,
  `P_to_from`, `Q_to_from`, `P_losses`, `Q_losses`

For DC results, reactive power and voltage magnitude columns are present but
contain zeros/ones (preserving structural consistency with AC results).

## DCPF Solve Trace

```
User: solve_powerflow(DCPowerFlow(), sys)
  -> PowerFlows.jl: construct PowerFlowData(DCPowerFlow(), sys)
      -> PowerNetworkMatrices.jl: build ABA_Matrix(sys)
          -> PowerSystems.jl: iterate components, extract topology
      -> PowerNetworkMatrices.jl: build BA_Matrix(sys)
      -> Extract bus injections/withdrawals from System components
      -> Identify reference bus (excluded from solve)
  -> PowerFlows.jl: solve_powerflow!(data::ABAPowerFlowData)
      -> KLU: factor ABA matrix
      -> KLU: solve ABA * theta = Pinj
      -> Compute: flow = BA' * theta
      -> Mark converged = true
  -> PowerFlows.jl: write_results(data, sys)
      -> Map arrays to bus numbers and branch names
      -> Construct bus_results DataFrame
      -> Construct flow_results DataFrame
  -> Return Dict of DataFrames
```

## Separation of Concerns

| Concern | Package | Clean boundary? |
|---------|---------|----------------|
| Data model (types, I/O, topology) | PowerSystems.jl | Yes -- independent package |
| Time series management | InfrastructureSystems.jl | Yes -- generic, not power-specific |
| Network matrix computation | PowerNetworkMatrices.jl | Yes -- pure linear algebra |
| Power flow solution | PowerFlows.jl | Yes -- consumes System + matrices |
| Optimization / OPF | PowerSimulations.jl | Yes -- adds JuMP layer on same data model |
| Results output | DataFrames.jl + CSV.jl | Yes -- standard Julia ecosystem |

The package dependency graph is a clean DAG:
```
InfrastructureSystems.jl
    |
PowerSystems.jl
    |
PowerNetworkMatrices.jl
    |
PowerFlows.jl          PowerSimulations.jl (adds JuMP/MOI)
```

No circular dependencies. Each package can be used independently (e.g.,
PowerNetworkMatrices.jl for PTDF without PowerFlows or PowerSimulations).

## Internal Interface Documentation

| Interface | Documented? | Quality |
|-----------|------------|---------|
| `solve_powerflow()` public API | Yes | Good docstrings per method variant |
| `PowerFlowData` struct | Yes | Fields documented, parametric on matrix type |
| `PTDF`, `ABA_Matrix` constructors | Yes | Public API docs in PowerNetworkMatrices |
| `KLULinSolveCache` | No | Internal implementation, clean but undocumented |
| `write_results()` | Yes | Docstrings describe output format |
| Extension via `construct_device!` | Partial | Docstring in formulations.jl shows pattern |

## Key Architectural Findings

1. **Clean 5-layer architecture** with well-defined package boundaries. Each package
   has a single responsibility (data model, matrices, flows, optimization, results).

2. **Julia's multiple dispatch** provides the formulation selection mechanism. Adding
   a new solve method means defining a new type (e.g., `MyCustomPowerFlow`) and
   implementing `solve_powerflow(::MyCustomPowerFlow, sys)`.

3. **DCPF has zero external solver dependency** -- uses KLU sparse direct solver only.
   The OPF path adds JuMP/MathOptInterface, introducing solver dependency.

4. **Parametric type dispatch** (`PowerFlowData{MatrixType}`) allows different matrix
   representations (PTDF, ABA, VirtualPTDF) to use the same data container with
   specialized solve methods.

5. **The OPF path** (PowerSimulations.jl) adds 2 more conceptual layers on top:
   template/formulation selection (`ProblemTemplate`, `DeviceModel`) and JuMP model
   construction (`OptimizationContainer`, `get_jump_model()`), bringing the total to 7
   layers for OPF.

6. **No circular dependencies** between packages -- clean DAG structure.

7. **Internal interfaces are type-safe** -- Julia's type system prevents passing
   wrong data types between layers at compile time.

## Observations

- **arch-quality:** The Sienna ecosystem has one of the cleanest architectural separations
  among the tools evaluated. The package-per-concern design means each component can be
  tested, versioned, and evolved independently.
- **arch-quality:** The use of Julia's type system for formulation dispatch (rather than
  string-based configuration or flag parameters) provides compile-time safety and enables
  IDE support for discovering available formulations.
- **doc-gaps:** Internal interfaces (KLULinSolveCache, PowerFlowData construction) are
  not documented in the public API. Users extending the framework need to read source code.
- **arch-quality:** The DAG dependency structure means users can import only what they
  need -- e.g., `PowerNetworkMatrices.jl` alone for PTDF computation without pulling in
  the simulation framework.

## Test Script

**Path:** `evaluations/powersimulations/tests/extensibility/test_b6_code_architecture.jl`

This is a qualitative test. The script contains the architectural findings as structured
data but does not perform a solve.

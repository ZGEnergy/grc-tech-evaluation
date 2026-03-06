# PowerModels.jl — Research Context (Merged)

This document merges three research outputs for the PowerModels.jl Phase 1 evaluation.

---

## Section 1: API & Formulations

**Version evaluated:** 0.21.5 | **Julia:** 1.10+ | **License:** BSD (LANL LA-CC-15-024)

## Key Findings

- **Dict-based data model** (`Dict{String, Any}`) — no typed structs, string keys throughout. Components: bus, branch, gen, load, shunt, storage, dcline, switch.
- **18 formulation types** from exact nonlinear (ACP, ACR, ACT, IVR) through linear (DCP, DCMP, BFA, NFA) to SOC/QC/SDP relaxations, all subtypes of `AbstractPowerModel`.
- **24 `solve_*` functions** covering PF, OPF, OTS, TNEP, OPB, multi-network variants with storage. No SCUC/SCED.
- **Native (non-JuMP) solvers**: `compute_ac_pf`, `compute_dc_pf` bypass JuMP for faster pure power flow.
- **Dual/LMP extraction** via `setting = Dict("output" => Dict("duals" => true))`. Bus duals as `lam_kcl_r`. AC OPF dual support limited (issue #409).
- **Multi-network** via `replicate()` + `solve_mn_*`. Manual data construction, no native time-series ingestion.
- **SCOPF** requires separate PowerModelsSecurityConstrained.jl package.
- **Input:** MATPOWER `.m`, PSS(R)E v33 `.raw`. **Output:** Dict only.
- **PTDF** via `calc_basic_ptdf_matrix()` (requires `make_basic_network()` preprocessing).
- **Solver interface:** JuMP-based, any MOI-compatible solver. `optimizer_with_attributes()` for config.

### Solve Pattern

```julia
result = solve_dc_opf("case.m", HiGHS.Optimizer)
# or with settings:
result = solve_dc_opf(data, HiGHS.Optimizer; setting=Dict("output"=>Dict("duals"=>true)))

```

### Two-Stage Model Building

```julia
pm = instantiate_model(data, ACPPowerModel, PowerModels.build_opf)
# Access JuMP model: pm.model
result = optimize_model!(pm, optimizer=Ipopt.Optimizer)

```

### Matrix Utilities
`calc_basic_ptdf_matrix`, `calc_basic_incidence_matrix`, `calc_admittance_matrix`, `calc_susceptance_matrix`, `calc_basic_jacobian_matrix`, etc. All `calc_basic_*` require `make_basic_network()`.

---

## Section 2: Extensions & Architecture

## Key Findings

- **Extension via Julia's type dispatch** — define new `AbstractPowerModel` subtypes and implement formulation-specific methods. No registration needed.
- **Constraint template pattern** (two-layer): templates extract data (formulation-agnostic), then call formulation-specific implementations that dispatch on concrete types.
- **Full JuMP model access** via `pm.model` after `instantiate_model()`.
- **`ref_extensions`** callback array: inject custom reference data at instantiation.
- **`solution_processors`** callback array: post-process solutions after optimization.
- **`pm.ext` dictionary**: per-model arbitrary state storage.
- **No Graphs.jl integration** — custom DFS for connected components, adjacency via `:arcs_from`, `:arcs_to`, `:bus_arcs`, `:buspairs`.
- **No DataFrames.jl integration** — results are nested dicts, manual conversion needed.
- **PTDF native** via `calc_basic_ptdf_matrix()` — O(n^3) dense inverse, `calc_basic_ptdf_row()` for per-branch sparse alternative.

### Architecture Layers

| Layer | Directory | Responsibility |

|-------|-----------|---------------|

| I/O | `src/io/` | Parsing MATPOWER, PSS/E, JSON |

| Data/Ref | `src/core/data.jl`, `ref.jl` | Validation, transformation, reference dict |

| Formulations | `src/form/` | Variable/constraint implementations per formulation |

| Problems | `src/prob/` | Problem specifications composing variables/constraints/objectives |

### Custom Problem Example

```julia
function build_my_opf(pm::AbstractPowerModel)
    PowerModels.variable_bus_voltage(pm)
    PowerModels.variable_gen_power(pm)
    PowerModels.variable_branch_power(pm)
    PowerModels.objective_min_fuel_and_flow_cost(pm)
    # ... constraints ...
end
result = PowerModels.solve_model("case.m", DCPPowerModel, optimizer, build_my_opf)

```

### Adding Custom JuMP Constraints

```julia
pm = instantiate_model(data, DCPPowerModel, PowerModels.build_opf)
JuMP.@constraint(pm.model, sum(...) <= limit)
result = optimize_model!(pm, optimizer=HiGHS.Optimizer)

```

### Graphs.jl Bridge (Manual)

```julia
using Graphs
g = SimpleGraph(length(data["bus"]))
for (_, br) in data["branch"]
    add_edge!(g, br["f_bus"], br["t_bus"])
end

```

---

## Section 3: Limitations & Ecosystem

## Key Findings

- **Steady-state only** — no SCUC, multi-period dispatch, or scheduling without extensions.
- **SCOPF external** (PowerModelsSecurityConstrained.jl) — lacks storage/dcline/switch support.
- **No distributed slack or LMP decomposition** — single reference bus, manual dual extraction needed.
- **Historical DC OPF bug** (issue #422): transformer phase shift ignored, fixed in later releases.
- **15+ extension packages** with varying maturity (LANL, KU Leuven, CSIRO).
- **Research-focused** — no evidence of utility/ISO operational deployment. Used as ARPA-e GOC benchmark.
- **Release cadence**: v0.21.4 (May 2024), v0.21.5 (Aug 2024). Still v0.x after 8+ years.
- **114 transitive dependencies** (with solvers). GLPK is GPL-3.0 (optional).
- **456 stars, 167 forks, 29 contributors, 83 open issues.** PSCC 2018 paper ~300+ citations.
- **StochasticPowerModels.jl** warns about breaking changes — pre-production maturity.

### Ecosystem Packages

| Package | Maintainer | Purpose |

|---------|-----------|---------|

| PowerModelsSecurityConstrained.jl | LANL | SCOPF |

| PowerModelsDistribution.jl | LANL | Unbalanced distribution |

| PowerModelsAnnex.jl | LANL | Experimental methods |

| PowerModelsITD.jl | LANL | Transmission-distribution |

| PowerModelsACDC.jl | KU Leuven | AC/DC grids |

| StochasticPowerModels.jl | KU Leuven | Stochastic OPF |

| UnitCommitment.jl | ANL | SCUC (separate project) |

| PowerSimulations.jl | NREL | Production cost modeling |

### License Summary
- PowerModels.jl: BSD | JuMP: MPL-2.0 | HiGHS: MIT | Ipopt: EPL-2.0 | SCIP: Apache-2.0 | GLPK: GPL-3.0 (optional)

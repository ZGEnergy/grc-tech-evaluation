# B-6: Code Architecture Audit (PowerModels.jl v0.21.5)

## Tool
PowerModels.jl v0.21.5

## Status: PASS (qualitative assessment)

## Summary
PowerModels.jl has a clean four-layer architecture with strong separation of concerns. The DCPF solve path traverses 4 abstraction layers from API call to solver. Internal interfaces are well-documented via docstrings and the type system. Total codebase: ~19,000 LOC across 43 source files.

## Architecture Layers

### Layer 1: I/O (`src/io/`, ~4,077 LOC)
- `matpower.jl` (1,237 LOC): MATPOWER `.m` parser
- `psse.jl` (932 LOC): PSS/E `.raw` parser
- `pti.jl` (1,755 LOC): PTI format parser
- `common.jl` (126 LOC): `parse_file()` dispatcher
- `json.jl` (27 LOC): JSON I/O

The top-level `parse_file()` dispatches by file extension. All parsers produce a canonical `Dict{String,Any}` data model (the "PM data dict"). This dict is the universal internal data representation.

### Layer 2: Core / Data / Reference (`src/core/`, ~7,847 LOC)
- `data.jl` (2,738 LOC): Data validation, per-unit conversion, `replicate()` for multi-network
- `data_basic.jl` (481 LOC): `make_basic_network()`, matrix computations (PTDF, susceptance, admittance)
- `ref.jl` (178 LOC): Reference extension functions
- `base.jl` (235 LOC): `solve_model()`, `instantiate_model()`, `build_ref()`, `ref_add_core!()`
- `types.jl` (542 LOC): Abstract type hierarchy (20+ model types)
- `variable.jl` (1,324 LOC): Variable declarations (bus voltage, gen power, branch flow)
- `constraint_template.jl` (984 LOC): Constraint templates that bridge formulation-agnostic specs to formulation-specific implementations
- `constraint.jl` (251 LOC): Low-level constraint helpers
- `objective.jl` (327 LOC): Objective function builders
- `expression_template.jl` (191 LOC): Expression templates
- `admittance_matrix.jl` (369 LOC): Admittance/susceptance matrix construction

Key design: `constraint_template.jl` defines formulation-agnostic constraint signatures that extract parameters from `ref()` and dispatch to formulation-specific implementations in `form/`. This is the primary extension point.

### Layer 3: Formulations (`src/form/`, ~4,277 LOC)
- `dcp.jl` (420 LOC): DC power flow formulation
- `acp.jl` (519 LOC): AC polar formulation
- `acr.jl` (260 LOC): AC rectangular formulation
- `shared.jl` (397 LOC): Shared constraint implementations
- `wr.jl` (801 LOC), `wrm.jl` (489 LOC): W-space relaxations
- Plus: `act.jl`, `apo.jl`, `bf.jl`, `iv.jl`, `lpac.jl`

Each formulation file overrides `variable_*`, `constraint_*`, and `sol_data_model!` methods for its model type. Julia's multiple dispatch on the `AbstractPowerModel` type hierarchy enables clean formulation switching.

### Layer 4: Problems (`src/prob/`, ~1,960 LOC)
- `pf.jl` (707 LOC): Power flow problems + `compute_dc_pf()`, `compute_ac_pf()`
- `opf.jl` (238 LOC): OPF problems + `solve_mn_opf()`, `solve_opf_ptdf()`
- `ots.jl` (57 LOC): Optimal transmission switching
- `tnep.jl` (94 LOC): Transmission network expansion planning
- Plus: `opb.jl`, `opf_bf.jl`, `opf_iv.jl`, `pf_bf.jl`, `pf_iv.jl`, `test.jl`

Each problem file defines a `build_*` function that assembles variables, constraints, and objective from Layers 2-3.

### Utilities (`src/util/`, ~688 LOC)
- `obbt.jl` (493 LOC): Optimality-based bound tightening
- `flow_limit_cuts.jl` (195 LOC): Flow limit cutting planes

## DCPF Solve Path Trace

### Path 1: `compute_dc_pf(file)` (direct linear solve, no JuMP)

```

compute_dc_pf(file::String)           # prob/pf.jl
  -> parse_file(file)                  # io/common.jl -> io/matpower.jl
  -> compute_dc_pf(data::Dict)         # prob/pf.jl
    -> reference_bus(data)             # core/data.jl
    -> calc_bus_injection_active(data)  # core/data.jl
    -> calc_susceptance_matrix(data)    # core/admittance_matrix.jl
    -> solve_theta(sm, ref_idx, bi)    # core/admittance_matrix.jl (linear solve)
    -> construct solution dict          # prob/pf.jl

```

**Layers traversed: 3** (I/O -> Core -> Prob). No JuMP, no formulation dispatch. Direct `B * theta = p` linear solve.

### Path 2: `solve_dc_opf(file, optimizer)` (JuMP-based OPF)

```

solve_dc_opf(file, optimizer)          # prob/opf.jl
  -> solve_opf(file, DCPPowerModel, optimizer)  # prob/opf.jl
    -> solve_model(file, DCPPowerModel, optimizer, build_opf)  # core/base.jl
      -> parse_file(file)              # io/common.jl
      -> instantiate_model(data, DCPPowerModel, build_opf)  # core/base.jl
        -> _IM.instantiate_model(...)   # InfrastructureModels
          -> ref_add_core!(ref)        # core/base.jl (builds :bus, :gen, :branch, :ref_buses, etc.)
          -> build_opf(pm)             # prob/opf.jl
            -> variable_bus_voltage(pm)       # dispatches to form/dcp.jl
            -> variable_gen_power(pm)         # core/variable.jl
            -> variable_branch_power(pm)      # core/variable.jl
            -> objective_min_fuel_and_flow_cost(pm)  # core/objective.jl
            -> constraint_theta_ref(pm, i)    # form/dcp.jl (fixes va[ref_bus]=0)
            -> constraint_power_balance(pm, i)  # dispatches to form/dcp.jl
            -> constraint_ohms_yt_from(pm, i)   # form/dcp.jl (p = -b*(va_f - va_t))
            -> constraint_thermal_limit_*(pm, i) # form/shared.jl
      -> optimize_model!(pm, optimizer=optimizer)  # InfrastructureModels

```

**Layers traversed: 4** (I/O -> Core -> Form -> Prob). Full JuMP model construction with type dispatch.

## Separation of Concerns Assessment

| Concern | Location | Clean? |

|---------|----------|--------|

| File parsing | `io/` | Yes — isolated, pluggable parsers |

| Data validation | `core/data.jl` | Yes — separate from solve logic |

| Network topology | `core/base.jl` (`ref_add_core!`) | Yes — pre-computed ref dict |

| Math formulation | `form/*.jl` | Yes — clean dispatch by model type |

| Problem assembly | `prob/*.jl` | Yes — `build_*` functions compose layers |

| Solution extraction | `core/solution.jl` | Minimal (37 LOC) — defers to InfrastructureModels |

| Solver interface | InfrastructureModels | Yes — abstracted behind `optimize_model!` |

## Extension Points
1. **New formulations**: Subtype `AbstractPowerModel`, override `constraint_*` and `variable_*` methods
2. **New problems**: Write a `build_*` function composing existing variables/constraints
3. **Ref extensions**: Pass `ref_extensions` functions to `solve_model()` (e.g., `ref_add_sm!`)
4. **Custom constraints**: Direct JuMP access via `pm.model` after `instantiate_model()`
5. **Solution processors**: Pass `solution_processors` functions to `solve_model()`

## Internal Documentation
- Good: Every public function has a docstring. Type hierarchy is well-commented. The `ref_add_core!` function has extensive docstring listing all computed keys.
- Gap: The constraint template -> formulation dispatch pattern is not explicitly documented. Users must understand Julia's multiple dispatch to navigate it.
- Gap: No architecture diagram or developer guide in the repo docs.

## Quantitative Summary

| Metric | Value |

|--------|-------|

| Total source files | 43 |

| Total LOC | 18,963 |

| Abstraction layers | 4 (I/O, Core, Form, Prob) |

| Type hierarchy depth | 3 (AbstractPowerModel -> AbstractActivePowerModel -> DCPPowerModel) |

| Number of formulation types | 20+ |

| Dependency on InfrastructureModels | Heavy (model instantiation, ref building, optimization) |

# powermodels — Research: API & Formulations

## Key Findings

- PowerModels.jl v0.21.5 exports **437 public symbols** covering 18 formulation types, 13 problem builders, ~30 solve/compute functions, ~80 constraint templates, ~60 variable constructors, and ~20 matrix/network utility functions.
- Architecture cleanly separates problem specification from formulation via Julia multiple dispatch across a **four-layer design**: public API, model lifecycle (`instantiate_model`/`optimize_model!`), formulation build (constraint templates + dispatched methods), and solver (JuMP/MOI). No plugin registry or callbacks -- extension is purely via type dispatch.
- The **two-level API** (`instantiate_model` + `optimize_model!`) exposes the underlying JuMP `Model` object, enabling arbitrary custom constraint injection via `@constraint(pm.model, ...)` with full dual extraction support. This is the primary extensibility mechanism.
- **18 formulation types** span exact nonlinear (ACP, ACR, ACT, IVR), linear approximations (DCP, DCMP, BFA, NFA), quadratic approximations (DCPLL, LPACC), quadratic relaxations (SOCWR, QCRM, QCLS, SOCBF + conic variants), and SDP relaxations (SDPWRM, SparseSDPWRM). Any formulation can be combined with any compatible problem specification.
- **Solver interface is JuMP/MOI**: any solver with an MOI wrapper is compatible. Solver swap is a single argument change. Four solvers installed in this evaluation: HiGHS (LP/QP/MILP), Ipopt (NLP), GLPK (LP/MILP), SCIP (MILP/MINLP/MIQP).
- **Data model** is a nested `Dict{String,Any}` with string-keyed components (bus, branch, gen, load, shunt, storage, dcline, switch). All values in per-unit with angles in radians. MATPOWER `.m` and PSS/E `.raw` (v33) parsed natively.
- **No built-in SCUC, SCED, or SCOPF** in core package. SCOPF available via ecosystem package `PowerModelsSecurityConstrained.jl`. SCUC requires manual JuMP MILP assembly (~140 lines using PowerModels data parsing only).
- **`compute_dc_pf` / `compute_ac_pf`** bypass JuMP entirely (direct linear algebra / NLsolve), but return incomplete result dicts: no branch flows in `solution`, `termination_status` is Bool not MOI enum. Branch flows require manual post-processing via `calc_branch_flow_dc`/`calc_branch_flow_ac`.
- **Multi-period** via `replicate(data, T)` + `solve_mn_opf_strg`. Storage complementarity uses binary variables (MIQP), requiring SCIP rather than HiGHS/Ipopt. Cyclic SoC not natively enforced -- requires manual constraint injection.
- **Ecosystem** is modular: `PowerModelsDistribution.jl` (unbalanced), `PowerModelsSecurityConstrained.jl` (SCOPF), `StochasticPowerModels.jl` (chance-constrained OPF), `PowerModelsACDC.jl` (AC/DC grids) all extend the core via type dispatch.

## Detailed Notes

### Version

Version in use: **PowerModels.jl v0.21** (pinned in `Project.toml` as `PowerModels = "0.21"`). The evaluation scripts reference v0.21.5 in their headers. Julia 1.10 is required. Documentation generated August 12, 2025 using Julia 1.11.6.

Source: `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/Project.toml`

---

## API Surface — High-Level Entry Points

### Power Flow (non-optimization, no solver required)

| Function | Solver | Description |
|---|---|---|
| `PowerModels.compute_dc_pf(data)` | Julia `\` (backslash) | Solves DC PF via linear algebra. No JuMP model. Returns result dict. |
| `PowerModels.compute_ac_pf(data)` | NLsolve (Newton-Raphson) | Solves AC PF. No JuMP model. Returns result dict. |

Both `compute_*` functions avoid JuMP overhead and are faster for single solves or contingency loops. `compute_dc_pf` does not support warm-starting. `compute_ac_pf` accepts warm-starting via bus voltage initial conditions set in the data dict.

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/power-flow/>

#### OPF and Power Flow (JuMP-based)

| Function | Signature | Description |
|---|---|---|
| `solve_ac_opf` | `(file_or_data, optimizer)` | Solves AC OPF using `ACPPowerModel` formulation |
| `solve_dc_opf` | `(file_or_data, optimizer)` | Solves DC OPF using `DCPPowerModel` formulation |
| `solve_opf` | `(file_or_data, FormulationType, optimizer)` | Generic OPF — any formulation type |
| `solve_dc_pf` | `(file_or_data, optimizer)` | Solves DC PF via JuMP (same results as `compute_dc_pf`, slower) |
| `solve_mn_opf` | `(mn_data, FormulationType, optimizer)` | Multi-network (multi-period) OPF |
| `solve_mn_opf_strg` | `(mn_data, FormulationType, optimizer)` | Multi-network OPF with storage |
| `solve_ots` | `(file_or_data, FormulationType, optimizer)` | Optimal Transmission Switching |
| `solve_tnep` | `(file_or_data, FormulationType, optimizer)` | Transmission Network Expansion Planning |
| `solve_opb` | `(file_or_data, FormulationType, optimizer)` | Optimal Power Balance (copper-plate) |

The first argument can be either a file path string (`"path/to/case.m"`) or a pre-parsed data dict.

An optional `setting` keyword argument controls output behavior. To enable dual variables (for LMPs): `setting=Dict("output" => Dict("duals" => true))`.

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/> and test files in `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/expressiveness/`

#### Two-Level API (model inspection and custom constraints)

```julia

# Build JuMP model without solving
pm = PowerModels.instantiate_model(data, ACPPowerModel, PowerModels.build_opf)

# Access the underlying JuMP model directly
jump_model = pm.model

# Add custom constraints using JuMP macros
@constraint(jump_model, some_var <= limit)

# Solve with chosen optimizer
result = PowerModels.optimize_model!(pm; optimizer=HiGHS.Optimizer)

```

Variable access pattern: `PowerModels.var(pm, nw_id, :p)` returns the power flow variable dict indexed by `(branch_id, from_bus, to_bus)`. The `nw_id_default` constant is used for single-network models.

Source: `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b1_custom_constraints.jl`

## Problem Builder Functions

These are passed as the third argument to `instantiate_model`:

- `PowerModels.build_opf` — standard OPF (bus injection model)
- `PowerModels.build_opf_bf` — OPF (branch flow model)
- `PowerModels.build_opf_iv` — OPF (current-voltage model)
- `PowerModels.build_opf_ptdf` — DC OPF via PTDF
- `PowerModels.build_pf` — power flow (bus injection)
- `PowerModels.build_pf_bf` — power flow (branch flow)
- `PowerModels.build_pf_iv` — power flow (current-voltage)
- `PowerModels.build_mn_opf` — multi-network OPF
- `PowerModels.build_mn_opf_strg` — multi-network OPF with storage
- `PowerModels.build_mn_opf_bf_strg` — multi-network branch-flow OPF with storage
- `PowerModels.build_ots` — optimal transmission switching
- `PowerModels.build_tnep` — transmission expansion planning
- `PowerModels.build_opb` — copper-plate optimal power balance

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/specifications/>

---

### Supported Problem Formulations

PowerModels.jl decouples problem type from mathematical formulation. Any formulation type can be combined with any compatible problem specification.

#### Exact Non-Convex AC Formulations (nonlinear, require NLP solver like Ipopt)

| Type Name | Abstract Base | Description |
|---|---|---|
| `ACPPowerModel` | `AbstractACPModel` | AC polar coordinates (default AC formulation) |
| `ACRPowerModel` | `AbstractACRModel` | AC rectangular coordinates |
| `ACTPowerModel` | `AbstractACTModel` | AC with voltage angle, magnitude squared, and crossproduct variables; includes tangent constraints for meshed networks |
| `IVRPowerModel` | `AbstractIVRModel` | Current-voltage rectangular; nonconvex due to constant power loads and apparent power limits |

#### Linear DC Approximations (compatible with LP solvers like HiGHS/GLPK)

| Type Name | Abstract Base | Description |
|---|---|---|
| `DCPPowerModel` | `AbstractDCPModel` | Standard DC approximation; `br_b = -br_x / (br_r^2 + br_x^2)` |
| `DCMPPowerModel` | `AbstractDCMPPModel` | MATPOWER-compatible DC; `br_b = -1/br_x` with transformer parameters |
| `NFAPowerModel` | `AbstractNFAModel` | Active power only network flow (transportation model, no angles) |
| `BFAPowerModel` | `AbstractBFAModel` | Linear branch flow model approximation (neglects loss terms) |

#### Quadratic Approximations

| Type Name | Abstract Base | Description |
|---|---|---|
| `DCPLLPowerModel` | `AbstractDCPLLModel` | DC with quadratic loss terms (requires NLP solver like Ipopt, not HiGHS) |
| `LPACCPowerModel` | `AbstractLPACCModel` | Linear-Programming AC Cold-Start approximation |

#### Quadratic / Conic Relaxations (require SOCP solver)

| Type Name | Abstract Base | Description |
|---|---|---|
| `SOCWRPowerModel` | `AbstractSOCWRModel` | Second-order cone relaxation (bus injection, W-space) |
| `SOCWRConicPowerModel` | `AbstractSOCWRConicModel` | SOC relaxation cast as native conic problem |
| `SOCBFPowerModel` | `AbstractSOCBFModel` | SOC branch-flow relaxation |
| `SOCBFConicPowerModel` | `AbstractSOCBFConicModel` | SOC branch-flow in conic form |
| `QCRMPowerModel` | `AbstractQCRMPowerModel` | Quadratic-Convex relaxation with recursive McCormick |
| `QCLSPowerModel` | `AbstractQCLSModel` | Strengthened QC relaxation with extreme-point encoding |

#### SDP Relaxations (require SDP solver e.g. Mosek, COSMO, SCS)

| Type Name | Abstract Base | Description |
|---|---|---|
| `SDPWRMPowerModel` | `AbstractSDPWRMModel` | Semidefinite relaxation of AC OPF |
| `SparseSDPWRMPowerModel` | `AbstractSparseSDPWRMModel` | Sparsity-exploiting SDP relaxation using network structure |

**Total: 18 concrete formulation types** spanning the full spectrum from exact nonlinear AC to linear DC to convex relaxations. The abstract type hierarchy has ~35 abstract types enabling fine-grained dispatch.

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/>, <https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/>

#### What is NOT built-in

- **SCUC (Security-Constrained Unit Commitment)**: Not supported. The evaluation test (`test_a5_scuc.jl`) confirms this explicitly: "PowerModels has NO built-in SCUC. It is a steady-state OPF tool." A ~140-line user-assembled JuMP MILP is required. PowerModels is used only for data parsing (`parse_file`) and `make_basic_network`.
- **SCED**: Not a distinct built-in problem type (DC OPF serves the same role in the steady-state case).
- **Security-constrained OPF (SCOPF)**: No built-in formulation; contingency analysis requires looping over the `compute_dc_pf` or OPF solvers.
- **Unit commitment**: No binary commitment variables or minimum up/down time constraints.

Source: `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/expressiveness/test_a5_scuc.jl`

---

### Data Model

The PowerModels data model is a nested `Dict{String,Any}`. Keys are string-valued component IDs (e.g., `"1"`, `"2"`). The top-level dict has the following structure:

```

data = {
  "name"        => String,
  "baseMVA"     => Float64,          # system MVA base
  "per_unit"    => Bool,             # true = all values in p.u.
  "multinetwork"=> Bool,             # false for single-network
  "bus"         => Dict{String, bus_dict},
  "branch"      => Dict{String, branch_dict},
  "gen"         => Dict{String, gen_dict},
  "load"        => Dict{String, load_dict},
  "storage"     => Dict{String, storage_dict},
  "switch"      => Dict{String, switch_dict},
  "dcline"      => Dict{String, dcline_dict},
  "shunt"       => Dict{String, shunt_dict},
}

```

#### Bus fields (required)
- `"index"` — integer ID
- `"status"` — {0, 1}
- `"bus_type"` — 1=PQ, 2=PV, 3=slack/reference, 4=inactive
- `"vm"` — voltage magnitude (p.u.)
- `"va"` — voltage angle (radians)
- `"vmin"`, `"vmax"` — voltage magnitude bounds (p.u.)

#### Branch fields (required)
- `"index"`, `"f_bus"`, `"t_bus"` — topology
- `"br_r"`, `"br_x"` — series resistance/reactance (p.u.)
- `"br_status"` — {0, 1}
- `"tap"` — transformer turns ratio (p.u., 1.0 for lines)
- `"shift"` — transformer phase shift (radians)
- `"rate_a"`, `"rate_b"`, `"rate_c"` — thermal ratings (MVA)
- `"angmin"`, `"angmax"` — angle difference bounds (radians)

#### Generator fields (required)
- `"index"`, `"gen_bus"` — location
- `"pg"`, `"qg"` — active/reactive power dispatch (p.u.)
- `"pmin"`, `"pmax"`, `"qmin"`, `"qmax"` — power bounds (p.u.)
- `"gen_status"` — {0, 1}
- `"model"` — cost model: 1=piecewise linear, 2=polynomial
- `"ncost"`, `"cost"` — cost function coefficients

#### Load fields (required)
- `"index"`, `"load_bus"`, `"pd"`, `"qd"`, `"status"`

All values are in per-unit by default. The `make_mixed_units!()` function converts to SI (MW, MVAr, etc.).

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/>

---

### Result Data Format

All solve functions return a Julia `Dict` with the following top-level keys:

- `"optimizer"` — name of the solver
- `"termination_status"` — MOI termination status enum (e.g., `OPTIMAL`, `LOCALLY_SOLVED`, `INFEASIBLE`)
- `"primal_status"` — MOI primal status
- `"dual_status"` — MOI dual status
- `"solve_time"` — Float64, seconds
- `"objective"` — Float64, final objective value
- `"objective_lb"` — lower bound (available for MIP solvers)
- `"solution"` — Dict mirroring network data structure with solved values

#### Solution sub-keys (typical OPF result)

- `result["solution"]["bus"]["1"]` → `{"vm" => Float64, "va" => Float64, "lam_kcl_r" => Float64}` (lam_kcl_r = LMP dual, only when duals enabled)
- `result["solution"]["gen"]["1"]` → `{"pg" => Float64, "qg" => Float64}`
- `result["solution"]["branch"]["1"]` → `{"pf" => Float64, "pt" => Float64, "qf" => Float64, "qt" => Float64}`

#### Utility functions for result processing

- `PowerModels.update_data!(data, result["solution"])` — merges solution values back into the network data dict (in-place mutation)
- `PowerModels.print_summary(result["solution"])` — prints a text summary
- `PowerModels.calc_branch_flow_ac(data)` — computes AC branch P/Q flows from updated data dict
- `PowerModels.calc_branch_flow_dc(data)` — computes DC branch flows (pf, pt) from updated data dict

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/result-data/> and test files

---

### Solver Interface

PowerModels uses JuMP as its modeling layer, which in turn uses MathOptInterface (MOI). Any solver with an MOI wrapper is compatible.

#### Solver configuration

```julia

# Simple: pass the optimizer constructor directly
PowerModels.solve_ac_opf(data, Ipopt.Optimizer)

# With attributes: use JuMP.optimizer_with_attributes
optimizer = JuMP.optimizer_with_attributes(
    HiGHS.Optimizer,
    "time_limit" => 300.0,
    "presolve" => "on",
    "threads" => 1,
    "output_flag" => true,
)
PowerModels.solve_dc_opf(data, optimizer)

```

## Solvers installed in this evaluation environment

| Package | Solver | Problem Types |
|---|---|---|
| `HiGHS.jl` v1 | HiGHS | LP, QP, MILP (no MIQP) |
| `Ipopt.jl` v1 | Ipopt | NLP (AC OPF) |
| `GLPK.jl` v1 | GLPK | LP, MILP |
| `SCIP.jl` v0.11 | SCIP | MILP, nonconvex MINLP |

Source: `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/Project.toml`

**Important limitation found in testing**: HiGHS cannot solve MIQP (mixed-integer quadratic programs). The SCUC test (`test_a5_scuc.jl`) had to linearize quadratic generator cost functions (dropping the quadratic term) because HiGHS rejects MIQP formulations. For AC OPF problems requiring quadratic costs with integer variables, SCIP or a commercial solver would be needed.

### `compute_ac_pf` and `compute_dc_pf` — solver-free paths

These functions bypass JuMP and MOI entirely:
- `compute_dc_pf` uses Julia's built-in `\` operator (sparse LU factorization) for the DC linear system
- `compute_ac_pf` uses NLsolve.jl (Newton-Raphson) for the AC nonlinear system

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/power-flow/>

---

### Input/Output Formats

#### Input formats (native parsing)

| Format | Function | Notes |
|---|---|---|
| MATPOWER `.m` | `PowerModels.parse_file("case.m")` | Primary format; all test cases use this |
| PTI `.raw` (PSS/E) | `PowerModels.parse_file("case.raw"; import_all=true)` | PSS/E RAW format |
| JSON | `PowerModels.parse_file("case.json")` | Can also load exported PowerModels dicts |

No native support for CIM, CGMES, CSV, or other grid model formats.

#### Output formats (native)

PowerModels exports **`export_matpower`** and **`export_pti`** functions (discovered in the 437-symbol export list). These were not tested in the evaluation and are not documented prominently. Results are also available as Julia dicts. Export to other formats:

- **MATPOWER `.m`**: `PowerModels.export_matpower("output.m", data)` (exported but untested)
- **PSS/E `.raw`**: `PowerModels.export_pti("output.raw", data)` (exported but untested)
- **JSON**: `PowerModels.export_file("output.json", data)` (generic export dispatcher)
- **CSV**: Use DataFrames.jl + CSV.jl (3-4 lines per component type, as shown in test B-5)

**Correction**: The earlier assessment that "no MATPOWER write, no PSS/E write" is incorrect. Both `export_matpower` and `export_pti` are in the public API. Their completeness and correctness remain unverified.

Source: `names(PowerModels)` export list; `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b5_interoperability.jl`

---

### Multi-Network (Multi-Period) Support

The `replicate(data, T)` function converts a single-network dict into a multi-network dict with `T` identical time periods. Users then modify individual periods to vary load or generation:

```julia

mn_data = PowerModels.replicate(data, 24)

# Modify each time period
for t in 1:24
    nw = mn_data["nw"][string(t)]
    for (lid, load) in nw["load"]
        load["pd"] *= hourly_load_profile[t]
    end
end

result = PowerModels.solve_mn_opf(mn_data, DCPPowerModel, optimizer)

```

Multi-period storage optimization: `solve_mn_opf_strg` adds energy storage balance constraints across periods using the `time_elapsed` field.

`replicate()` only works on single-network data. Calling it on already-replicated data throws an error.

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/multi-networks/> and `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b4_stochastic_wrapping_small.jl`

---

## Basic Data Utilities (Matrix-Level Access)

The `make_basic_network(data)` function normalizes a network dict to a "basic" form (contiguous bus numbering 1:N, single connected component, no inactive components, no DC lines or switches). This is required before calling the matrix utility functions:

| Function | Returns | Notes |
|---|---|---|
| `make_basic_network(data)` | normalized data dict | Prerequisite for matrix functions |
| `calc_basic_ptdf_matrix(data)` | `Matrix{Float64}` (branches × buses) | Full PTDF matrix |
| `calc_basic_ptdf_row(data, branch_idx)` | `Vector{Float64}` | Single PTDF row; more memory-efficient |
| `calc_basic_admittance_matrix(data)` | sparse complex matrix | Y-bus |
| `calc_basic_susceptance_matrix(data)` | sparse real matrix | B-matrix |
| `calc_basic_branch_susceptance_matrix(data)` | matrix | Branch susceptance |
| `calc_basic_incidence_matrix(data)` | sparse Int matrix | Bus-branch incidence |
| `calc_basic_jacobian_matrix(data)` | sparse matrix | AC power flow Jacobian |
| `calc_basic_bus_voltage(data)` | complex vector | Bus voltages |
| `calc_basic_bus_injection(data)` | complex vector | Bus power injections |
| `calc_basic_branch_series_impedance(data)` | complex vector | Series impedance per branch |
| `compute_basic_dc_pf(data)` | voltage angle vector | DC PF result as angles array |
| `calc_connected_components(data)` | set of sets | Returns island components |

PTDF validation from test B-9 confirms that `calc_basic_ptdf_matrix` predictions match `compute_dc_pf` flows within 1e-6 tolerance on case39.

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/basic-data-utilities/> and `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b9_ptdf_extraction.jl`

---

### LMP Extraction

LMPs are accessible when duals are requested. The dual on the KCL (power balance) constraint at each bus is stored in `solution["bus"][id]["lam_kcl_r"]`. This was confirmed working for DC OPF in test A-3.

For AC OPF, LMPs are expected at `lam_kcl_r` and `lam_kcl_i` (real and imaginary parts of the complex KCL dual).

Reference bus LMP will be zero (or the reference price) depending on formulation.

Source: `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/expressiveness/test_a3_dcopf.jl`

---

### Storage Model

Storage (BESS) is a native component type stored under `data["storage"]`. Required fields include energy capacity, charge/discharge ratings, efficiency parameters (`charge_efficiency`, `discharge_efficiency`), and a resistance/reactance pair for losses.

The multi-network OPF-with-storage (`solve_mn_opf_strg`) enforces inter-period energy balance:

```

e[t] - e[t-1] = time_elapsed * (η_charge * sc[t] - sd[t] / η_discharge)

```

Six per-period variables per storage device: energy level, charge amount, discharge amount, reactive power slack, complex injection power, complex injection current.

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/storage/>

---

### Architecture: Four-Layer Dispatch Design

PowerModels' internal architecture is organized into four cleanly separated layers, with Julia multiple dispatch as the sole extension mechanism:

1. **Public API** (`src/prob/*.jl`): One-line entry points (e.g., `solve_dc_opf`) that delegate to `solve_model` with formulation and builder bound.
2. **Model lifecycle** (`src/core/base.jl`): `solve_model` -> `instantiate_model` -> `optimize_model!`. Users can intercept between instantiation and optimization.
3. **Formulation build** (`build_*` functions + constraint templates + formulation methods): Constraint templates (`constraint_power_balance`, etc.) are defined over `AbstractPowerModel` and dispatch to formulation-specific implementations based on type. Data extraction is decoupled from mathematical formulation.
4. **Solver layer** (JuMP/MOI): Completely isolated. Solver swap is a single argument change.

The type hierarchy enforces separation: constraint templates never reference formulation-specific types directly; the dispatch system selects the correct implementation at compile time.

Source: evaluation observation `arch-quality-extensibility-B6_four_layer_dispatch_architecture.md`, confirmed in source code

### Extension Patterns

1. **Custom constraints on existing model**: Use `instantiate_model` + `@constraint` on `pm.model`, then `optimize_model!`. No subtyping required. This is the primary documented extension path (test B-1). Dual extraction via `JuMP.dual()` works correctly on custom constraints.

2. **Custom formulation**: Create a new Julia struct subtyping `AbstractPowerModel` or one of its abstract subtypes, then define specialized variable/constraint methods dispatching on the new type. This requires understanding the method dispatch system but does not require patching source code.

3. **Custom problem specification**: Create a new `build_myproblem(pm)` function following the convention, then pass it to `instantiate_model`. No registration step needed.

4. **Graph access**: PowerModels has no native Graphs.jl integration and no adjacency API. The network graph must be built manually from `branch["f_bus"]` / `branch["t_bus"]` fields (~15 lines). `PowerModelsAnalytics.jl` (not installed in this evaluation) provides a Graphs.jl bridge.

5. **Reference bus change**: Change `bus["bus_type"]` to 3 for the new slack bus and to 2 for the old one. Takes 2 lines. LMPs shift but dispatch is invariant (confirmed in test B-8).

6. **Distributed slack**: No built-in support. Requires manual PTDF-based DC OPF construction (~150 lines in test B-8).

Source: test files in `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/`

---

### Ecosystem Extensions

PowerModels.jl serves as the foundation for a modular ecosystem of extension packages, all using the same type-dispatch architecture:

| Package | Purpose | Maintained by |
|---|---|---|
| [`PowerModelsDistribution.jl`](https://github.com/lanl-ansi/PowerModelsDistribution.jl) | Unbalanced multi-phase distribution network optimization | LANL-ANSI |
| [`PowerModelsSecurityConstrained.jl`](https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl) | Security-constrained OPF (used in ARPA-e GOC Challenge 1) | LANL-ANSI |
| [`StochasticPowerModels.jl`](https://github.com/Electa-Git/StochasticPowerModels.jl) | Stochastic/chance-constrained OPF with polynomial chaos expansion | Electa (KU Leuven) |
| [`PowerModelsACDC.jl`](https://github.com/electa-git/PowerModelsACDC.jl) | AC/DC hybrid grid modeling with converter stations | Electa |
| [`PowerModelsGMD.jl`](https://github.com/lanl-ansi/PowerModelsGMD.jl) | Geomagnetically-induced current modeling | LANL-ANSI |
| [`PowerModelsONM.jl`](https://github.com/lanl-ansi/PowerModelsONM.jl) | Outage and network management for distribution | LANL-ANSI |
| [`PowerModelsProtection.jl`](https://github.com/lanl-ansi/PowerModelsProtection.jl) | Protection coordination for distribution grids | LANL-ANSI |
| [`PowerModelsInterface.jl`](https://github.com/NREL-Sienna/PowerModelsInterface.jl) | Bridge between PowerSystems.jl (Sienna) and PowerModels.jl | NREL-Sienna |

None of these ecosystem packages are installed in the evaluation environment. The SCOPF test (A-9) implemented manual iterative Benders cutting-plane using the two-level API instead of `PowerModelsSecurityConstrained.jl`.

Source: <https://github.com/lanl-ansi/PowerModels.jl>, web search results

---

### Complete Exported API Surface (437 symbols)

The full `names(PowerModels)` export list (v0.21.5) breaks down as follows:

| Category | Count | Examples |
|---|---|---|
| Concrete formulation types | 18 | `ACPPowerModel`, `DCPPowerModel`, `SOCWRPowerModel`, ... |
| Abstract formulation types | ~35 | `AbstractACPModel`, `AbstractDCPModel`, `AbstractConicModel`, ... |
| Solve functions | ~20 | `solve_ac_opf`, `solve_dc_opf`, `solve_opf`, `solve_mn_opf_strg`, `solve_ots`, `solve_tnep`, ... |
| Compute functions (JuMP-free) | 4 | `compute_ac_pf`, `compute_dc_pf`, `compute_basic_dc_pf`, `compute_ac_pf!` |
| Build functions (problem specs) | 13 | `build_opf`, `build_pf`, `build_mn_opf_strg`, `build_ots`, `build_tnep`, ... |
| Constraint templates | ~80 | `constraint_power_balance`, `constraint_ohms_yt_from`, `constraint_thermal_limit_from`, ... |
| Variable constructors | ~60 | `variable_bus_voltage`, `variable_gen_power`, `variable_branch_power`, `variable_storage_energy`, ... |
| Matrix/network utilities | ~20 | `calc_basic_ptdf_matrix`, `calc_admittance_matrix`, `calc_susceptance_matrix`, `make_basic_network`, ... |
| Data correction functions | ~15 | `correct_network_data!`, `correct_bus_types!`, `correct_thermal_limits!`, ... |
| I/O functions | 7 | `parse_file`, `parse_matpower`, `parse_psse`, `export_file`, `export_matpower`, `export_pti`, `parse_json` |
| Solution utilities | ~10 | `sol_data_model!`, `update_data!`, `print_summary`, `sol_component_value`, ... |
| Model lifecycle | 4 | `instantiate_model`, `optimize_model!`, `solve_model`, `apply_pm!` |
| MOI re-exports | ~30 | `OPTIMAL`, `INFEASIBLE`, `LOCALLY_SOLVED`, `TerminationStatusCode`, `ResultStatusCode`, ... |

**Notable: `export_matpower` and `export_pti` exist** (contradicting the earlier finding that no MATPOWER/PSS/E export is built-in). These were not tested in the evaluation.

Source: `names(PowerModels)` output from Julia REPL inside devcontainer (v0.21.5)

---

### Mathematical Model (Objective and Constraints)

The core OPF formulation minimizes quadratic generator cost:

**Objective:** `min sum_k [ c2_k * pg_k^2 + c1_k * pg_k + c0_k ]`

Three AC OPF variants are formally specified in the documentation (Bus Injection Model, Branch Flow Model, Current-Voltage formulation), all sharing:

- **Sets:** N (buses), G (generators with G_i at bus i), E (branches forward/reverse), L (loads), S (shunts)
- **Decision variables:** Generator complex power S^g_k, bus voltages V_i, branch flows S_ij
- **Physical constraints:** Kirchhoff's Current Law (power/current balance), Ohm's Law (voltage drops across impedances)
- **Operational bounds:** Generator P/Q limits, voltage magnitude bounds, branch thermal/current limits, voltage angle difference constraints
- **Reference:** Reference bus angle pinned to zero

Cost models supported: piecewise linear (`model=1`) and polynomial (`model=2`, up to quadratic).

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/math-model/>

---

### Observed API Friction (from evaluation testing)

These friction points were documented during the evaluation and are relevant to API quality assessment:

| Friction | Severity | Detail |
|---|---|---|
| `compute_dc_pf` omits branch flows | Moderate | Result dict has no `"branch"` key; requires manual `(va_from - va_to - shift) / (br_x * tap)` |
| `compute_ac_pf` omits branch flows | Low | Requires `update_data!` + `calc_branch_flow_ac` post-processing |
| `compute_*` returns Bool status | Low | `termination_status` is `Bool`, not MOI `TerminationStatusCode`; inconsistent with `solve_*` |
| `baseMVA` must be `Float64` | Low | Integer value causes type errors in some code paths |
| Quadratic costs + HiGHS SCOPF | Moderate | HiGHS QP solver reports `OTHER_ERROR` when security constraints are added with c2 > 0 |
| `DCPLLPowerModel` requires Ipopt | Low | Lossy DC approximation is NLP, not compatible with HiGHS |
| `make_basic_network` absorbs phase shifts | Low | Phase shift angles reset; PTDF matrix does not reflect PST topology |
| No native distributed slack | Low | Requires ~150-line manual PTDF-based implementation |
| No native Graphs.jl integration | Low | ~15 lines manual adjacency construction |
| Storage OPF requires SCIP (MIQP) | Moderate | `build_mn_opf_strg` uses binary complementarity; HiGHS/Ipopt reject |
| Cyclic SoC not natively enforced | Low | `constraint_storage_state_initial` only pins period 1; cyclic requires manual injection |
| SCIP cannot return LP duals | Moderate | Two-phase fix-and-price needed for LMPs from MIP storage OPF |
| No built-in contingency solver | Moderate | SCOPF requires manual Benders or installing `PowerModelsSecurityConstrained.jl` |

Source: observation files in `evaluations/powermodels/results/observations/`

---

## Sources

### Official Documentation
1. <https://lanl-ansi.github.io/PowerModels.jl/stable/> — Official documentation homepage
2. <https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/> — Getting started / quick reference
3. <https://lanl-ansi.github.io/PowerModels.jl/stable/specifications/> — Problem specifications (build_* functions)
4. <https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/> — Network formulation types
5. <https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/> — Detailed formulation type hierarchy and references
6. <https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/> — Network data dictionary format
7. <https://lanl-ansi.github.io/PowerModels.jl/stable/result-data/> — Result data format
8. <https://lanl-ansi.github.io/PowerModels.jl/stable/math-model/> — Mathematical formulations
9. <https://lanl-ansi.github.io/PowerModels.jl/stable/power-flow/> — Power flow solve functions
10. <https://lanl-ansi.github.io/PowerModels.jl/stable/storage/> — Storage model
11. <https://lanl-ansi.github.io/PowerModels.jl/stable/multi-networks/> — Multi-network support
12. <https://lanl-ansi.github.io/PowerModels.jl/stable/basic-data-utilities/> — Basic data utility functions
13. <https://lanl-ansi.github.io/PowerModels.jl/stable/utilities/> — Advanced utility functions (OBBT, PTDF cuts)

### GitHub Repositories

1. <https://github.com/lanl-ansi/PowerModels.jl> — Main repository (LANL-ANSI)
2. <https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl> — SCOPF extension
3. <https://github.com/lanl-ansi/PowerModelsDistribution.jl> — Distribution network extension
4. <https://github.com/Electa-Git/StochasticPowerModels.jl> — Stochastic OPF extension
5. <https://github.com/NREL-Sienna/PowerModelsInterface.jl> — PowerSystems.jl bridge

### Evaluation Files

1. `evaluations/powermodels/Project.toml` — Installed version and solver dependencies
2. `evaluations/powermodels/verify_install.jl` — Installation verification
3. Evaluation test scripts in `evaluations/powermodels/tests/expressiveness/` (A-1 through A-12)
4. Evaluation test scripts in `evaluations/powermodels/tests/extensibility/` (B-1 through B-9)
5. Observation reports in `evaluations/powermodels/results/observations/` (13 documented friction/architecture findings)

### Runtime Verification

1. `names(PowerModels)` output from Julia REPL inside devcontainer (v0.21.5, 437 exported symbols)

---

## Gaps and Uncertainties

- **`export_matpower` / `export_pti` completeness**: Both functions are exported but were not tested in this evaluation. It is unknown whether they produce round-trip-correct output for all component types (storage, switches, DC lines).
- **AC OPF LMP (`lam_kcl_i`)**: The reactive power dual `lam_kcl_i` is expected for AC formulations alongside `lam_kcl_r`, but no test in this evaluation exercises AC OPF LMP extraction directly. Behavior needs verification.
- **PSS/E `.raw` parsing completeness**: Documentation confirms PTI RAW v33 format support with `import_all=true`, covering buses, generators, branches, transformers, HVDC lines. The extent of field coverage for FACTS devices was not verified.
- **`SDPWRMPowerModel` solver requirements**: Requires an SDP solver (e.g., Mosek, COSMO, SCS). None of the four installed solvers (HiGHS, Ipopt, GLPK, SCIP) support SDP natively. The SDP relaxation formulations are unavailable in this evaluation's solver set.
- **`QCRMPowerModel` compatibility**: QC relaxations should work with Ipopt but were not tested in the evaluation.
- **Transformer modeling depth**: The branch model includes `tap` and `shift` fields for transformers. OPF variants with OLTC (`constraint_ohms_y_oltc_pst_from/to`) and PST variables (`variable_branch_transform_angle`, `variable_branch_transform_magnitude`) are exported but were not tested. These were added in v0.21.
- **`make_basic_network` bus renumbering**: Renumbers buses to contiguous 1:N. The mapping between original bus IDs and basic network bus indices must be reconstructed manually (as shown in test B-9). No built-in mapping dict is returned.
- **`PowerModelsSecurityConstrained.jl` maintenance status**: Not installed in the evaluation. Its compatibility with PowerModels v0.21.5 and solver support are unverified.
- **`StochasticPowerModels.jl` maturity**: Developed by Electa (KU Leuven), supports chance-constrained OPF via polynomial chaos expansion. Not tested; maintenance cadence unknown.
- **PowerModelsAnalytics.jl**: A companion package providing visualization and Graphs.jl integration is referenced in test B-2 comments but is not installed in this evaluation. Its API was not researched.
- **Switch component**: The `switch` data type and associated `constraint_switch_*` / `variable_switch_*` functions are exported but were not exercised in any test. Their interaction with topology propagation (`resolve_switches!`, `propagate_topology_status!`) is documented but unverified.

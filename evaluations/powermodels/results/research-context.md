# powermodels — Research Context

## Detailed Notes

### Version

Version in use: **PowerModels.jl v0.21** (pinned in `Project.toml` as `PowerModels = "0.21"`). The evaluation scripts reference v0.21.5 in their headers. Julia 1.10 is required.

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

## Build JuMP model without solving
pm = PowerModels.instantiate_model(data, ACPPowerModel, PowerModels.build_opf)

## Access the underlying JuMP model directly
jump_model = pm.model

## Add custom constraints using JuMP macros
@constraint(jump_model, some_var <= limit)

## Solve with chosen optimizer
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

#### AC Formulations (nonlinear, require NLP solver like Ipopt)

| Type Name | Base Type | Description |
|---|---|---|
| `ACPPowerModel` | `AbstractACPForm` | AC polar coordinates (default AC formulation) |
| `ACRPowerModel` | `AbstractACRForm` | AC rectangular coordinates |
| `ACTPowerModel` | `AbstractACTForm` | AC with voltage product variables |
| `IVRPowerModel` | `AbstractIVRModel` | Current-voltage rectangular |

#### DC Approximations (linear, compatible with LP solvers like HiGHS/GLPK)

| Type Name | Base Type | Description |
|---|---|---|
| `DCPPowerModel` | `AbstractDCPForm` | Standard DC approximation |
| `DCMPPowerModel` | `AbstractDCMPForm` | DC with phase-shifting transformers |
| `NFAPowerModel` | `AbstractNFAForm` | Network-flow approximation (no angle constraints) |

#### Convex Relaxations (require SOCP/SDP solvers)

| Type Name | Base Type | Description |
|---|---|---|
| `SOCWRPowerModel` | `AbstractWRForm` | Second-order cone (W relaxation) |
| `SOCBFPowerModel` | `AbstractSOCBFModel` | SOC branch-flow relaxation |
| `SOCBFConicPowerModel` | `AbstractSOCBFConicModel` | SOC branch-flow (conic form) |
| `QCRMPowerModel` | `AbstractWRForm` | Quadratic convex relaxation |
| `QCLSPowerModel` | — | QC with linear voltage magnitude |
| `SDPWRMPowerModel` | `AbstractSDPWRMModel` | Semidefinite programming relaxation |

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/>

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

## Simple: pass the optimizer constructor directly
PowerModels.solve_ac_opf(data, Ipopt.Optimizer)

## With attributes: use JuMP.optimizer_with_attributes
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

PowerModels has no built-in export to common formats (no MATPOWER write, no PSS/E write). Results are Julia dicts. Export to external formats requires user code:

- **CSV**: Use DataFrames.jl + CSV.jl (3–4 lines per component type, as shown in test B-5)
- **JSON**: `JSON.json(result, 2)` (used in all test scripts)
- **MATPOWER**: Not built-in; external package `PowerModelsAnalytics.jl` may help

Source: `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b5_interoperability.jl`

---

### Multi-Network (Multi-Period) Support

The `replicate(data, T)` function converts a single-network dict into a multi-network dict with `T` identical time periods. Users then modify individual periods to vary load or generation:

```julia

mn_data = PowerModels.replicate(data, 24)

## Modify each time period
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

### Extension Patterns

1. **Custom constraints on existing model**: Use `instantiate_model` + `@constraint` on `pm.model`, then `optimize_model!`. No subtyping required. This is the primary documented extension path (test B-1).

2. **Custom formulation**: Create a new Julia struct subtyping `AbstractPowerModel` or one of its abstract subtypes, then define specialized variable/constraint methods dispatching on the new type. This requires understanding the method dispatch system but does not require patching source code.

3. **Custom problem specification**: Create a new `build_myproblem(pm)` function following the convention, then pass it to `instantiate_model`. No registration step needed.

4. **Graph access**: PowerModels has no native Graphs.jl integration and no adjacency API. The network graph must be built manually from `branch["f_bus"]` / `branch["t_bus"]` fields (~15 lines). `PowerModelsAnalytics.jl` (not installed in this evaluation) provides a Graphs.jl bridge.

5. **Reference bus change**: Change `bus["bus_type"]` to 3 for the new slack bus and to 2 for the old one. Takes 2 lines. LMPs shift but dispatch is invariant (confirmed in test B-8).

6. **Distributed slack**: No built-in support. Requires manual PTDF-based DC OPF construction (~150 lines in test B-8).

Source: test files in `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/`

---

## Sources

1. <https://lanl-ansi.github.io/PowerModels.jl/stable/> — Official documentation homepage
2. <https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/> — Getting started / quick reference
3. <https://lanl-ansi.github.io/PowerModels.jl/stable/specifications/> — Problem specifications (build_* functions)
4. <https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/> — Network formulation types
5. <https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/> — Network data dictionary format
6. <https://lanl-ansi.github.io/PowerModels.jl/stable/result-data/> — Result data format
7. <https://lanl-ansi.github.io/PowerModels.jl/stable/math-model/> — Mathematical formulations
8. <https://lanl-ansi.github.io/PowerModels.jl/stable/power-flow/> — Power flow solve functions
9. <https://lanl-ansi.github.io/PowerModels.jl/stable/storage/> — Storage model
10. <https://lanl-ansi.github.io/PowerModels.jl/stable/multi-networks/> — Multi-network support
11. <https://lanl-ansi.github.io/PowerModels.jl/stable/basic-data-utilities/> — Basic data utility functions
12. <https://lanl-ansi.github.io/PowerModels.jl/stable/utilities/> — Advanced utility functions (OBBT, PTDF cuts)
13. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/Project.toml` — Installed version and solver dependencies
14. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/verify_install.jl` — Installation verification (uses `solve_dc_pf`)
15. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/expressiveness/test_a1_dcpf.jl` — DCPF API usage (`compute_dc_pf`, `calc_branch_flow_dc`)
16. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/expressiveness/test_a2_acpf.jl` — ACPF API usage (`compute_ac_pf`, `calc_branch_flow_ac`)
17. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/expressiveness/test_a3_dcopf.jl` — DC OPF with LMP extraction
18. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/expressiveness/test_a5_scuc.jl` — SCUC (no built-in; manual JuMP assembly)
19. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b1_custom_constraints.jl` — Two-level API for custom constraints
20. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b2_graph_access.jl` — No native graph API; manual adjacency build
21. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b3_contingency_loop.jl` — N-1 contingency loop with `calc_connected_components`
22. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b4_stochastic_wrapping_small.jl` — Multi-period stochastic DC OPF via `replicate` + `solve_mn_opf`
23. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b5_interoperability.jl` — Export to DataFrames/CSV
24. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b7_ac_feasibility_extension.jl` — DC OPF → AC PF feasibility workflow
25. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b8_reference_bus_config_small.jl` — Reference bus and distributed slack
26. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b9_ptdf_extraction.jl` — PTDF matrix extraction via `calc_basic_ptdf_matrix`

---

## Gaps and Uncertainties

- **`solve_dc_pf` vs `compute_dc_pf` distinction**: The `verify_install.jl` script uses `solve_dc_pf` (JuMP-based), while test A-1 uses `compute_dc_pf` (solver-free). Both exist and return equivalent results but with different overhead. The exact API signature of `solve_dc_pf` was not fully confirmed from docs—it may require passing a solver.
- **AC OPF LMP (lam_kcl_i)**: The reactive power dual `lam_kcl_i` is expected for AC formulations alongside `lam_kcl_r`, but no test in this evaluation exercises AC OPF LMP extraction directly. Behavior needs verification.
- **PSS/E `.raw` parsing completeness**: The documentation confirms PTI RAW format is supported with `import_all=true`, but the extent of field coverage (e.g., shunts, HVDC, FACTS) relative to MATPOWER was not verified.
- **`SDPWRMPowerModel` solver requirements**: Requires an SDP solver (e.g., Mosek, COSMO, SCS). None of the four installed solvers (HiGHS, Ipopt, GLPK, SCIP) support SDP natively. The SDP relaxation formulation is unavailable in this evaluation's solver set.
- **`QCRMPowerModel` compatibility**: QC relaxations should work with Ipopt but were not tested in the available test files.
- **Transformer modeling depth**: The branch model includes `tap` and `shift` fields for transformers. Phase-shifting transformer support is documented but was not exercised in any test file reviewed.
- **`make_basic_network` bus renumbering**: `make_basic_network` renumbers buses to contiguous 1:N. The mapping between original bus IDs and basic network bus indices must be reconstructed manually (as shown in test B-9). No built-in mapping dict is returned by the function.
- **Documentation URL structure**: Several expected documentation pages (e.g., `/solver/`, `/file-io/`, `/network-formulations/`) returned 404, suggesting the stable docs may be structured differently from expected paths. The content was accessed through working pages and source code instead.
- **PowerModelsAnalytics.jl**: A companion package providing visualization and Graphs.jl integration is referenced in test B-2 comments but is not installed in this evaluation. Its API was not researched.

---

## Extensions & Architecture

## powermodels — Research: Extensions & Architecture

## Key Findings

- PowerModels is built on a **two-level extension model**: (1) subtype `AbstractPowerModel` to add a new mathematical formulation, and (2) write a custom `build_*` function that calls variable/constraint templates. No plugin registration or callback registry is needed — Julia multiple dispatch is the extension mechanism.
- The `instantiate_model(data, ModelType, build_fn; ref_extensions=[...])` function accepts a `ref_extensions` array of functions that are called during reference-data preprocessing, providing a clean hook point for adding derived data structures (e.g., custom arc mappings, extra indexed sets) before the JuMP model is constructed.
- The **two-level API** (`instantiate_model` → `optimize_model!`) gives direct access to `pm.model` (the underlying JuMP model) between construction and solve. Custom JuMP constraints can be appended with `@constraint(pm.model, ...)` without any patching. Dual values are extractable via `JuMP.dual()`.
- There is **no native Graphs.jl integration**. Network graph structure must be built manually from `data["branch"]["f_bus"]` / `"t_bus"` fields. PowerModelsAnalytics.jl adds visualization (Vega-based) and exposes `build_network_graph`, but is a separate package not installed in the evaluation environment.
- **DataFrame interoperability is trivial**: results are plain Julia `Dict`s with string keys. Constructing a `DataFrame` from result dicts takes 3–4 lines per component type; no custom serialization is required.
- The **`ref_add_core!`** function (source: `src/core/base.jl`) is the canonical reference-data builder. It populates `:bus`, `:gen`, `:branch`, `:arcs_from`, `:arcs_to`, `:arcs`, `:bus_arcs`, `:buspairs`, and related lookup tables. Custom `ref_extensions` functions receive the same `ref` dict and can add arbitrary keys.
- **Constraint templates** (`src/core/constraint_template.jl`) decouple data extraction from mathematical formulation: each template function is defined over `AbstractPowerModel` and passes named scalar arguments to a formulation-specific method. Adding a custom constraint requires implementing only the formulation-specific method (or reusing the template pattern for a new formulation).
- **No distributed-slack support** in the native API. Implementing load-proportional distributed slack requires ~150 lines of manual JuMP code using `calc_basic_ptdf_matrix` as a building block.
- The **PTDF matrix is a first-class API**: `make_basic_network` + `calc_basic_ptdf_matrix` returns a dense `(branches × buses)` matrix. A single-row variant `calc_basic_ptdf_row(data, l)` is also available for memory-efficient access.
- The ecosystem follows the **InfrastructureModels.jl** pattern: `AbstractPowerModel <: _IM.AbstractInfrastructureModel`. Extension packages (PowerModelsDistribution, PowerModelsSecurityConstrained, PowerModelsAnnex, etc.) all subtype this hierarchy, enabling multi-infrastructure co-optimization through InfrastructureModels.

## Detailed Notes

### Extension via Julia Multiple Dispatch (Custom Formulations)

PowerModels uses Julia's type system as its extension mechanism. There is no plugin registry, no hook list, and no callback API. Instead:

1. Define a new abstract type: `abstract type MyModel <: AbstractPowerModel end` (or subtype an existing intermediate like `AbstractDCPModel`).
2. Define a concrete struct: `mutable struct MyPowerModel <: MyModel; @pm_fields; end`
3. Dispatch new variable/constraint methods on `MyModel` or `MyPowerModel` where the built-in implementations differ.
4. Write a `build_my_problem(pm::AbstractPowerModel)` function that composes variable and constraint calls.
5. Call: `instantiate_model(data, MyPowerModel, build_my_problem)`.

The `@pm_fields` macro (defined in `base.jl` via `_IM.@def`) injects the five standard fields: `model`, `data`, `setting`, `solution`, `ref`. Source: `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/base.jl`.

The type hierarchy defined in `src/core/types.jl` includes:
- `AbstractActivePowerModel <: AbstractPowerModel` (DC/active-only models)
- `AbstractConicModel <: AbstractPowerModel` (for SDP/conic solvers)
- `AbstractBFModel <: AbstractPowerModel` (branch-flow models)
- `AbstractACPModel <: AbstractPowerModel`, `AbstractDCPModel <: AbstractActivePowerModel`, etc.

### `ref_extensions` — Pre-Build Hook

`instantiate_model` delegates to `_IM.instantiate_model(data, model_type, build_method, ref_add_core!, _pm_global_keys, pm_it_sym; kwargs...)`. The `ref_extensions` keyword accepts an array of functions with signature `(ref::Dict{Symbol,Any}) -> nothing`. These are called after `ref_add_core!` populates the standard sets, allowing extensions to add custom lookup tables before any variables or constraints are built.

Example usage pattern (from PowerModelsDistribution):

```julia

pm = PowerModels.instantiate_model(data, ACPPowerModel, build_opf;
    ref_extensions=[my_custom_ref_fn!])

```

This is the documented hook for packages that extend PowerModels (e.g., PowerModelsDistribution uses `ref_add_arcs_trans!`). Source: `base.jl` line `_IM.instantiate_model(...)`.

### Two-Level API: `instantiate_model` + `optimize_model!`

The high-level `solve_*` functions (e.g., `solve_dc_opf`) are thin wrappers over `solve_model`, which calls `instantiate_model` then `optimize_model!`. Using the two-level API directly:

```julia

pm = PowerModels.instantiate_model(data, DCPPowerModel, PowerModels.build_opf)
jump_model = pm.model            # access the JuMP model
flow_var = PowerModels.var(pm, :p)[(br_idx, f_bus, t_bus)]
gate_con = @constraint(jump_model, flow_var <= gate_limit)
result = PowerModels.optimize_model!(pm; optimizer=optimizer)
dual_val = JuMP.dual(gate_con)   # dual extraction works

```

This pattern was confirmed working in test B-1 (`test_b1_custom_constraints.jl`): a flow gate constraint was added post-instantiation and its dual correctly reflected binding status.

Accessor functions on the `pm` object (all defined in `base.jl`, forwarding to `_IM`):
- `var(pm, key)` / `var(pm, nw, key)` — variable dictionary access
- `con(pm, key)` — constraint dictionary access
- `ref(pm, key)` — reference data access
- `sol(pm, key)` — solution data access
- `ids(pm, key)` — component ID iterator
- `nw_ids(pm)` — network IDs (for multi-network models)

### Build Function Architecture

A `build_*` function receives a typed `pm::AbstractPowerModel` argument and calls the compositional variable/constraint API. The canonical example from `src/prob/opf.jl`:

```julia

function build_opf(pm::AbstractPowerModel)
    variable_bus_voltage(pm)
    variable_gen_power(pm)
    variable_branch_power(pm)
    ...
    for i in ids(pm, :ref_buses)
        constraint_theta_ref(pm, i)
    end
    for i in ids(pm, :bus)
        constraint_power_balance(pm, i)
    end
    for i in ids(pm, :branch)
        constraint_ohms_yt_from(pm, i)
        ...
    end
end

```

A custom `build_*` function can call any subset of these, reorder them, or add custom JuMP constraints inline. There is no required superclass method or decorator.

### Constraint Template Pattern

Templates in `src/core/constraint_template.jl` are the indirection layer between data and math. A template:
1. Accepts `pm::AbstractPowerModel` and component index `i`.
2. Looks up parameters from `ref(pm, :branch, i)` or similar.
3. Calls the formulation-specific implementation passing scalar values.

```julia

function constraint_ohms_yt_from(pm::AbstractPowerModel, i::Int; nw=nw_id_default)
    branch = ref(pm, nw, :branch, i)
    g, b = calc_branch_y(branch)
    # ... extract more params ...
    constraint_ohms_yt_from(pm, nw, i, f_bus, t_bus, g, b, ...)
end

```

The formulation-specific implementation (e.g., for `DCPPowerModel`) is dispatched by type. To add a custom constraint for a new formulation type, only the formulation-specific method needs to be added — the template method is inherited.

### Graph Access

PowerModels has **no native Graphs.jl integration** (confirmed by test B-2 comment and `native_graph_api = false`). The `data` dict exposes topology through:
- `data["bus"]` — dict of bus dicts with voltage/type info
- `data["branch"]` — dict of branch dicts, each with `"f_bus"` and `"t_bus"` integer fields
- `PowerModels.calc_connected_components(data)` — returns array of connected component bus sets
- `PowerModels.connected_components(data)` (alias)
- `ref[:arcs]`, `ref[:bus_arcs]` — preprocessed arc tuples `(branch_id, from_bus, to_bus)`

For graph algorithms (BFS, shortest path, etc.), the adjacency structure must be built manually from branch endpoint data (~15 lines of Julia). The test B-2 implementation demonstrates this is straightforward.

**PowerModelsAnalytics.jl** (separate package, not installed) wraps network data into a graph structure and provides `build_network_graph` and `plot_network` via Vega.jl. It does not appear to expose a Graphs.jl-compatible interface based on available documentation. Source: <https://lanl-ansi.github.io/PowerModelsAnalytics.jl/stable/>

### DataFrame / CSV Interoperability

Results are returned as nested Julia `Dict{String,Any}` (test B-5). Converting to DataFrames requires only the standard `DataFrame(; col=[...])` constructor syntax — no custom serialization, no special adapters. Export pattern from `test_b5_interoperability.jl`:

```julia

bus_df = DataFrame(;
    bus_id=[parse(Int, id) for id in keys(sol["bus"])],
    va_rad=[bus["va"] for bus in values(sol["bus"])],
)
CSV.write(path, bus_df)

```

Assessment: "3–4 lines each (DataFrame constructor + sort + CSV.write). Custom serialization needed: false."

### Multi-Network / Stochastic Wrapping

`PowerModels.replicate(data, T)` deep-copies a single-network dict into a multi-network structure with `T` time periods accessible at `mn_data["nw"]["1"]` through `mn_data["nw"][string(T)]`. Each period's data can be mutated independently before calling `solve_mn_opf`. This is the documented approach for multi-period and stochastic problems (test B-4). No native stochastic decomposition (Benders, L-shaped) is provided.

### PTDF Matrix API

`PowerModels.calc_basic_ptdf_matrix(basic_data)` returns a dense `Float64` matrix of shape `(branches, buses)`. Prerequisite: `basic_data = PowerModels.make_basic_network(data)` which renumbers buses to contiguous 1:N. A row-level accessor `calc_basic_ptdf_row(data, l)` is also provided for memory-efficient single-row access. Confirmed working in test B-9 with max flow prediction error < 1e-6.

### Reference Bus Configuration

Single-slack reference bus change is trivial via data dict mutation (`bus_type` field: 3 = slack, 2 = PV). No model reconstruction. Distributed slack is not natively supported and requires ~150 lines of manual PTDF-based OPF via JuMP (test B-8).

### Ecosystem Extension Packages

Built on `InfrastructureModels.jl` (`AbstractPowerModel <: _IM.AbstractInfrastructureModel`). Known extension packages following the same pattern:

| Package | Scope |
|---|---|
| PowerModelsDistribution.jl | Unbalanced distribution networks |
| PowerModelsSecurityConstrained.jl | N-1 security constrained OPF |
| PowerModelsAnalytics.jl | Visualization (Vega-based) |
| PowerModelsAnnex.jl | Exploratory/experimental formulations |
| PowerModelsONM.jl | Outage management (depends on PMD) |
| GasPowerModels.jl | Gas+power co-optimization |
| PowerWaterModels.jl | Power+water co-optimization |

All extension packages create new `AbstractPowerModel` subtypes and use the same `instantiate_model` / `build_*` / `ref_extensions` API.

## Sources

1. `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/base.jl` — AbstractPowerModel definition, instantiate_model, var/con/ref/sol accessors, ref_add_core! implementation
2. `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/types.jl` — Abstract type hierarchy (AbstractActivePowerModel, AbstractBFModel, AbstractConicModel, etc.)
3. `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/constraint_template.jl` — Constraint template pattern with AbstractPowerModel dispatch
4. `/opt/julia-depot/packages/PowerModels/VCmhH/src/prob/opf.jl` — build_opf canonical build function structure
5. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b1_custom_constraints.jl` — Two-level API usage, custom constraint addition, dual extraction (v0.21.5)
6. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b2_graph_access.jl` — Graph access pattern, confirmation of no native Graphs.jl API
7. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b3_contingency_loop.jl` — deepcopy + data mutation for N-1 loop
8. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b4_stochastic_wrapping.jl` — replicate() + multi-period OPF
9. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b5_interoperability.jl` — DataFrame/CSV export pattern
10. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b7_ac_feasibility_extension.jl` — Mutable data dict workflow, no model reconstruction needed
11. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b8_reference_bus_config.jl` — Reference bus config via bus_type mutation; distributed slack workaround
12. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b9_ptdf_extraction.jl` — calc_basic_ptdf_matrix, make_basic_network, calc_basic_ptdf_row APIs
13. <https://lanl-ansi.github.io/PowerModels.jl/stable/> — Official documentation (v0.21, August 2025)
14. <https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/> — Type hierarchy, formulation listing
15. <https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/> — Two-level API (instantiate_model, optimize_model!, pm.model)
16. <https://lanl-ansi.github.io/PowerModels.jl/stable/specifications/> — Problem specification listing (build_opf, build_pf, build_tnep, etc.)
17. <https://lanl-ansi.github.io/PowerModels.jl/stable/constraints/> — Constraint template pattern documentation
18. <https://lanl-ansi.github.io/PowerModels.jl/stable/variables/> — Variable definition pattern
19. <https://lanl-ansi.github.io/PowerModels.jl/stable/multi-networks/> — replicate(), multi-network structure
20. <https://github.com/lanl-ansi/PowerModels.jl> — Repository (v0.21.5, 80 releases, 457 stars)
21. <https://github.com/lanl-ansi/InfrastructureModels.jl> — Base abstraction layer
22. <https://github.com/lanl-ansi/PowerModelsAnalytics.jl> — Visualization extension
23. <https://github.com/lanl-ansi/PowerModelsAnnex.jl> — Experimental extension
24. <https://lanl-ansi.github.io/PowerModelsAnalytics.jl/stable/quickguide/> — Analytics quickstart (visualization focus, limited graph API docs)
25. <https://arxiv.org/abs/1711.01728> — PowerModels.jl paper (Coffrin et al., 2018)

## Gaps and Uncertainties

- **Graphs.jl bridge status**: PowerModelsAnalytics.jl documentation focuses on visualization (Vega/plot_network). Whether it exposes a Graphs.jl-compatible type is not confirmed from available docs. This needs a direct source code check of `PowerModelsAnalytics.jl` if graph-algorithm interop matters.
- **`solution_processors` parameter**: `solve_model` accepts `solution_processors=[]` (an array of post-solve functions). The full API for writing custom solution processors was not explored. This could be relevant for automated result transformation.
- **`relax_integrality` parameter**: `optimize_model!` accepts `relax_integrality=true` to solve MIP relaxations. Interaction with custom constraints added post-instantiation was not tested.
- **`@pm_fields` downstream behavior**: Whether `@pm_fields` correctly captures all required fields when used in a downstream package that `import`s (vs `using`) PowerModels is noted in the source code comments as a known scope concern. Not verified empirically.
- **PowerModelsSecurityConstrained.jl activity**: The changelog URL was found but the package's current maintenance status and compatibility with v0.21 was not verified.
- **DataFrames round-trip fidelity**: The B-5 test verifies row counts but not numerical precision of the CSV round-trip. For production use, floating-point serialization precision should be checked.
- **Distributed slack natively**: Whether any recent version or extension package added native distributed slack support was not confirmed. The B-8 test documents it as absent in v0.21.5 but this may exist in PowerModelsAnnex.

---

## Limitations & Ecosystem

## powermodels — Research: Limitations & Ecosystem

## Key Findings

- PowerModels.jl is a single-developer-dominated project: @ccoffrin has 831 of 1,014 commits (82%), with no other contributor above 45 commits. This creates a significant bus-factor risk.
- As of March 2026, the repo has 457 stars, 167 forks, and 87 open issues — modest for a tool positioned as a research framework for power system optimization.
- The package is **research-oriented, single-period OPF only** by design: no unit commitment, no SCUC, no contingency analysis, no multi-period dispatch beyond the manual multi-network replication API.
- Multi-period support exists only through manual `replicate()` + patch-per-timestep workflow; there is no built-in rolling horizon, look-ahead OPF, or BESS cycling dispatch problem.
- The `solve_pf()` function does **not** work with `LPACCPowerModel` (open issue #891, filed Oct 2023, still unresolved as of March 2026).
- The `DCPLL` formulation silently falls back to DCP when used with power flow problems instead of raising an error (open issue #873, filed Aug 2023, unresolved).
- Generators in PQ-type buses are not allowed in power flow (`@assert false` in code), a limitation with no workaround documented (open issue #989, filed Nov 2025).
- PSS/E (PTI) parser has at least 8 open issues dating back to 2020, covering v34 format support, incorrect active-generator bus handling, VSC data, and tolerance for malformed fields. PSS/E support should be considered fragile.
- The ecosystem of extension packages (security-constrained, restoration, distribution, etc.) provides broader coverage but each is a separate package with its own maintenance state; PowerModelsSecurityConstrained.jl explicitly does not support `storage`, `dcline`, or `switch` components.
- Recent commit activity (late 2025 – early 2026) is dominated by dependency bumps and CI updates, not new features — the core package appears to be in maintenance mode.

## Detailed Notes

### Problem Scope and Missing Capabilities

PowerModels is explicitly scoped to **steady-state single-period OPF and power flow** variants. The math-model documentation confirms unit commitment and multi-period problems are out of scope for the core package.

Supported problem types in core PowerModels v0.21:
- AC OPF (polar: ACPPowerModel, rectangular: ACRPowerModel, IVRPowerModel)
- DC OPF (DCPPowerModel, DCMPPowerModel, BFAPowerModel, NFAPowerModel)
- Quadratic approximations (LPACCPowerModel, DCPLLPowerModel)
- SOC/SDP relaxations (SOCWRPowerModel, SOCBFPowerModel, SDPWRMPowerModel, SparseSDPWRMPowerModel, QCRMPowerModel, QCLSPowerModel)
- Transmission network expansion planning (TNEP)
- Optimal transmission switching (OTS)
- Power flow (PF) — but with known gaps (see bugs below)
- Multi-network co-optimization via `solve_mn_opf` (manual setup required)

Not present in core:
- Security-constrained unit commitment (SCUC) — requires PowerModelsSecurityConstrained.jl
- Unit commitment / generation scheduling
- Multi-period economic dispatch
- Contingency analysis (N-1, N-k)
- BESS arbitrage or cycling dispatch as a built-in problem type
- Rolling horizon OPF
- Probabilistic / stochastic OPF (separate StochasticPowerModels.jl)

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/> and <https://lanl-ansi.github.io/PowerModels.jl/stable/math-model/>

### Known Bugs and Open Issues (Evaluation-Relevant)

**Issue #989** — Generators in PQ buses not allowed (filed Nov 2025, unresolved)
`solve_pf()` hits `@assert false` when any generator is on a PQ bus. Affects real-world networks where load buses have distributed generation.
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/989>

**Issue #891** — `solve_pf()` does not work with `LPACCPowerModel` (filed Oct 2023, unresolved)
Raises `MethodError: no method matching expression_branch_power_ohms_yt_from(::LPACCPowerModel, ...)`. A full traceback is in the issue; the formulation is partially implemented for OPF but the PF dispatch is missing.
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/891>

**Issue #873** — DCPLL silently falls back to DCP for power flow (filed Aug 2023, unresolved)
No error is raised; users may not realize they are running a different formulation.
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/873>

**Issue #932** — Incorrect behavior for PSSE active generators at load buses (filed Oct 2024, related fix PR #934 still open)
Generator bus voltage set incorrectly when generator is on a load-type bus in PTI files.
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/932>

**Issue #921** — No support for PSS/E RAW format version 34 (filed Jul 2024, unresolved)
Only PSS/E v33 is officially supported. Many utilities use v33 or v34.
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/921>

**Issue #890** — Problems with non-Float64 types (filed Sep 2023, unresolved)
Cannot use alternative numeric types (ForwardDiff, Dual numbers for sensitivity analysis).
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/890>

**Issue #770** — Parallel power flow computations not supported (filed Mar 2021, unresolved)
Multi-threading is not implemented for batch power flow jobs.
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/770>

**Issue #703** — Switch support for power flow problems (filed Apr 2020, unresolved)
Switches are modeled for OPF but not for PF problem specifications.
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/703>

### PSS/E Parser Fragility

At least 8 open issues target the PTI/PSS/E parser (label: "File format: PSSE/PTI"):
- #932, #921, #918, #897, #893, #888, #856, #843, #842, #794, #749, #737

Issues range from blank field handling to VSC data, transformer angle offsets >60°, and v34 format support. The parser is described as following PSS/E v33 specification; deviations in real-world files frequently cause parse failures or silent data errors.

### Multi-Period and Storage Limitations

Multi-period OPF is possible via `PowerModels.replicate(data, n)` which clones the single network n times into a multi-network dict; the caller must manually set per-period parameters (load profiles, etc.) before calling `solve_mn_opf`. There is no built-in time-series loading, rolling horizon, or period-linking constraint set for BESS state-of-charge across an arbitrary horizon.

The storage model documents a complementarity constraint `sc_t * sd_t = 0` (no simultaneous charge/discharge), which is a continuous relaxation — the constraint can be violated by interior-point solvers, requiring either a binary variable or a penalty term for strict enforcement. The documentation acknowledges this: "the standard storage model does not use binary variables to prevent simultaneous charging and discharging."
Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/storage/>

### Ecosystem and Dependency Tree

#### Core dependencies (from Project.toml, v0.21):
- JuMP v1 — modeling layer
- Ipopt v1 — nonlinear solver (NLP)
- GLPK v1 — LP/MIP solver
- HiGHS v1 — LP/MIP solver
- SCIP v0.11 — MIP solver
- InfrastructureModels — shared LANL data model library (implicit transitive dep)

All solvers are open-source. For large-scale problems, commercial solvers (Gurobi, CPLEX, MOSEK for SDP) are typically required but are not bundled.

#### First-party extension packages (all LANL-hosted):

| Package | Stars | Description | Last release |
|---|---|---|---|
| PowerModelsDistribution.jl | 156 | Unbalanced distribution networks | Active |
| PowerModelsSecurityConstrained.jl | 41 | SCUC; excludes storage/dcline/switch | v0.12.0 Jan 2024 |
| PowerModelsADA.jl | 37 | Distributed OPF algorithms | Active |
| PowerModelsRestoration.jl | 27 | N-k restoration / MLD | v0.9.0 Jan 2024 |
| PowerModelsAnnex.jl | 25 | Exploratory extensions | Active |
| PowerModelsONM.jl | 20 | Distribution feeder restoration | Active |
| PowerModelsITD.jl | 15 | Integrated T&D optimization | Active |
| PowerModelsGMD.jl | 12 | Geomagnetic disturbance | Active |
| PowerModelsProtection.jl | 10 | Fault study formulations | Active |
| PowerModelsStability.jl | 3 | Stability-constrained PF | Active |

#### Third-party notable:
- PandaModels.jl (13 stars) — bridge from pandapower networks to PowerModels
- StochasticPowerModels.jl (24 stars) — stochastic OPF extension
- PowerModelsDistributionStateEstimation.jl (39 stars) — state estimation for distribution

Source: GitHub API search, March 2026

### Community Size and Activity

- **Stars**: 457 (modest for a 10-year-old research framework)
- **Forks**: 167
- **Open issues**: 87 (several dating back to 2016–2018 with no resolution)
- **Total commits**: 1,014 on master
- **Contributors**: 27 named; @ccoffrin accounts for 831 commits (82%)
- **Second-most active**: @pseudocubic (45), @jd-lara (34), @odow (22)
- **Institutional backing**: Los Alamos National Laboratory (LANL); funded partly through DOE Grid Optimization Competition
- **Discourse**: No dedicated forum; users post on Julia Discourse and GitHub issues

The high concentration of commits in one person represents meaningful key-person risk. The project's pace has slowed noticeably: recent commits (Dec 2025 – Mar 2026) are CI dependency bumps only.

Source: GitHub API, <https://github.com/lanl-ansi/PowerModels.jl>

### Release History and Changelog Quality

| Release | Date | Notes |
|---|---|---|
| v0.21.5 | 2025-08-12 | Relax test conditions, silence logger during precompile |
| v0.21.4 | 2025-05-20 | Numerical fixes in PF, syntax fix in export |
| v0.21.3 | 2024-11-04 | Bug fixes |
| v0.21.2 | 2024-07-05 | Bug fixes |
| v0.21.1 | 2024-03-16 | Bug fixes |
| v0.21.0 | 2024-01-19 | Breaking: new JuMP nonlinear interface |
| v0.20.1 | 2024-01-10 | Bug fixes |
| v0.20.0 | 2024-01-02 | Breaking: two-sided constraints, cost function rewrite, dropped multi-conductor |
| v0.19.10 | 2024-01-01 | Maintenance |
| v0.19.9 | 2023-05-28 | Maintenance |

**Changelog quality**: The CHANGELOG.md exists and is structured, but entries at the patch level are sparse (e.g., "relax test conditions"). Major breaking changes in v0.20 and v0.21 are documented. No pre-release (alpha/beta/RC) process is used.

There have been 80 total releases since 2016. Release cadence is irregular: 5 releases in 2024, 2 in 2025.

Source: GitHub API releases endpoint, CHANGELOG.md

### Documentation Quality

The official docs at <https://lanl-ansi.github.io/PowerModels.jl/stable/> are generated by Documenter.jl and include:
- Manual: network data formats, result structures, math model, storage, switches, multi-network, utilities
- Library: API reference for formulations, problem specs, variables, constraints
- Developer: naming conventions only (not a full extension guide)
- Experiment results: benchmark tables for OPF across PGLib-OPF cases

#### Gaps and weaknesses:
- No troubleshooting guide
- No real-world deployment examples or case studies
- Developer documentation is a style guide, not an architecture guide — adding new formulations requires reading source code
- `solve_pf()` API is not well-documented relative to `solve_opf()`
- Multi-network workflow lacks worked examples showing BESS multi-period dispatch
- Docs do not surface known bugs (issue #891, #873) as warnings

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/>

### Deployment Evidence

PowerModels is primarily used in academic and national-laboratory research. Evidence of production utility/ISO deployment is sparse:
- DOE Grid Optimization (GO) Competition used PowerModels-based solvers (PowerModelsSecurityConstrained.jl was specifically developed for the competition)
- LANL internal use implied by commit history
- No public evidence of use by commercial ISO/RTO operators or energy trading firms

### License

BSD 3-Clause ("Other" per GitHub API, but text confirms BSD). Permissive for commercial and research use. All first-party extension packages share the same license.

Source: <https://github.com/lanl-ansi/PowerModels.jl>

## Sources

1. <https://github.com/lanl-ansi/PowerModels.jl> — Main repository
2. <https://lanl-ansi.github.io/PowerModels.jl/stable/> — Official documentation
3. <https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/> — Formulation list
4. <https://lanl-ansi.github.io/PowerModels.jl/stable/math-model/> — Mathematical model scope
5. <https://lanl-ansi.github.io/PowerModels.jl/stable/storage/> — Storage model and limitations
6. <https://lanl-ansi.github.io/PowerModels.jl/stable/multi-networks/> — Multi-network API
7. <https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/> — Supported data formats
8. <https://lanl-ansi.github.io/PowerModels.jl/stable/experiment-results/> — Benchmark tables
9. <https://github.com/lanl-ansi/PowerModels.jl/issues/989> — Generators in PQ buses bug
10. <https://github.com/lanl-ansi/PowerModels.jl/issues/891> — solve_pf LPACCPowerModel bug
11. <https://github.com/lanl-ansi/PowerModels.jl/issues/873> — DCPLL silent fallback
12. <https://github.com/lanl-ansi/PowerModels.jl/issues/932> — PSSE generator at load bus
13. <https://github.com/lanl-ansi/PowerModels.jl/issues/921> — PSS/E v34 support missing
14. <https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl> — SCUC extension
15. <https://github.com/lanl-ansi/PowerModelsRestoration.jl> — Restoration extension
16. GitHub API: repos/lanl-ansi/PowerModels.jl (stars, forks, releases, contributors)
17. /home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/Project.toml — local version pin (v0.21)

## Gaps and Uncertainties

- **Solver compatibility matrix**: It is unclear which formulations (especially SDP variants) require commercial solvers to solve problems of useful size. The benchmark results use HSL ma57 (restricted license, not open-source), not the open-source solvers bundled in Project.toml.
- **Actual multi-period BESS dispatch**: It is unverified whether the `solve_mn_opf` path correctly enforces BESS state-of-charge continuity across timesteps when replicated networks are used, or whether that coupling must be added manually by the user.
- **Simultaneous charge/discharge in practice**: Whether the continuous complementarity constraint `sc_t * sd_t = 0` is enforced tightly enough by Ipopt/HiGHS in practice (vs. requiring explicit binary variables) needs empirical testing.
- **PSS/E v33 vs. v34 gap impact**: The actual severity of PSS/E parsing failures on industry-standard case files (beyond the test cases) is unknown without testing against real utility data.
- **PowerModelsSecurityConstrained.jl maintenance**: v0.12.0 was released Jan 2024 and the last commit was Oct 2025; unclear if it tracks v0.21 of the core package without issues.
- **Performance on large networks (>10k buses)**: Benchmark data covers up to 13,659 buses with QC formulations taking 23–262 seconds (excluding JIT). Behavior at 30k+ buses is not documented.
- **Windows/cross-platform reliability**: Issue #830 (Pluto.jl stream error) and issue #842 (PSSE parser blank field) suggest some platform-specific behavior that was not reproduced on Linux in the benchmarks.

---

## Version Capabilities

```yaml
tool: powermodels
installed_version: 0.21.5
release_date: 2025-08-12
latest_version: 0.21.5
latest_release_date: 2025-08-12
research_date: 2026-03-11
```

## powermodels — Version & Capability Report

## Version Summary

The installed version is PowerModels.jl 0.21.5, which is also the current latest stable release (published 2025-08-12). The evaluation environment is fully up to date — there is no version gap to account for.

The 0.21.x series has been stable since January 2024 (v0.21.0), with the major change being an update to JuMP's new nonlinear interface. Patch releases since then have been limited to bug fixes (PSS/E parser corrections, `compute_ac_pf` InexactError, switch resolution logic), performance improvements to basic data utilities (`calc_basic_incidence_matrix`, `calc_connected_components`), and developer tooling (PrecompileTools integration, CI updates). No new features or capability additions were made in the 0.21.x series beyond what was present in 0.21.0.

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes | 0.13.2 | `solve_dc_pf(data, Optimizer)` via LP/JuMP — formulated as optimization problem, not direct matrix solve. Also `compute_basic_dc_pf` for matrix-based solve without solver overhead. |
| AC Power Flow (ACPF) | yes | 0.16.0 | `solve_ac_pf(data, Optimizer)` for optimizer-based; `compute_ac_pf(data)` for native NLSolve-based iterative solver (added v0.16.0). |
| DC Optimal Power Flow (DC OPF) | yes | early | `solve_opf(data, DCPPowerModel, Optimizer)`. DCPPowerModel is the standard linear DC approximation. |
| AC Optimal Power Flow (AC OPF) | yes | early | `solve_opf(data, ACPPowerModel, Optimizer)`. Multiple AC formulations: ACPPowerModel (polar), ACRPowerModel (rectangular), ACTPowerModel (w-space). |
| Security-Constrained Unit Commitment (SCUC) | no | — | Not provided. PowerModels is a steady-state network optimization library. Unit commitment (integer scheduling) is out of scope. |
| Security-Constrained Economic Dispatch (SCED) | no | — | Not provided as a built-in problem type. Contingency analysis utilities exist but no full SCED formulation. |
| PTDF / Shift Factor Extraction | yes | 0.13.2 | `calc_basic_ptdf_matrix(data)` returns a dense Float64 matrix (branches × buses). `calc_basic_ptdf_row(data, branch_idx)` extracts a single row. Also `calc_basic_susceptance_matrix` and `calc_basic_branch_susceptance_matrix`. See: basic-data-utilities docs. |
| Contingency Analysis (N-1) | partial | 0.13.2 | No dedicated N-1 contingency solver. `calc_connected_components` and iterative flow-limit cut solvers (`solve_opf_ptdf_branch_power_cuts`, `solve_opf_branch_power_cuts`) support contingency-aware OPF workflows but require user-side loop construction for full N-1 analysis. |
| Custom Constraint Injection | yes | 0.14.0 | `instantiate_model(data, FormType, build_fn)` allows passing a custom `build_fn` that adds constraints to the JuMP model via full JuMP constraint API. Documented in formulations/model sections. |
| Network Graph Access | yes | early | `parse_file` returns a nested Julia dictionary. `calc_basic_incidence_matrix(data)` returns a sparse integer incidence matrix. `calc_basic_admittance_matrix(data)` returns sparse complex admittance matrix. Direct dictionary traversal of `data["bus"]`, `data["branch"]`, etc. |
| CSV Data Import | no | — | Not supported. Accepted formats are MATPOWER `.m`, PSS/E PTI `.raw` (v33 spec), and JSON. No CSV reader. |
| MATPOWER Case Import | yes | early | `PowerModels.parse_file("case.m")`. Extensive support documented. Tested on case39.m in this evaluation. |
| Multi-Period / Time Series | yes | 0.14.1 | `replicate(data, n)` creates an n-timestep multi-network. `solve_mn_opf` solves coupled multi-network OPF. Storage state-of-charge linking across periods supported. `parse_files` (v0.17.4) creates multinetwork from multiple source files. |
| Warm Start / Solution Reuse | partial | unknown | JuMP supports `set_start_value` for variables, but PowerModels does not expose a documented high-level warm-start API. Users must access the underlying JuMP model via `pm.model` and set start values manually. Not documented as a first-class feature. |
| Parallel Computation | partial | unknown | Julia's built-in `Distributed` and `Threads` can be applied externally. PowerModels itself has no built-in parallel solve API. Solvers like HiGHS support internal parallelism via solver options. `solve_opf_ptdf_branch_power_cuts` is iterative but sequential. |

### Canonical Feature–Suite Mapping

| Feature | Suites |
|---------|--------|
| DC Power Flow (DCPF) | A, G |
| AC Power Flow (ACPF) | A, G |
| DC Optimal Power Flow (DC OPF) | A |
| AC Optimal Power Flow (AC OPF) | A |
| Security-Constrained Unit Commitment (SCUC) | A |
| Security-Constrained Economic Dispatch (SCED) | A |
| PTDF / Shift Factor Extraction | B |
| Contingency Analysis (N-1) | B |
| Custom Constraint Injection | C |
| Network Graph Access | C |
| CSV Data Import | G |
| MATPOWER Case Import | A, G |
| Multi-Period / Time Series | B |
| Warm Start / Solution Reuse | D |
| Parallel Computation | D |

### Support Semantics

- **yes** — Feature is fully supported in the installed version.
- **no** — Feature is not available.
- **partial** — Feature exists but with significant limitations (explained in Notes).
- **Since Version** — The version that introduced the feature. Set to `unknown` if the changelog does not provide this information.

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|----------------------|
| 0.21.0 | Update to JuMP's new nonlinear interface (breaking) | AC OPF and nonlinear formulations use new `@constraint`/`@NLconstraint` patterns from JuMP 1.x. Any test code written for pre-0.21 nonlinear syntax must use new API. |
| 0.20.0 | Drop `run_*` functions — replaced by `solve_*` | All solver calls must use `solve_dc_pf`, `solve_opf`, etc. Old `run_*` names no longer exist even with deprecation (dropped in 0.20.0 after deprecation in 0.19.2). |
| 0.20.0 | Revised models to use two-sided constraints | OPF constraint formulation internals changed; affects custom constraint injection that wraps standard constraints. |
| 0.20.0 | Drop support for multiple conductors | Multi-conductor models (previously used for three-phase distribution) are no longer supported; now in PowerModelsDistribution.jl. |
| 0.20.0 | Rewrite objective function building | Custom objective function code must use new objective API. |
| 0.18.0 | Renamed `*_flow_cuts` to `*_branch_power_cuts` | PTDF-based OPF cutting plane solver has new function name: `solve_opf_ptdf_branch_power_cuts`. |
| 0.18.0 | `update_data!` result dict format changed (native PF now outputs results dict) | `compute_ac_pf` and `compute_dc_pf` now return standard results dictionaries, not in-place mutations. |
| 0.17.0 | Updated function naming convention throughout | Many internal and public functions renamed; see issue #701. |
| 0.16.0 | `instantiate_model` moved to InfrastructureModels | Function still available but sourced from InfrastructureModels.jl dependency. |
| 0.14.0 | `post_*` functions renamed to `build_*` | Problem builder functions are `build_opf`, `build_pf`, etc. |

## Changelog Analysis

The changelog from v0.13.2 (when PTDF and basic data utilities were added) to v0.21.5 (installed) shows the following themes relevant to the 15 canonical features:

### PTDF and Linear Algebra Utilities (B Suite)
Added in v0.13.2: native DC power flow solver, AdmittanceMatrix data structures, PTDF-based OPF problem specification, and iterative flow limit cut solvers. v0.13.1 added `DCMPPowerModel` replicating MATPOWER's DC model exactly. v0.18.3 added Jacobian matrix calculation. v0.19.8 improved PTDF matrix computation performance. v0.21.4 improved `calc_basic_incidence_matrix` performance.

#### AC Power Flow (A Suite)
Native AC power flow iterative solver added in v0.16.0 using NLSolve. Prior to this only optimizer-based ACPF was supported. v0.18.3 fixed bugs in `compute_ac_pf` slack bus reporting. v0.21.4 fixed `InexactError` in `compute_ac_pf`.

#### Multi-Network / Time Series (B Suite)
Multi-network framework has been present since at least v0.13.0. v0.14.1 improved OLTC/PST variable support. v0.17.4 added `parse_files` for multi-source multinetwork creation. v0.18.1 fixed multinetwork support in sparse SDP models.

#### Custom Constraints / Extensibility (C Suite)
The `instantiate_model` pattern for custom problem builders has been stable since v0.14.0 (renamed from `InitializePowerModel` in v0.16.0, then delegated to InfrastructureModels). v0.21.0 changed the nonlinear constraint interface via JuMP's new NL API — this is the most significant change affecting custom constraint injection in the evaluation period.

#### Data Import (G Suite)
MATPOWER `.m` parsing has been present from the start. PSS/E `.raw` parsing for v33 spec added historically. v0.21.4 fixed `parse_file` to correctly use `JSON.parsefile` for JSON input. No CSV support added in any version.

#### Warm Start / Parallel (D Suite)
No dedicated warm-start or parallel computation features added in any 0.21.x release. No changelog entries reference these features across the entire history reviewed.

## Sources

1. `evaluations/powermodels/Manifest.toml` — pinned dependency versions including PowerModels 0.21.5
2. `evaluations/powermodels/Project.toml` — declared dependencies and compat bounds
3. `evaluations/powermodels/notes/install-findings.md` — smoke test findings from 2026-03-03
4. GitHub API: `https://api.github.com/repos/lanl-ansi/PowerModels.jl/releases` — release dates confirmed
5. GitHub raw: `https://raw.githubusercontent.com/lanl-ansi/PowerModels.jl/master/CHANGELOG.md` — full changelog text
6. `https://lanl-ansi.github.io/PowerModels.jl/stable/specifications/` — problem specification docs
7. `https://lanl-ansi.github.io/PowerModels.jl/stable/basic-data-utilities/` — PTDF, admittance, incidence matrix functions
8. `https://lanl-ansi.github.io/PowerModels.jl/stable/multi-networks/` — multi-network (time series) API
9. `https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/` — supported data formats
10. `https://lanl-ansi.github.io/PowerModels.jl/stable/utilities/` — utility solver functions
11. GitHub API: `https://api.github.com/repos/lanl-ansi/PowerModels.jl/contents/src/prob` — source file listing confirming problem types

## Gaps and Uncertainties

- **Warm start**: The JuMP model is accessible via `pm.model` and JuMP's `set_start_value` works, but there is no documented high-level PowerModels warm-start workflow. Whether the evaluation protocol's warm-start tests can be satisfied via raw JuMP access needs runtime verification.
- **Parallel computation**: Solver-level parallelism (HiGHS threads) is available via `set_optimizer_attribute`, but PowerModels-level parallelism is undocumented. The degree to which this satisfies Suite D tests is unclear.
- **Contingency Analysis (N-1)**: The iterative cut-based solvers (`solve_opf_ptdf_branch_power_cuts`) are related but are OPF-with-violations tools, not classical N-1 contingency screening. Whether the evaluation protocol's contingency tests require classical screening or constraint-based approaches needs clarification from the test specification.
- **SCUC/SCED**: These are definitively absent from PowerModels.jl — they are not mentioned anywhere in the documentation or source tree. If Suite A tests require SCUC/SCED, they will fail.
- **CSV import**: Definitively not supported. Any Suite G test requiring CSV input will need a user-written parser or conversion step.
- **`calc_basic_ptdf_matrix` performance on large cases**: The changelog notes a performance improvement in v0.19.8, but no benchmarks are documented. Performance on large networks (e.g., case2848) is unknown without testing.
- **PSS/E v34+ format support**: Only PSS/E v33 spec is documented. Newer PSS/E format versions are not confirmed supported.

# powermodels — Research: API & Formulations

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

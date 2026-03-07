# PowerModels.jl -- Research: API & Formulations

**Version evaluated:** 0.21.5 (installed via Project.toml compat `"0.21"`, Julia 1.10)
**Repository:** <https://github.com/lanl-ansi/PowerModels.jl>
**Documentation:** <https://lanl-ansi.github.io/PowerModels.jl/stable/>
**License:** BSD (Multi-Infrastructure Control and Optimization Toolkit, C15024, Los Alamos National Laboratory)

## Key Findings

- PowerModels.jl exports **437 symbols** and provides a highly modular architecture that cleanly decouples **problem specifications**(PF, OPF, OTS, TNEP) from **network formulations**(AC polar/rectangular, DC, SOC, SDP, QC, LPAC, branch-flow, current-voltage, etc.) -- any problem can be paired with any compatible formulation.
- **18+ network formulation types** are provided, ranging from exact nonlinear (ACPPowerModel, ACRPowerModel) through linear approximations (DCPPowerModel, DCMPPowerModel, NFAPowerModel) to convex relaxations (SOCWRPowerModel, SDPWRMPowerModel, QCRMPowerModel).
- The data model is a **nested `Dict{String, Any}`** based on MATPOWER conventions but with important differences: loads and shunts are separated from buses, all values are per-unit, angles are in radians, and every component gets a unique integer `"index"`.
- Input formats: **MATPOWER `.m`** and **PSS/E `.raw` (v33)** files via `parse_file()`. Output: JSON-serializable result dicts. Also supports `export_matpower()` and `export_pti()`.
- Solver interface uses **JuMP**, so any JuMP-compatible solver works: Ipopt (NLP), HiGHS/GLPK (LP/MIP), Gurobi (LP/MIP/QP), SCIP (MINLP), SCS/Mosek (conic/SDP). Solvers are passed as optimizer factories.
- **PTDF matrix** computation is built-in via `calc_basic_ptdf_matrix()` and there is a dedicated PTDF-based OPF formulation (`solve_opf_ptdf`).
- **LMP/dual values** are accessible for DC-OPF via `result["solution"]["bus"]["lam_kcl_r"]` with the setting `Dict("output" => Dict("duals" => true))`. AC-OPF dual support is limited.
- **No built-in SCUC or unit commitment.** PowerModels focuses on steady-state OPF. Unit commitment is handled by the separate package `UnitCommitment.jl`. SCOPF is in the separate `PowerModelsSecurityConstrained.jl`.
- **Multi-period/multi-network** support exists via `replicate()` and `solve_mn_opf()` / `solve_mn_opf_strg()`, enabling time-coupled storage optimization with `time_elapsed` parameter.
- Native (non-JuMP) power flow solvers exist: `compute_ac_pf()` (NLsolve-based) and `compute_dc_pf()` (direct linear solve), avoiding JuMP overhead.

## Detailed Notes

### Problem Specifications (solve functions)

All `solve_*` functions accept `(file_or_data, model_type, optimizer; kwargs...)`. Shorthand variants for AC/DC omit the model_type argument.

| Function | Problem | Notes |
|----------|---------|-------|
| `solve_pf(file, Type, opt)` | Power Flow | Generic, any formulation |
| `solve_ac_pf(file, opt)` | AC Power Flow | Shorthand for ACPPowerModel |
| `solve_dc_pf(file, opt)` | DC Power Flow | Shorthand for DCPPowerModel |
| `solve_opf(file, Type, opt)` | Optimal Power Flow | Generic |
| `solve_ac_opf(file, opt)` | AC OPF | Shorthand |
| `solve_dc_opf(file, opt)` | DC OPF | Shorthand |
| `solve_opf_bf(file, Type, opt)` | OPF Branch Flow | For AbstractBFModel types |
| `solve_opf_iv(file, Type, opt)` | OPF Current-Voltage | For IVRPowerModel |
| `solve_opf_ptdf(file, Type, opt)` | OPF with PTDF | PTDF-based DC formulation |
| `solve_ots(file, Type, opt)` | Optimal Transmission Switching | Binary branch indicators |
| `solve_tnep(file, Type, opt)` | Transmission Network Expansion | Binary new-branch indicators |
| `solve_opb(file, Type, opt)` | Optimal Power Balance | Simplified problem |
| `solve_mn_opf(file, Type, opt)` | Multi-network OPF | Multi-period |
| `solve_mn_opf_strg(file, Type, opt)` | Multi-network OPF + Storage | Time-coupled storage |
| `solve_mn_opf_bf_strg(file, Type, opt)` | MN OPF BF + Storage | Branch-flow variant |
| `solve_obbt_opf!(data, opt)` | Optimality-based bound tightening | Iterative bound refinement |
| `solve_opf_branch_power_cuts(file, Type, opt)` | OPF with lazy flow cuts | Iterative constraint generation |
| `solve_opf_ptdf_branch_power_cuts(file, opt)` | PTDF OPF with lazy cuts | Combines PTDF + cuts |

**Source:** Exported symbols from PowerModels v0.21.5; method signatures from Julia introspection.

#### Native Power Flow (no JuMP)

| Function | Method | Notes |
|----------|--------|-------|
| `compute_ac_pf(file_or_data)` | NLsolve (Newton) | Polar coordinates, needs near-feasible start |
| `compute_ac_pf!(data)` | NLsolve (in-place) | Modifies data dict directly |
| `compute_dc_pf(file_or_data)` | Linear solve (`\` operator) | Direct, no warm start |
| `compute_basic_dc_pf(data)` | Linear solve | Requires basic network |

**Source:** <https://lanl-ansi.github.io/PowerModels.jl/stable/power-flow/>

#### Post-Processing

| Function | Purpose |
|----------|---------|
| `calc_branch_flow_ac(data)` | Compute AC branch flows from voltage solution |
| `calc_branch_flow_dc(data)` | Compute DC branch flows from angle solution |
| `set_ac_pf_start_values!(data)` | Set warm-start values for AC PF |

### Network Formulations (Type Hierarchy)

PowerModels uses Julia's type system to dispatch formulation-specific constraint and variable methods. All concrete types inherit from `AbstractPowerModel`.

**Source:** <https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/>

#### Exact Nonconvex (NLP)

| Type | Description | Coordinates |
|------|-------------|-------------|
| `ACPPowerModel` | Full AC power flow | Polar (V, theta) |
| `ACRPowerModel` | Full AC power flow | Rectangular (Vr, Vi) |
| `ACTPowerModel` | AC with tangent constraints | Mixed (theta, W, WR, WI) |
| `IVRPowerModel` | Current-voltage formulation | Rectangular I and V |

#### Linear Approximations

| Type | Description | Key Assumptions |
|------|-------------|-----------------|
| `DCPPowerModel` | Standard DC approximation | Active power only, `br_b = -br_x/(br_r^2+br_x^2)` |
| `DCMPPowerModel` | MATPOWER-compatible DC | `br_b = -1/br_x`, includes tap/shift |
| `DCPLLPowerModel` | DC with linear losses | Adds loss linearization |
| `NFAPowerModel` | Network flow approximation | Transportation model, no angles |
| `BFAPowerModel` | Linear branch flow | Neglects current magnitude losses |
| `LPACCPowerModel` | LP approximation of AC | "Cold-start" variant, linearized cosine |

#### Convex Relaxations (SOC/QC)

| Type | Description | Math |
|------|-------------|------|
| `SOCWRPowerModel` | SOC relaxation, bus injection | QCQP |
| `SOCWRConicPowerModel` | SOC relaxation, conic form | Conic |
| `SOCBFPowerModel` | SOC relaxation, branch flow | QCQP |
| `SOCBFConicPowerModel` | SOC branch flow, conic | Conic |
| `QCRMPowerModel` | QC relaxation, McCormick | QCQP |
| `QCLSPowerModel` | QC relaxation, strengthened | QCQP + lambda |

#### SDP Relaxations

| Type | Description | Solver Needs |
|------|-------------|-------------|
| `SDPWRMPowerModel` | Full SDP relaxation | SDP solver (SCS, Mosek) |
| `SparseSDPWRMPowerModel` | Sparse SDP relaxation | SDP solver, exploits sparsity |

### Data Model

**Source:** <https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/>

The internal data model is a `Dict{String, Any}` with string keys throughout (for JSON serialization). Top-level keys:

```

"per_unit"       :: Bool      # true if data is in per-unit
"baseMVA"        :: Float64   # system MVA base
"name"           :: String    # network name
"time_elapsed"   :: Float64   # hours, for storage energy calculations
"multinetwork"   :: Bool      # single vs multi-network flag
"bus"            :: Dict{String, Any}   # indexed by string of bus number
"gen"            :: Dict{String, Any}
"branch"         :: Dict{String, Any}
"load"           :: Dict{String, Any}   # separated from bus (unlike MATPOWER)
"shunt"          :: Dict{String, Any}   # separated from bus (unlike MATPOWER)
"storage"        :: Dict{String, Any}
"dcline"         :: Dict{String, Any}
"switch"         :: Dict{String, Any}

```

#### Bus Fields
- `"bus_i"`, `"index"` -- bus number / unique ID
- `"bus_type"` -- 1=PQ, 2=PV, 3=ref, 4=isolated
- `"vm"` -- voltage magnitude (p.u.)
- `"va"` -- voltage angle (radians)
- `"vmin"`, `"vmax"` -- voltage bounds (p.u.)
- `"base_kv"` -- base voltage (kV)

#### Generator Fields
- `"gen_bus"` -- connected bus index
- `"pg"`, `"qg"` -- active/reactive power output
- `"pmin"`, `"pmax"`, `"qmin"`, `"qmax"` -- power bounds
- `"gen_status"` -- 1=active, 0=inactive
- `"cost"`, `"ncost"`, `"model"` -- cost model (polynomial or piecewise linear, merged from gencost)

#### Branch Fields
- `"f_bus"`, `"t_bus"` -- from/to bus indices
- `"br_r"`, `"br_x"` -- series resistance/reactance (p.u.)
- `"br_b"` -- total line charging susceptance (p.u.)
- `"tap"`, `"shift"` -- transformer tap ratio and phase shift (radians)
- `"transformer"` -- boolean, true if transformer
- `"rate_a"`, `"rate_b"`, `"rate_c"` -- thermal ratings (MVA)
- `"br_status"` -- 1=active, 0=inactive
- `"angmin"`, `"angmax"` -- angle difference bounds (radians)

#### Load Fields
- `"load_bus"` -- connected bus index
- `"pd"`, `"qd"` -- active/reactive demand
- `"status"` -- 1=active, 0=inactive

#### Storage Fields
- `"storage_bus"` -- connected bus index
- `"energy"`, `"energy_rating"` -- current energy state, capacity (MWh)
- `"charge_rating"`, `"discharge_rating"` -- power limits (MW)
- `"charge_efficiency"`, `"discharge_efficiency"` -- efficiency scalars (0-1)
- `"r"`, `"x"` -- impedance parameters
- `"p_loss"`, `"q_loss"` -- standing losses
- `"thermal_rating"`, `"current_rating"` -- connection limits

#### Key Differences from MATPOWER

1. Loads and shunts are **separate components**, not embedded in bus data
2. All angles in **radians**(MATPOWER uses degrees)
3. All values in **per-unit**(MATPOWER uses mixed units)
4. Every component has a unique `"index"` field
5. Cost data from `gencost` is **merged into gen** records
6. All branches include `"transformer"` boolean and default tap=1.0, shift=0.0
7. Conversion functions: `make_per_unit!()`, `make_mixed_units!()`

### Input/Output Formats

**Input parsers:**
- `parse_file(path)` -- auto-detects .m (MATPOWER) or .raw (PSS/E v33)
- `parse_matpower(path)` -- explicit MATPOWER parser
- `parse_psse(path)` / `parse_pti(path)` -- explicit PSS/E parser
- `parse_json(path)` -- PowerModels JSON format
- `parse_files(paths...)` -- merge multiple files

**Output:**
- `export_matpower(path, data)` -- write MATPOWER .m file
- `export_pti(path, data)` -- write PSS/E .raw file
- `export_file(path, data)` -- auto-detect format from extension
- Result dicts are JSON-serializable (all string keys)

**Source:** Exported symbols; <https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/>

### Result Structure

All `solve_*` functions return a `Dict{String, Any}`:

```julia

result = solve_ac_opf("case3.m", Ipopt.Optimizer)

result["solve_time"]       # Float64, seconds
result["objective"]        # Float64, objective value
result["termination_status"]  # MOI termination status
result["primal_status"]    # MOI result status
result["dual_status"]      # MOI result status
result["optimizer"]        # solver name string
result["solution"]         # Dict with component solutions

```

Solution components mirror the input data structure:

```julia

result["solution"]["bus"]["1"]["vm"]    # voltage magnitude at bus 1
result["solution"]["bus"]["1"]["va"]    # voltage angle at bus 1
result["solution"]["gen"]["1"]["pg"]    # active power output of gen 1
result["solution"]["branch"]["1"]["pf"] # active power flow (from end)
result["solution"]["branch"]["1"]["pt"] # active power flow (to end)

```

**Branch losses:** `data["pt"] + data["pf"]` for each branch.

**Source:** <https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/>

### Solver Interface

PowerModels uses JuMP's optimizer interface. Any JuMP-compatible solver can be used:

```julia

# Direct optimizer
solve_ac_opf("case3.m", Ipopt.Optimizer)

# Optimizer with attributes
opt = JuMP.optimizer_with_attributes(Ipopt.Optimizer, "print_level" => 0)
solve_ac_opf("case3.m", opt)

```

**Solver compatibility by formulation:**

| Formulation Category | Required Solver Type | Example Solvers |
|---------------------|---------------------|-----------------|
| AC (NLP) | Nonlinear | Ipopt, KNITRO |
| DC (LP) | Linear | HiGHS, GLPK, Gurobi, CPLEX |
| SOC/QC (QCQP) | Quadratic or conic | Gurobi, Mosek, CPLEX |
| SOC Conic | Conic | SCS, Mosek, ECOS |
| SDP | Semidefinite | SCS, Mosek, CSDP |
| OTS/TNEP (MIP) | Mixed-integer | HiGHS, GLPK, Gurobi, SCIP |
| AC + MIP (MINLP) | MINLP | Juniper (Ipopt + HiGHS), SCIP |

The evaluation Project.toml includes: Ipopt, HiGHS, GLPK, SCIP, JuMP.

**Source:** <https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/;> Project.toml

### Two-Level API (Convenience vs. Advanced)

**Level 1 -- Convenience:** `solve_ac_opf(file, optimizer)` handles everything.

**Level 2 -- Advanced:** Decomposed workflow for inspection and customization:

```julia

# 1. Parse data
data = parse_file("case3.m")

# 2. Modify data
data["load"]["1"]["pd"] = 0.5

# 3. Instantiate model (creates JuMP model)
pm = instantiate_model(data, ACPPowerModel, PowerModels.build_opf)

# 4. Inspect JuMP model
print(pm.model)

# 5. Solve
result = optimize_model!(pm, optimizer=Ipopt.Optimizer)

```

This allows users to add custom constraints/variables to the JuMP model before solving.

**Source:** <https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/>

### PTDF Matrix and Related Utilities

PowerModels provides matrix-based analysis via "basic network" utilities. A basic network is one that has been cleaned (no DC lines, switches, isolated components; contiguous numbering):

```julia

data = parse_file("case14.m")
basic = make_basic_network(data)

ptdf = calc_basic_ptdf_matrix(basic)           # branches x buses
B    = calc_basic_susceptance_matrix(basic)     # buses x buses
Bf   = calc_basic_branch_susceptance_matrix(basic)  # branches x buses
Y    = calc_basic_admittance_matrix(basic)      # complex admittance matrix
A    = calc_basic_incidence_matrix(basic)        # branches x buses (sparse)
J    = calc_basic_jacobian_matrix(basic)         # AC Jacobian

```

Additional utilities:
- `calc_basic_bus_voltage(basic)` -- complex bus voltage vector
- `calc_basic_bus_injection(basic)` -- complex bus injection vector
- `calc_basic_branch_series_impedance(basic)` -- complex impedance vector
- `calc_basic_ptdf_row(basic, branch_idx)` -- single PTDF row for one branch

The PTDF-based OPF (`solve_opf_ptdf`) uses these internally.

**Source:** <https://lanl-ansi.github.io/PowerModels.jl/stable/basic-data-utilities/;> GitHub issue #728

### LMP / Dual Value Extraction

Dual values (shadow prices on power balance constraints) can be extracted for DC-OPF:

```julia

result = solve_dc_opf("case14.m", Ipopt.Optimizer,
    setting = Dict("output" => Dict("duals" => true)))

# LMP at each bus (active power balance dual)
for (id, bus) in result["solution"]["bus"]
    println("Bus $id LMP: $(bus["lam_kcl_r"])")
end

```

- `"lam_kcl_r"` = active power balance Lagrange multiplier (real power LMP)
- `"lam_kcl_i"` = reactive power balance Lagrange multiplier

AC-OPF dual support is partial/experimental as of v0.21. The JuMP backend theoretically provides duals for any continuous formulation via `JuMP.dual()`, but PowerModels does not automatically extract all constraint duals.

**Source:** <https://github.com/lanl-ansi/PowerModels.jl/issues/409>

### Multi-Network / Multi-Period

```julia

data = parse_file("case3.m")
mn_data = replicate(data, 24)  # 24 time periods

# Modify each period
for (nw_id, nw) in mn_data["nw"]
    nw["load"]["1"]["pd"] = load_profile[parse(Int, nw_id)]
end

result = solve_mn_opf(mn_data, DCPPowerModel, HiGHS.Optimizer)

# With storage (time-coupled energy state constraints)
result = solve_mn_opf_strg(mn_data, DCPPowerModel, HiGHS.Optimizer)

```

The `time_elapsed` parameter (hours) controls energy-to-power conversion for storage state transitions between periods.

**Source:** <https://lanl-ansi.github.io/PowerModels.jl/stable/multi-networks/;> <https://lanl-ansi.github.io/PowerModels.jl/stable/storage/>

### Ecosystem / Extension Packages

PowerModels is the foundation for a family of packages from LANL-ANSI:

| Package | Purpose |
|---------|---------|
| **PowerModelsSecurityConstrained.jl** | SCOPF, contingency analysis, PTDF cuts |
| **PowerModelsDistribution.jl** | Unbalanced distribution network optimization |
| **PowerModelsAnnex.jl** | Exploratory/experimental formulations |
| **PowerModelsACDC.jl** | Hybrid AC/DC grid OPF (KU Leuven) |
| **PowerModelsStability.jl** | Transient stability constraints |
| **GasModels.jl / WaterModels.jl** | Multi-infrastructure (gas/water + power) |

**Source:** <https://github.com/lanl-ansi/PowerModels.jl;> <https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl>

### What PowerModels Does NOT Provide

- **Unit commitment (SCUC/SCED):** No binary on/off generator decisions. Use `UnitCommitment.jl` (ANL-CEEESA) instead.
- **Time-domain simulation:** Steady-state only; no transient, dynamic, or EMT simulation.
- **Contingency analysis (N-1):** Not in core; requires `PowerModelsSecurityConstrained.jl`.
- **Stochastic OPF:** No built-in scenario/chance-constraint support (GitHub issue #112 remains open).
- **Full LMP decomposition:** Only power balance duals are extracted; congestion and loss components require manual computation.
- **Three-phase / unbalanced:** Requires `PowerModelsDistribution.jl`.

## Sources

1. [PowerModels.jl GitHub repository](https://github.com/lanl-ansi/PowerModels.jl)
2. [PowerModels.jl stable documentation -- Home](https://lanl-ansi.github.io/PowerModels.jl/stable/)
3. [PowerModels.jl -- Network Formulations](https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/)
4. [PowerModels.jl -- Formulation Details](https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/)
5. [PowerModels.jl -- Network Data Format](https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/)
6. [PowerModels.jl -- Getting Started / Quick Guide](https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/)
7. [PowerModels.jl -- Power Flow](https://lanl-ansi.github.io/PowerModels.jl/stable/power-flow/)
8. [PowerModels.jl -- Multi-Networks](https://lanl-ansi.github.io/PowerModels.jl/stable/multi-networks/)
9. [PowerModels.jl -- Storage](https://lanl-ansi.github.io/PowerModels.jl/stable/storage/)
10. [PowerModels.jl -- Basic Data Utilities](https://lanl-ansi.github.io/PowerModels.jl/stable/basic-data-utilities/)
11. [GitHub issue #409 -- Nodal Prices](https://github.com/lanl-ansi/PowerModels.jl/issues/409)
12. [GitHub issue #728 -- PTDF/Incidence Matrix](https://github.com/lanl-ansi/PowerModels.jl/issues/728)
13. [GitHub issue #112 -- Multi-period/Stochastic OPF](https://github.com/lanl-ansi/PowerModels.jl/issues/112)
14. [PowerModelsSecurityConstrained.jl](https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl)
15. [PowerModelsDistribution.jl](https://github.com/lanl-ansi/PowerModelsDistribution.jl)
16. [PowerModelsAnnex.jl](https://github.com/lanl-ansi/PowerModelsAnnex.jl)
17. [UnitCommitment.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl)
18. Installed source: `/opt/julia-depot/packages/PowerModels/VCmhH/` (devcontainer)
19. Project.toml: `/workspace/evaluations/powermodels/Project.toml` (devcontainer)

## Gaps and Uncertainties

- **AC-OPF dual value support:** The docs and GitHub issues suggest partial support but it is unclear which formulations fully report duals in v0.21.5. Needs testing with `setting = Dict("output" => Dict("duals" => true))` on ACPPowerModel.
- **LMP decomposition into energy/congestion/loss components:** Not provided out of the box. Must be manually computed from PTDF and constraint duals. Needs verification of what dual values are actually populated.
- **Stochastic OPF:** GitHub issue #112 (2017) asked about this; status unclear. The multi-network framework could theoretically support scenarios but no built-in stochastic formulation exists.
- **`DCMPPowerModel` vs `DCPPowerModel` numerical differences:** Documentation states different susceptance calculations (`-1/br_x` vs `-br_x/(br_r^2+br_x^2)`). Impact on results for networks with non-negligible resistance should be tested.
- **Performance of native PF vs. JuMP PF:** Documentation claims `compute_dc_pf` offers "significant memory saving and marginal performance saving" but no benchmarks are cited. Should be tested for scalability evaluation.
- **Multi-network storage constraints:** The linking constraints between time periods (energy state transitions) are documented mathematically but should be verified to work correctly with real storage scenarios.
- **PSS/E parser completeness:** Only v33 is mentioned. Compatibility with newer PSS/E versions (v34, v35) is undocumented.
- **On/off generator constraints:** `constraint_gen_power_on_off` and `variable_gen_indicator` exist in exports, suggesting some UC-like binary dispatch support within OTS/TNEP, but this is not documented as a standalone capability. Needs investigation.

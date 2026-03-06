# PowerModels.jl -- Research: API & Formulations

**Version evaluated:** 0.21.5
**Julia compatibility:** 1.10+ (tested on 1.10; docs generated with 1.11.6)
**Repository:** [lanl-ansi/PowerModels.jl](https://github.com/lanl-ansi/PowerModels.jl)
**GitHub stats:** 456 stars, 167 forks, 87 open issues, created 2016-08-01
**License:** BSD-style (custom LANL; shown as "NOASSERTION" on GitHub)
**Last push:** 2025-12-01

## Key Findings

- **Dict-based data model, not structs.** Network data is a `Dict{String, Any}` with string keys throughout, enabling JSON serialization but sacrificing type safety. Components include `"bus"`, `"branch"`, `"gen"`, `"load"`, `"shunt"`, `"storage"`, `"dcline"`, `"switch"`.
- **18 formulation types** are exported, from exact nonlinear (ACP, ACR, ACT, IVR) through linear approximations (DCP, DCMP, BFA, NFA) to convex relaxations (SOCWR, SOCBF, QC variants) and SDP relaxations. All are subtypes of `AbstractPowerModel`.
- **Problem-formulation decoupling** is the core architectural pattern. Any `solve_*` function accepts any compatible `AbstractPowerModel` subtype and any JuMP-compatible solver as arguments.
- **24 `solve_*` functions** are exported, covering power flow (PF), optimal power flow (OPF), optimal transmission switching (OTS), transmission network expansion planning (TNEP), optimal power balance (OPB), and multi-network variants with storage.
- **No built-in SCUC/SCED.** Unit commitment is handled by a separate package ([UnitCommitment.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl)). PowerModels focuses on steady-state optimization only.
- **Dual variables / LMP extraction** works for linear formulations (DC OPF) via `setting = Dict("output" => Dict("duals" => true))`. Bus duals appear as `lam_kcl_r` (real power balance Lagrange multiplier) in the solution dict. AC OPF dual extraction is limited.
- **Multi-network (multi-period)** support exists via `replicate()` and `solve_mn_*` functions, but it is an advanced feature requiring manual data construction. No native time-series ingestion.
- **SCOPF is a separate package** ([PowerModelsSecurityConstrained.jl](https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl)), not in core PowerModels.
- **Input formats:** MATPOWER `.m` files and PTI/PSS(R)E v33 `.raw` files. Output is always a Julia `Dict` (no file export functions).
- **PTDF matrix computation** is built in via `calc_basic_ptdf_matrix()` and related matrix utilities.

## Detailed Notes

### Entry Points and solve_* Functions

All `solve_*` functions follow the pattern:

```julia
result = solve_<problem>(<data_source>, <FormulationType>, <Optimizer>)

```

Convenience shorthands exist for common cases:

```julia
solve_ac_opf("case3.m", Ipopt.Optimizer)    # equivalent to solve_opf(..., ACPPowerModel, ...)
solve_dc_opf("case3.m", HiGHS.Optimizer)    # equivalent to solve_opf(..., DCPPowerModel, ...)
solve_ac_pf("case3.m", Ipopt.Optimizer)
solve_dc_pf("case3.m", HiGHS.Optimizer)

```

Complete list of exported `solve_*` functions (from v0.21.5 source introspection):

| Function | Description |

|----------|-------------|

| `solve_ac_opf` | AC optimal power flow (shorthand) |

| `solve_ac_pf` | AC power flow (shorthand) |

| `solve_dc_opf` | DC optimal power flow (shorthand) |

| `solve_dc_pf` | DC power flow (shorthand) |

| `solve_mn_opf` | Multi-network OPF |

| `solve_mn_opf_bf_strg` | Multi-network branch-flow OPF with storage |

| `solve_mn_opf_strg` | Multi-network OPF with storage |

| `solve_model` | Generic model solver (low-level) |

| `solve_nfa_opb` | Network flow approximation optimal power balance |

| `solve_obbt_opf!` | Optimality-based bound tightening OPF |

| `solve_opb` | Optimal power balance (copper plate) |

| `solve_opf` | Formulation-agnostic OPF |

| `solve_opf_bf` | OPF with branch flow formulation |

| `solve_opf_branch_power_cuts` | OPF with lazy branch power cuts |

| `solve_opf_branch_power_cuts!` | In-place variant |

| `solve_opf_iv` | OPF with current-voltage formulation |

| `solve_opf_ptdf` | OPF using PTDF formulation (DCPPowerModel only) |

| `solve_opf_ptdf_branch_power_cuts` | PTDF OPF with lazy cuts |

| `solve_opf_ptdf_branch_power_cuts!` | In-place variant |

| `solve_ots` | Optimal transmission switching |

| `solve_pf` | Formulation-agnostic power flow |

| `solve_pf_bf` | Power flow with branch flow formulation |

| `solve_pf_iv` | Power flow with current-voltage formulation |

| `solve_theta` | Voltage angle recovery |

| `solve_tnep` | Transmission network expansion planning |

Source: Runtime introspection of `names(PowerModels)` in v0.21.5 via devcontainer.

### Native (Non-JuMP) Solvers

PowerModels also provides direct matrix-based solvers that bypass JuMP:

- `compute_ac_pf(data)` / `compute_ac_pf!(data)` -- Nonlinear AC power flow using Newton-Raphson on the admittance matrix (polar coordinates)
- `compute_dc_pf(data)` -- Linear DC power flow using the susceptance matrix
- `compute_basic_dc_pf(data)` -- Simplified DC power flow for basic networks

These are faster for pure power flow (no optimization) because they avoid JuMP model construction overhead.

Source: [Power Flow docs](https://lanl-ansi.github.io/PowerModels.jl/stable/power-flow/)

### Formulation Types (All 18 Exported Concrete Types)

**Exact Non-Convex Models:**

| Type | Description |

|------|-------------|

| `ACPPowerModel` | AC power flow, polar bus voltage variables (V, theta) |

| `ACRPowerModel` | AC power flow, rectangular bus voltage variables (Vr, Vi) |

| `ACTPowerModel` | AC power flow with voltage angle and squared magnitude variables |

| `IVRPowerModel` | Current-voltage formulation, rectangular coordinates |

**Linear Approximations:**

| Type | Description |

|------|-------------|

| `DCPPowerModel` | Standard DC approximation using `br_b = -br_x / (br_r^2 + br_x^2)` |

| `DCMPPowerModel` | MATPOWER-compatible DC model using `br_b = -1/br_x` with transformer params |

| `DCPLLPowerModel` | DC with piecewise-linear losses |

| `BFAPowerModel` | Linear branch flow approximation (LinDistFlow) |

| `NFAPowerModel` | Network flow approximation (active power only, transportation model) |

**Quadratic Approximations:**

| Type | Description |

|------|-------------|

| `LPACCPowerModel` | LPAC cold-start approximation with quadratic cosine terms |

**Quadratic/Conic Relaxations:**

| Type | Description |

|------|-------------|

| `SOCWRPowerModel` | Second-order cone relaxation (QCP formulation) |

| `SOCWRConicPowerModel` | SOC relaxation (conic formulation) |

| `QCRMPowerModel` | Quadratic-convex relaxation with McCormick envelopes |

| `QCLSPowerModel` | Strengthened QC relaxation with extreme-point encoding |

| `SOCBFPowerModel` | SOC relaxation of branch flow model |

| `SOCBFConicPowerModel` | SOC branch flow (conic formulation) |

**SDP Relaxations:**

| Type | Description |

|------|-------------|

| `SDPWRMPowerModel` | Semidefinite relaxation using W matrix variables |

| `SparseSDPWRMPowerModel` | Sparsity-exploiting SDP using matrix completion |

All concrete types inherit from abstract types (e.g., `AbstractACPModel`, `AbstractDCPModel`, `AbstractSOCWRModel`) enabling dispatch-based extensibility.

Source: [Formulations docs](https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/), [Formulation Details docs](https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/), runtime `names(PowerModels)` introspection.

### Data Model

The internal data representation is `Dict{String, Any}` (not typed structs). This is by design for JSON serialization and algorithmic data exchange.

**Top-level keys** (from parsing `case39.m`):

```

baseMVA       => 100 (Int64)
bus           => Dict with 39 entries
branch        => Dict with 46 entries
gen           => Dict with 10 entries
load          => Dict with 21 entries
shunt         => Dict with 0 entries
storage       => Dict with 0 entries
dcline        => Dict with 0 entries
switch        => Dict with 0 entries
per_unit      => true (Bool)
name          => "case39"
source_type   => "matpower"
source_version => "2"

```

**Key structural differences from MATPOWER:**
- Load and shunt data are separated from bus data into their own component dictionaries
- All components are indexed by string keys (e.g., `data["bus"]["1"]`)
- Each component has an `"index"` field (integer) and `"source_id"` field
- All values are per-unit; angles are in radians (not degrees)
- Transformer branches get `tap` and `shift` fields (nominal: `tap=1.0, shift=0.0`)

**Bus fields:** `bus_i`, `bus_type`, `area`, `zone`, `base_kv`, `vm`, `va`, `vmin`, `vmax`, `index`, `source_id`

**Generator fields:** `gen_bus`, `pg`, `qg`, `pmin`, `pmax`, `qmin`, `qmax`, `gen_status`, `model` (1=PWL, 2=polynomial), `ncost`, `cost` (vector), `vg`, `mbase`, `apf`, `startup`, `shutdown`, `ramp_10`, `ramp_30`, `ramp_agc`, `ramp_q`, plus `pc1`, `pc2`, `qc1min/max`, `qc2min/max`

**Branch fields:** `f_bus`, `t_bus`, `br_r`, `br_x`, `br_status`, `tap`, `shift`, `transformer` (bool), `rate_a`, `rate_b`, `rate_c`, `angmin`, `angmax`, `b_fr`, `b_to`, `g_fr`, `g_to`, `index`, `source_id`

**Load fields:** `load_bus`, `pd`, `qd`, `status`, `index`, `source_id`

**Storage fields:** `storage_bus`, `ps`, `qs`, `energy`, `energy_rating`, `charge_rating`, `discharge_rating`, `charge_efficiency`, `discharge_efficiency`, `qmin`, `qmax`, `r`, `x`, `p_loss`, `q_loss`, `thermal_rating`, `current_rating`

Source: [Network Data Format docs](https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/), runtime introspection of parsed case39.m.

### Input/Output Formats

**Input (parsing):**
- MATPOWER `.m` files via `parse_matpower()` or `parse_file()`
- PTI/PSS(R)E v33 `.raw` files via `parse_psse()` / `parse_pti()` or `parse_file()`
- PowerModels JSON format via `parse_json()`
- `parse_file()` auto-detects format by extension
- `parse_files()` merges multiple files
- `import_all=true` flag preserves PSS(R)E extension data not used by PowerModels

**Output:**
- Results are returned as `Dict{String, Any}` -- no file-writing functions are provided
- `print_summary(result["solution"])` for human-readable output
- Solution dict mirrors input structure: `result["solution"]["bus"]["1"]["va"]`
- Top-level result keys: `termination_status`, `primal_status`, `dual_status`, `objective`, `objective_lb`, `solve_time`, `optimizer`, `solution`

**Note:** PSS(R)E v34 is NOT supported (see [issue #921](https://github.com/lanl-ansi/PowerModels.jl/issues/921)).

Source: [Quick Guide](https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/), runtime introspection.

### Solver Interface

PowerModels uses JuMP as its optimization modeling layer. Any solver with a JuMP/MathOptInterface (MOI) wrapper can be used.

**Solver configuration pattern:**

```julia
# Simple: pass optimizer type
result = solve_ac_opf("case3.m", Ipopt.Optimizer)

# With options: use optimizer_with_attributes (re-exported from JuMP)
result = solve_ac_opf("case3.m",
    optimizer_with_attributes(Ipopt.Optimizer, "print_level" => 0))

```

**Solver requirements by formulation:**

| Formulation | Required solver type |

|-------------|---------------------|

| DCPPowerModel, NFAPowerModel | LP solver (HiGHS, GLPK, Gurobi) |

| ACPPowerModel, ACRPowerModel, IVRPowerModel | NLP solver (Ipopt, KNITRO) |

| SOCWRPowerModel, SOCBFPowerModel | QCP/SOCP solver (Gurobi, Mosek, ECOS) |

| SOCWRConicPowerModel, SOCBFConicPowerModel | Conic solver (SCS, Mosek) |

| SDPWRMPowerModel | SDP solver (Mosek, SCS, CSDP) |

| OTS, TNEP (with DCPPowerModel) | MILP solver (HiGHS, GLPK, Gurobi, SCIP) |

| OTS (with ACPPowerModel) | MINLP solver (Juniper, SCIP) |

**Two-stage model building** (for advanced use):

```julia
pm = instantiate_model(data, ACPPowerModel, PowerModels.build_opf)
result = optimize_model!(pm, optimizer=Ipopt.Optimizer)
# Access JuMP model directly: pm.model

```

Source: [Quick Guide](https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/), Project.toml dependencies.

### Dual Variables and LMP Extraction

Dual variable extraction is available for linear formulations (DC OPF):

```julia
result = solve_dc_opf(data, HiGHS.Optimizer;
    setting = Dict("output" => Dict("duals" => true)))

# Bus-level duals (LMP proxy for DC OPF):
result["solution"]["bus"]["1"]["lam_kcl_r"]  # real power balance dual
result["solution"]["bus"]["1"]["lam_kcl_i"]  # reactive power balance dual (NaN for DC)

# Branch-level duals (congestion):
result["solution"]["branch"]["1"]["mu_sm_fr"]  # thermal limit dual (from bus)
result["solution"]["branch"]["1"]["mu_sm_to"]  # thermal limit dual (to bus)

```

**Limitations:**
- LMP decomposition (energy + congestion + losses) is NOT built in
- AC OPF dual extraction was limited due to JuMP/MOI constraints (per [issue #409](https://github.com/lanl-ansi/PowerModels.jl/issues/409))
- PTDF-based shift factors are available (`calc_basic_ptdf_matrix`) but not integrated with LMP decomposition

Source: [GitHub issue #409](https://github.com/lanl-ansi/PowerModels.jl/issues/409), runtime verification.

### Multi-Network / Multi-Period Support

PowerModels supports multi-network data for time-series or scenario analysis:

```julia
# Create 3 time periods from a single network
mn_data = PowerModels.replicate(data, 3)

# Modify each period independently
mn_data["nw"]["1"]["load"]["1"]["pd"] = 1.0
mn_data["nw"]["2"]["load"]["1"]["pd"] = 1.5
mn_data["nw"]["3"]["load"]["1"]["pd"] = 2.0

# Solve multi-network OPF
result = solve_mn_opf(mn_data, DCPPowerModel, HiGHS.Optimizer)

```

**Multi-network solve functions:**
- `solve_mn_opf` -- multi-period OPF
- `solve_mn_opf_strg` -- multi-period OPF with storage (inter-temporal energy constraints)
- `solve_mn_opf_bf_strg` -- multi-period branch-flow OPF with storage

**Key consideration:** The `replicate()` function performs a deep copy of the full network for each period, which can be memory-intensive for large networks with many periods. The `time_elapsed` parameter (hours) in the data dict controls energy-to-power conversion for storage.

**System-level parameters:**
- `data["multinetwork"]` -- boolean flag
- `data["time_elapsed"]` -- hours elapsed per period (for storage energy calculations)

Source: [Multi Networks docs](https://lanl-ansi.github.io/PowerModels.jl/stable/multi-networks/), [Network Data docs](https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/).

### SCOPF and Contingency Analysis

**Not in core PowerModels.** Security-constrained OPF requires the separate package [PowerModelsSecurityConstrained.jl](https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl) (also by LANL).

Key features of the extension:
- Developed for ARPA-e Grid Optimization Competition Challenge 1 (October 2019)
- Iterative SCOPF solver: checks violated branch flow constraints in contingencies and resolves until fixed-point
- Uses PTDF-based flow cuts under DC power flow assumption
- Base-case model is formulation-agnostic (can use AC or DC)
- Also available: [PowerModelsACDCsecurityconstrained.jl](https://github.com/csiro-energy-systems/PowerModelsACDCsecurityconstrained.jl) for hybrid AC/DC grids

Source: [PowerModelsSecurityConstrained.jl docs](https://lanl-ansi.github.io/PowerModelsSecurityConstrained.jl/stable/), [Julia Discourse thread](https://discourse.julialang.org/t/powermodels-jl-multinetwork-for-security-constrained-ac-opf/113511).

### Unit Commitment (SCUC/SCED)

**Not supported.** PowerModels is strictly a steady-state network optimization tool. It does not model:
- Binary on/off commitment variables
- Minimum up/down time constraints
- Start-up/shut-down costs (fields exist in data but are not used in formulations)
- Ramping constraints across time periods (ramp fields exist in data but are unused)

For unit commitment, the Julia ecosystem offers [UnitCommitment.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl) (by ANL-CEEESA), which is a separate package.

Source: Web search, PowerModels exported function list (no UC-related build/solve functions).

### Matrix Utility Functions

PowerModels exports a comprehensive set of matrix computation utilities:

| Function | Returns |

|----------|---------|

| `calc_admittance_matrix(data)` | Complex admittance matrix (Y-bus) |

| `calc_susceptance_matrix(data)` | Real susceptance matrix (B) |

| `calc_admittance_matrix_inv(data)` | Inverse admittance matrix |

| `calc_susceptance_matrix_inv(data)` | Inverse susceptance matrix |

| `calc_basic_ptdf_matrix(data)` | PTDF matrix (branch x bus) |

| `calc_basic_ptdf_row(data, branch_idx)` | Single PTDF row |

| `calc_basic_incidence_matrix(data)` | Incidence matrix (+1/-1) |

| `calc_basic_jacobian_matrix(data)` | AC power flow Jacobian |

| `calc_basic_branch_susceptance_matrix(data)` | Branch susceptance matrix |

| `calc_branch_flow_ac(data)` | AC branch flows from solution |

| `calc_branch_flow_dc(data)` | DC branch flows from solution |

The `calc_basic_*` functions require pre-processing with `make_basic_network(data)` which removes DC lines, switches, and inactive components.

Source: [Basic Data Utilities docs](https://lanl-ansi.github.io/PowerModels.jl/stable/basic-data-utilities/).

### Ecosystem Extensions

PowerModels serves as a foundation for several extension packages:

| Package | Purpose |

|---------|---------|

| [PowerModelsDistribution.jl](https://github.com/lanl-ansi/PowerModelsDistribution.jl) | Unbalanced (multi-conductor) distribution networks |

| [PowerModelsSecurityConstrained.jl](https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl) | SCOPF with contingency constraints |

| [PowerModelsACDC.jl](https://github.com/Electa-Git/PowerModelsACDC.jl) | Hybrid AC/DC grid OPF |

| [PowerModelsGMD.jl](https://github.com/lanl-ansi/PowerModelsGMD.jl) | Geomagnetic disturbance modeling |

| [PowerModelsProtection.jl](https://github.com/lanl-ansi/PowerModelsProtection.jl) | Fault study formulations |

| [PowerModelsONM.jl](https://github.com/lanl-ansi/PowerModelsONM.jl) | Outage management for distribution |

All extensions follow the same `AbstractPowerModel` type hierarchy and JuMP-based architecture.

### Energy Storage Model

PowerModels includes a generic storage component with:
- Six decision variables: energy state, charge/discharge amounts, reactive power, complex power injection
- Six constraint types: energy balance, charge/discharge complementarity (NL or MI), loss accounting, reactive limits, thermal limits, current limits
- Inter-temporal coupling via `time_elapsed` parameter in multi-network mode
- Charge/discharge efficiency parameters

Storage is fully integrated into multi-network OPF via `solve_mn_opf_strg()` and `solve_mn_opf_bf_strg()`.

Source: [Storage docs](https://github.com/lanl-ansi/PowerModels.jl/blob/master/docs/src/storage.md), [arxiv.org/abs/2004.14768](https://arxiv.org/abs/2004.14768).

## Sources

1. [PowerModels.jl GitHub repository](https://github.com/lanl-ansi/PowerModels.jl)
2. [PowerModels.jl stable documentation -- home](https://lanl-ansi.github.io/PowerModels.jl/stable/)
3. [Quick Guide](https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/)
4. [Network Formulations](https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/)
5. [Formulation Details](https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/)
6. [Network Data Format](https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/)
7. [Power Flow](https://lanl-ansi.github.io/PowerModels.jl/stable/power-flow/)
8. [Problem Specifications](https://lanl-ansi.github.io/PowerModels.jl/stable/specifications/)
9. [Basic Data Utilities](https://lanl-ansi.github.io/PowerModels.jl/stable/basic-data-utilities/)
10. [Multi Networks docs (v0.11)](https://lanl-ansi.github.io/PowerModels.jl/v0.11/multi-networks/)
11. [GitHub issue #409 -- Nodal Prices](https://github.com/lanl-ansi/PowerModels.jl/issues/409)
12. [GitHub issue #112 -- Multi-period/stochastic OPF](https://github.com/lanl-ansi/PowerModels.jl/issues/112)
13. [GitHub issue #921 -- PSS/E v34 support](https://github.com/lanl-ansi/PowerModels.jl/issues/921)
14. [PowerModelsSecurityConstrained.jl](https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl)
15. [UnitCommitment.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl)
16. [Julia Discourse -- SCOPF multinetwork discussion](https://discourse.julialang.org/t/powermodels-jl-multinetwork-for-security-constrained-ac-opf/113511)
17. Runtime introspection of PowerModels v0.21.5 via devcontainer (exported symbols, parsed data structures, solve results)
18. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/Project.toml`
19. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/verify_install.jl`
20. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/test/test_gate.jl`

## Gaps and Uncertainties

- **AC OPF dual extraction status:** Issue #409 was closed but the discussion indicates full AC dual support may still be incomplete. Needs verification with Ipopt on a small case to see if `lam_kcl_r` populates correctly for AC formulations.
- **PSS(R)E version support:** Only v33 is confirmed. v34 support is an open issue (#921). The extent of v33 coverage (which record types are parsed) is unclear.
- **Multi-network data construction:** The `replicate()` function is documented, but how to build multi-network data from scratch (without replicating) is not well-documented. Extension packages may have better patterns.
- **Output export:** No built-in functions to write results back to MATPOWER `.m` or PSS(R)E `.raw` format. Users must implement their own serialization.
- **Cost model flexibility:** Generator cost data supports piecewise-linear (model=1) and polynomial (model=2) via MATPOWER conventions, but it is unclear whether custom cost functions can be injected without subclassing.
- **Performance at scale:** No benchmarks found for networks beyond standard test cases (e.g., 10,000+ bus systems). The `replicate()` deep-copy approach for multi-period may not scale.
- **License specifics:** GitHub shows "NOASSERTION" rather than a standard SPDX identifier. The actual license terms in the repo should be reviewed for contract compliance.
- **Switch component:** Documented in the data model but no dedicated `solve_*` functions for switch optimization (unlike OTS which uses branch status variables).

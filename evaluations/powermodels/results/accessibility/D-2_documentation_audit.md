---
test_id: D-2
tool: powermodels
dimension: accessibility
network: N/A
status: qualified_pass
workaround_class: null
timestamp: 2026-03-13T23:00:00Z
protocol_version: v10
skill_version: v1
test_hash: "dd0263e3"
---

# D-2: Documentation Audit

## Assessment Method

For each Suite A test (A-1 through A-12), assess whether implementation is possible using **only** the official documentation at `https://lanl-ansi.github.io/PowerModels.jl/stable/`. No source code reading, no GitHub issues, no Stack Overflow.

Documentation structure reviewed:
- Home (overview, installation)
- Manual: Getting Started, Network Data Format, Result Data Format, Mathematical Model, Power Flow, Storage Model, Switch Model, Multi Networks, Utilities, Basic Data Utilities
- Library: Network Formulations, Problem Specifications, Modeling Components, Relaxation Schemes, File IO
- Developer: Formulation Details

Rating scale:
- **Fully documented** -- example code in docs covers the exact API; no inference required
- **Partially documented** -- API is documented but usage pattern requires inference
- **Source code required** -- result structure, key names, or behavior not described; source code reading was necessary
- **Undocumented gap** -- functionality does not exist or is not mentioned in docs at all

## Per-Test Audit

### A-1: DC Power Flow (DCPF)

**Rating: Partially documented**

The docs describe both `compute_dc_pf` and `solve_dc_pf`. The return structure (bus angles in `result["solution"]["bus"][id]["va"]`) is covered. However, branch flows are **not** in the result dict -- this gap is not mentioned in the docs. A new user following the quickstart will compute angles correctly but will not find branch flows in the obvious location.

From the api-friction observation: `result["solution"]["branch"]` does not exist for `compute_dc_pf`. The workaround (compute from angles manually using the DC power flow formula, or use `calc_branch_flow_dc`) requires reading source code or inferring from the utility functions list.

Additionally, `termination_status` returned as a `Bool` from `compute_dc_pf` (vs a JuMP `TerminationStatusCode` from `solve_dc_opf`) is undocumented.

### A-2: AC Power Flow (ACPF)

**Rating: Partially documented**

`compute_ac_pf` is documented with its return structure. Bus voltages (`vm`, `va`) and generator outputs (`pg`, `qg`) are described. Branch flows require the `calc_branch_flow_ac` post-processing call -- this function is mentioned in the docs but the two-step workflow is not shown with an end-to-end example.

From the convergence-quality observation: NR iteration count and final residual are not exposed in the result dict. This diagnostic gap is not mentioned in the docs. A user expecting convergence quality metrics will find only a Bool termination status and solve time.

### A-3: DC OPF with LMPs

**Rating: Fully documented**

`solve_dc_opf` is covered in the quickstart with optimizer syntax. The `setting=Dict("output" => Dict("duals" => true))` kwarg for enabling LMPs is documented in the solution output section. The `lam_kcl_r` key for LMP extraction is listed in the bus solution dict documentation. Cost model structure (polynomial model 2) is documented in the network data format section.

One friction point: the docs show `solve_dc_opf(file, optimizer)` clearly, but some older examples use the deprecated 3-argument form. This causes confusion (as noted in D-1).

### A-4: AC Feasibility Check (Warm-start from DCOPF)

**Rating: Partially documented**

`solve_ac_opf` and `compute_ac_pf` are both documented. The warm-start pattern (setting bus `vm`/`va` from a prior DC solution) is described in the power flow documentation. However, the exact dict key structure for setting initial conditions is not shown with a worked example. The two-step DCOPF-then-ACPF pattern for feasibility checking is not illustrated in the docs.

Branch flows require post-processing via `calc_branch_flow_ac`, same gap as A-2. The `update_data!` function for merging solution values back into data is documented but not shown in this workflow context.

### A-5: SCUC (Unit Commitment)

**Rating: Undocumented gap**

SCUC is not a built-in problem type in PowerModels.jl. The docs do not mention it. UC binary variables, min up/down times, and startup costs are not in the PowerModels data model. Implementation requires a fully custom JuMP model (~250 LOC) using PowerModels only for data parsing. This limitation is not called out in the docs -- a user would only discover it after exhausting the problem type list.

### A-6: SCED (Economic Dispatch from UC Schedule)

**Rating: Partially documented**

Multi-network OPF (`solve_mn_opf`) is documented. The `replicate` function for constructing multi-network data from a single network is covered. However, the workflow for fixing commitment from a prior SCUC solve (setting `pmin`/`pmax` to enforce commitment) and constructing time-varying load profiles requires source code reading or test suite examples. Ramp rate constraints between periods are not part of the standard `build_mn_opf` formulation -- the user must add them manually.

### A-7: N-1 Contingency Sweep

**Rating: Partially documented**

The `deepcopy` + `br_status=0` + `compute_dc_pf` loop pattern is not described anywhere in the official docs. The `compute_dc_pf` function is documented; `br_status` as a branch field is part of the data model reference. Users must independently derive the contingency loop pattern. `calc_connected_components` is documented and is needed to handle island formation.

### A-8: Stochastic Timeseries OPF

**Rating: Undocumented gap**

There is no stochastic OPF formulation in PowerModels. The `replicate` multi-network facility creates T-period coupling (temporal), not scenario branching. No scenario tree, non-anticipativity constraints, or probability-weighted objectives exist. The docs do not mention stochastic optimization at all.

### A-9: SCOPF (Security-Constrained OPF)

**Rating: Source code required**

SCOPF is mentioned in the ecosystem context (`PowerModelsSecurityConstrained.jl` exists as a separate package) but the core PowerModels library has no built-in SCOPF. Implementing it via LODF-based constraints requires:
1. LODF computation from PTDF (undocumented formula)
2. Branch flow variable access via `var(pm, :p)[(br_idx, f_bus, t_bus)]` -- the tuple key format is discoverable only by inspecting source code
3. Understanding that `make_basic_network` is required before `calc_basic_ptdf_matrix` (not in docstrings)

From the doc-gap observation: these patterns required reverse-engineering from source and power systems literature.

### A-10: Lossy DC OPF with LMP Decomposition

**Rating: Source code required**

`DCPLLPowerModel` is listed in the formulations reference but its solver requirements (Ipopt, not HiGHS -- due to QCQP constraints) are not documented. LMP decomposition into energy, congestion, and loss components requires understanding the KKT structure. The docs do not provide a decomposition formula or worked example. The solver incompatibility with HiGHS (from api-friction observation) would surprise users following the standard quickstart pattern.

### A-11: Distributed Slack OPF

**Rating: Undocumented gap**

No distributed slack formulation exists in PowerModels. The docs do not mention it. Implementation requires ~150 LOC of manual PTDF-based OPF construction using JuMP. The `calc_basic_ptdf_matrix` API is documented (a positive), but using it to construct distributed-slack PTDF and a custom OPF model is entirely user-derived.

### A-12: Multi-Period DCOPF with Storage

**Rating: Partially documented**

`solve_mn_opf_strg` is documented as a function name but the storage data model (energy capacity, charge/discharge efficiency, SoC bounds, storage field names) is not fully described with worked examples. The `storage` component of the data model has a brief reference. Cyclic SoC constraints require manual JuMP constraint injection via `instantiate_model` -- this pattern is not shown for storage specifically. The solver requirement (SCIP for MIQP due to binary complementarity variables) is not documented.

## Summary Table

| Test | Documentation Coverage | Source Code Required? | GitHub/SO Required? |
|------|------------------------|----------------------|---------------------|
| A-1 DCPF | Partial | Yes (branch flows) | No |
| A-2 ACPF | Partial | No (calc_branch_flow_ac documented) | No |
| A-3 DCOPF+LMPs | Full | No | No |
| A-4 AC Feasibility | Partial | No (inferrable) | No |
| A-5 SCUC | Undocumented gap | N/A (not built-in) | No |
| A-6 SCED | Partial | Helpful | No |
| A-7 N-1 Contingency | Partial | No (inferrable) | No |
| A-8 Stochastic OPF | Undocumented gap | N/A (not built-in) | No |
| A-9 SCOPF | Source required | Yes (LODF, var access) | No |
| A-10 Lossy DCOPF | Source required | Yes (solver compat, decomp) | No |
| A-11 Distributed Slack | Undocumented gap | N/A (not built-in) | No |
| A-12 Multi-Period+Storage | Partial | Yes (solver req, cyclic SoC) | No |

**Completability from docs alone:** 3 of 12 tests (A-3, and with inference A-1/A-2 partial capabilities). Core power flow and OPF are documented. Advanced problem types (SCUC, stochastic, SCOPF, distributed slack) are either absent from the tool or undocumented.

## Cross-Reference to Consumed Observations

The following observation tags informed this audit:

- **api-friction** (10 observations): Branch flow gaps (A-1, A-2, A-4), solver incompatibilities (A-10 HiGHS/QCQP, A-12 HiGHS/MIQP), quadratic cost QP behavior (A-3), baseMVA type (A-6), no graph library (A-7/B-2), no distributed slack (B-8)
- **doc-gaps** (2 observations): SCOPF LODF pattern undocumented (A-9), formulation methods lack docstrings (B-6)
- **convergence-quality** (1 observation): compute_ac_pf exposes no NR diagnostics (A-2)

## Overall Assessment

**qualified_pass**: Core OPF and power flow tests (A-1, A-2, A-3, A-4) are largely implementable from docs, with the branch-flow post-processing gap being the most consistent friction point. Advanced capabilities (A-5 SCUC, A-8 stochastic, A-11 distributed slack) are absent from the tool entirely. SCOPF and lossy OPF exist but require source code reading to implement.

The documentation is well-structured for formulation-level concepts (the problem-formulation separation, the two-level API, PTDF utilities) but weak on:
1. Worked examples for data manipulation patterns (contingency loops, multi-period construction, storage data model)
2. Solver compatibility matrices (which formulations require which solvers)
3. Result dict key documentation for `compute_*` vs `solve_*` variants
4. Formulation-specific constraint method signatures for extension developers

No test required GitHub issues or Stack Overflow -- where docs were insufficient, source code reading filled the gap. This is a strength of PowerModels being pure Julia: all source is readable and type-annotated.

---
test_id: D-2
tool: powermodels
dimension: accessibility
network: N/A
status: qualified_pass
workaround_class: null
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "3d231b72"
---

# D-2: Documentation Audit

## Assessment Method

For each Suite A test (A-1 through A-12), assess whether implementation is possible using **only** the official documentation at `https://lanl-ansi.github.io/PowerModels.jl/stable/`. No source code reading, no GitHub issues, no Stack Overflow.

Rating scale:
- **Fully documented** — example code in docs covers the exact API; no inference required
- **Partially documented** — API is documented but usage pattern requires inference
- **Source code required** — result structure, key names, or behavior not described; source code reading was necessary
- **Undocumented gap** — functionality does not exist or is not mentioned in docs at all

## Per-Test Audit

### A-1: DC Power Flow (DCPF)

#### Rating: Partially documented

The docs describe both `compute_dc_pf` and `solve_dc_pf`. The return structure (bus angles in `result["solution"]["bus"][id]["va"]`) is covered. However, branch flows are **not** in the result dict — this gap is not mentioned in the docs. A new user following the quickstart will compute angles correctly but will not find branch flows in the obvious location.

From the api-friction observation: `result["solution"]["branch"]` does not exist for `compute_dc_pf`. The workaround (compute from angles manually) requires knowing the DC power flow formula or reading source. Not discoverable from docs alone.

Additionally, `termination_status` returned as a `Bool` from `compute_dc_pf` (vs a JuMP `TerminationStatusCode` from `solve_dc_opf`) is undocumented.

### A-2: AC Power Flow (ACPF)

#### Rating: Partially documented

`compute_ac_pf` is documented with its return structure. Bus voltages (`vm`, `va`) and generator outputs (`pg`, `qg`) are described. Branch flows require the `calc_branch_flow_ac` post-processing call — this function is mentioned in the docs but the two-step workflow is not shown with an end-to-end example.

From the convergence-quality observation: NR iteration count and final residual are not exposed in the result dict. This diagnostic gap is not mentioned in the docs. A user expecting convergence quality metrics will find only a Bool termination status and solve time.

### A-3: DC OPF with LMPs

#### Rating: Fully documented

`solve_dc_opf` is covered in the quickstart with optimizer syntax. The `setting=Dict("output" => Dict("duals" => true))` kwarg for enabling LMPs is documented in the solution output section. The `lam_kcl_r` key for LMP extraction is listed in the bus solution dict documentation.

One friction point: the docs show `solve_dc_opf(file, optimizer)` clearly, but some older examples in the docs use the deprecated 3-argument form. This causes confusion (as noted in D-1).

### A-4: AC Feasibility Check (Warm-start from DCOPF)

#### Rating: Partially documented

`solve_ac_opf` and `compute_ac_pf` are both documented. The warm-start pattern (setting bus `vm`/`va` from a prior DC solution) is described in the power flow documentation. However, the exact dict key structure for setting initial conditions is not shown with a worked example. Users must infer which sub-dict to modify. The two-step DCOPF-then-ACPF pattern for feasibility checking is not illustrated in the docs.

From the api-friction observation on A-4: branch flows require post-processing via `calc_branch_flow_ac`, same gap as A-2.

### A-5: SCUC (Unit Commitment)

#### Rating: Undocumented gap

SCUC is not a built-in problem type in PowerModels.jl. The docs do not mention it. UC binary variables, min up/down times, and startup costs are not in the PowerModels data model. Implementation requires a fully custom JuMP model using PowerModels only for data parsing. This limitation is not called out in the docs — a user would only discover it after exhausting the problem type list.

### A-6: Multi-Period DCOPF

#### Rating: Partially documented

`solve_mn_opf` (multi-network OPF) is documented. The `replicate` function for constructing multi-network data from a single network is covered. However, the workflow for constructing time-varying load profiles (modifying `pd`/`qd` per period) requires source code reading or examples from the test suite — the docs describe the API but not the data manipulation pattern.

### A-7: N-1 Contingency Sweep

#### Rating: Partially documented

The `deepcopy` + `br_status=0` + `compute_dc_pf` loop pattern is not described anywhere in the official docs. The `compute_dc_pf` function is documented; `br_status` as a branch field is part of the data model reference. Users must independently derive the contingency loop pattern. From the arch-quality observation (B-3), this pattern works cleanly and is efficient, but its discoverability is low.

`calc_connected_components` is documented and is needed to handle island formation — this part is findable.

### A-8: Stochastic DCOPF

#### Rating: Partially documented

Multi-network data structures support scenario-based analysis, but the stochastic OPF pattern (building scenario trees, extracting per-scenario results) is not illustrated with a complete example. The `replicate` function can be used to build scenario data, but probability-weighted objectives require custom objective modification.

### A-9: LMP Decomposition

#### Rating: Partially documented

LMPs via `lam_kcl_r` are documented. Decomposing LMP into energy, congestion, and loss components is not documented — it requires understanding the KKT structure of the OPF formulation. The docs do not provide a decomposition formula or example.

### A-10: PTDF Extraction

#### Rating: Fully documented

The `Basic Data Utilities` section documents `calc_basic_ptdf_matrix`, `calc_basic_ptdf_row`, `calc_basic_admittance_matrix`, and related matrix functions explicitly. This is one of the best-documented areas of the API. Column/row ordering relative to the bus index is described.

### A-11: SCOPF (Security-Constrained OPF)

#### Rating: Undocumented gap

SCOPF is not a built-in problem type. The docs do not describe how to formulate it. Users would need to assemble it from the contingency loop pattern (A-7) and the custom constraint injection API (B-1). No example or guidance in the official docs.

### A-12: Multi-Period DCOPF with Storage

#### Rating: Partially documented

`solve_mn_opf_strg` is documented as a function name but the storage data model (energy capacity, charge/discharge efficiency, SoC bounds) is not fully described with field names and units. The `storage` component of the PowerModels data model has a brief reference but no worked example showing how to populate it and interpret results.

From the cross-tool watchpoints: PowerModels does not natively support multi-period OPF with cyclic SoC constraints in a way that is straightforward from docs alone.

## Summary Table

| Test | Documentation Coverage | Source Code Required? | GitHub/SO Required? |
|------|------------------------|----------------------|---------------------|
| A-1 DCPF | Partial | Yes (branch flows) | No |
| A-2 ACPF | Partial | No (calc_branch_flow_ac documented) | No |
| A-3 DCOPF+LMPs | Full | No | No |
| A-4 AC Feasibility | Partial | No (inferrable) | No |
| A-5 SCUC | Undocumented gap | N/A (not possible) | No |
| A-6 Multi-Period | Partial | Helpful | No |
| A-7 N-1 Contingency | Partial | No (inferrable) | No |
| A-8 Stochastic OPF | Partial | Yes | No |
| A-9 LMP Decomposition | Partial | Yes | No |
| A-10 PTDF | Full | No | No |
| A-11 SCOPF | Undocumented gap | N/A (not built-in) | No |
| A-12 Multi-Period+Storage | Partial | Yes | No |

## Overall Assessment

**qualified_pass**: Core OPF and power flow tests (A-1, A-2, A-3, A-4, A-10) are largely implementable from docs, with the branch-flow post-processing gap being the most consistent friction point. Advanced capabilities (A-5 SCUC, A-11 SCOPF) are simply absent from the tool and not mentioned in docs.

The documentation is well-structured for formulation-level concepts (the problem-formulation separation, the two-level API) but weak on worked examples for the data manipulation patterns that most users need (contingency loops, multi-period data construction, storage data model).

No test required GitHub issues or Stack Overflow — where docs were insufficient, source code reading filled the gap.

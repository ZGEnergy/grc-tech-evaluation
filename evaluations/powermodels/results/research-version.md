---
tool: powermodels
installed_version: 0.21.5
release_date: 2025-08-12
latest_version: 0.21.5
latest_release_date: 2025-08-12
research_date: 2026-03-24
---

# powermodels — Version & Capability Report

## Version Summary

The installed version is PowerModels.jl 0.21.5, which is also the current latest stable release (published 2025-08-12). The evaluation environment is fully up to date — there is no version gap to account for. Unreleased commits on master since v0.21.5 are limited to CI dependency bumps (actions/checkout v5->v6, actions/upload-pages-artifact v3->v4) and an update to JSON@1 — no functional changes.

The 0.21.x series has been stable since January 2024 (v0.21.0), with the major change being an update to JuMP's new nonlinear interface. Patch releases since then have been limited to bug fixes (PSS/E parser corrections, `compute_ac_pf` numerical precision errors, switch resolution logic, three-winding transformer parsing), performance improvements to basic data utilities (`calc_basic_incidence_matrix`, `calc_connected_components`, in-place building of basic network data), and developer tooling (PrecompileTools integration, CI updates, Memento logger silencing during precompilation). No new features or capability additions were made in the 0.21.x series beyond what was present in 0.21.0.

Key dependencies in the installed environment: JuMP v1.29.4, InfrastructureModels v0.7.8, with solvers Ipopt (nonlinear), HiGHS (LP/MIP), GLPK (LP/MIP), and SCIP (MIP/MINLP). JuMP and HiGHS have newer versions available upstream but the pinned versions are functional.

PowerModels.jl supports an extensive set of power flow formulations: exact non-convex models (ACPPowerModel polar, ACRPowerModel rectangular, ACTPowerModel w-space, IVRPowerModel current-voltage), linear approximations (DCPPowerModel, DCMPPowerModel with transformer parameters, BFAPowerModel branch flow, NFAPowerModel network flow), quadratic approximations (DCPLLPowerModel, LPACCPowerModel cold-start), quadratic relaxations (SOCWRPowerModel, SOCWRConicPowerModel, QCRMPowerModel, QCLSPowerModel, SOCBFPowerModel, SOCBFConicPowerModel), and SDP relaxations (SDPWRMPowerModel, SparseSDPWRMPowerModel). Problem specifications include Power Flow (PF), Optimal Power Flow (OPF), Optimal Power Balance (OPB), Optimal Transmission Switching (OTS), and Transmission Network Expansion Planning (TNEP), each available in BIM, BFM, and CFM variants where applicable.

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
| Warm Start / Solution Reuse | partial | 0.16.0 | PowerModels documents warm starting via `*_start` data keys (`pg_start`, `qg_start`, `vm_start`, `va_start`) and provides `set_ac_pf_start_values!` to configure a solution as starting values. However, the docs warn warm starting is "a very delicate task and can easily result in degraded performance" and recommend flat-start defaults. JuMP-level `set_start_value` also available via `pm.model`. |
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
4. GitHub API: `https://api.github.com/repos/lanl-ansi/PowerModels.jl/releases` — release dates confirmed (v0.21.5 = 2025-08-12, verified 2026-03-13)
5. GitHub raw: `https://raw.githubusercontent.com/lanl-ansi/PowerModels.jl/master/CHANGELOG.md` — full changelog text
6. `https://lanl-ansi.github.io/PowerModels.jl/stable/specifications/` — problem specification docs (PF, OPF, OPB, OTS, TNEP)
7. `https://lanl-ansi.github.io/PowerModels.jl/stable/basic-data-utilities/` — PTDF, admittance, incidence, Jacobian matrix functions
8. `https://lanl-ansi.github.io/PowerModels.jl/stable/multi-networks/` — multi-network (time series) API via `replicate()`
9. `https://lanl-ansi.github.io/PowerModels.jl/stable/parser/` — supported data formats (MATPOWER .m, PSS/E .raw v33, JSON)
10. `https://lanl-ansi.github.io/PowerModels.jl/stable/utilities/` — OBBT, lazy flow limits, PTDF cut solvers
11. GitHub API: `https://api.github.com/repos/lanl-ansi/PowerModels.jl/contents/src/prob` — source file listing confirming problem types
12. `https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/` — network formulation types (ACPPowerModel, DCPPowerModel, IVRPowerModel, SOC/QC relaxations)
13. `https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl` — extension package for SCOPF/contingency analysis (separate from core PowerModels)
14. Devcontainer `julia --project=. -e 'using Pkg; Pkg.status()'` — runtime version verification (2026-03-13)
15. `https://lanl-ansi.github.io/PowerModels.jl/stable/power-flow/` — power flow docs, warm start documentation (`set_ac_pf_start_values!`, `*_start` data keys)
16. `https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/` — full formulation type catalog (ACP, ACR, ACT, IVR, DCP, DCMP, BFA, NFA, DCPLL, LPACC, SOCWR, QCR, QCLS, SOCBF, SDPWRM)
17. GitHub API: `https://api.github.com/repos/lanl-ansi/PowerModels.jl/commits` — unreleased master commits verified (2026-03-24): only CI bumps and JSON@1 update since v0.21.5

## Gaps and Uncertainties

- **Warm start**: PowerModels documents `set_ac_pf_start_values!` and `*_start` data keys for warm starting, but the docs explicitly warn it is "a very delicate task and can easily result in degraded performance." Whether the evaluation protocol's warm-start tests require robust, solver-agnostic warm starting (which PowerModels discourages) or merely the ability to set initial values (which is supported) needs clarification.
- **Parallel computation**: Solver-level parallelism (HiGHS threads) is available via `set_optimizer_attribute`, but PowerModels-level parallelism is undocumented. The degree to which this satisfies Suite D tests is unclear.
- **Contingency Analysis (N-1)**: The iterative cut-based solvers (`solve_opf_ptdf_branch_power_cuts`) are related but are OPF-with-violations tools, not classical N-1 contingency screening. Whether the evaluation protocol's contingency tests require classical screening or constraint-based approaches needs clarification from the test specification.
- **SCUC/SCED**: These are definitively absent from PowerModels.jl — they are not mentioned anywhere in the documentation or source tree. If Suite A tests require SCUC/SCED, they will fail.
- **CSV import**: Definitively not supported. Any Suite G test requiring CSV input will need a user-written parser or conversion step.
- **`calc_basic_ptdf_matrix` performance on large cases**: The changelog notes a performance improvement in v0.19.8, but no benchmarks are documented. Performance on large networks (e.g., case2848) is unknown without testing.
- **PSS/E v34+ format support**: Only PSS/E v33 spec is documented. Newer PSS/E format versions are not confirmed supported.

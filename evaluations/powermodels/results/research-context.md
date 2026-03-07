# PowerModels.jl — Consolidated Research Context

## Section 1: API & Formulations

PowerModels.jl v0.21.5 exports 437 symbols and provides a modular architecture decoupling problem specifications (PF, OPF, OTS, TNEP) from 18+ network formulations (AC polar/rectangular, DC, SOC, SDP, QC, LPAC, branch-flow, current-voltage).

**Key API patterns:**
- `solve_*(file_or_data, ModelType, optimizer)` — convenience solve functions
- `instantiate_model(data, ModelType, build_method)` + `optimize_model!(pm)` — advanced 2-level API
- `compute_ac_pf(data)` / `compute_dc_pf(data)` — native power flow (no JuMP overhead)
- `parse_file(path)` — auto-detects MATPOWER .m and PSS/E .raw v33

**Data model:** Nested `Dict{String,Any}` based on MATPOWER conventions. Loads/shunts separated from buses, angles in radians, all per-unit. Every component has unique `"index"`.

**Solver interface:** Via JuMP — any JuMP-compatible solver works (Ipopt for NLP, HiGHS/GLPK for LP/MIP, SCIP for MINLP). Swapped via optimizer factory argument.

**Result access:** `result["solution"]["bus"]["1"]["vm"]`, `result["solution"]["gen"]["1"]["pg"]`, etc. Duals via `setting = Dict("output" => Dict("duals" => true))`, accessible as `bus["lam_kcl_r"]` (active power LMP).

**Built-in utilities:** PTDF matrix (`calc_basic_ptdf_matrix`), susceptance/admittance/incidence matrices, Jacobian. PTDF-based OPF variant available.

**Multi-period:** `replicate(data, N)` creates multi-network data, solved via `solve_mn_opf` / `solve_mn_opf_strg` (time-coupled storage).

**NOT built-in:** SCUC/SCED, contingency analysis (SCOPF), stochastic OPF, distributed slack, LODF, full LMP decomposition.

## Section 2: Extensions & Architecture

**Three-layer architecture:**
1. `prob/` — problem specifications (what constraints/variables are needed)
2. `form/` — formulations (how they are mathematically expressed, dispatched by type)
3. `core/` — infrastructure (types, lifecycle, templates, ref building, solution handling)

~14,000 lines total. Built on InfrastructureModels.jl v0.7.8 for model lifecycle.

**Extension mechanisms (no traditional plugin system):**
1. **Type hierarchy + multiple dispatch** — subtype `AbstractPowerModel`, override constraint/variable methods
2. **`ref_extensions`** — list of functions for pre-computation hooks during model instantiation
3. **`solution_processors`** — post-solve result transformation hooks
4. **`ext` dictionary** — arbitrary per-model-instance storage (`pm.ext::Dict{Symbol,Any}`)
5. **Custom `build_method`** — compose existing or new variable/constraint/objective functions
6. **Direct JuMP model access** — `pm.model` exposes underlying `JuMP.Model` for arbitrary constraints

**Constraint template pattern:** Templates extract data from `ref` dict, pass to formulation-specific methods dispatched on abstract types. Clean separation of data access from math formulation.

**No native Graphs.jl or DataFrames.jl integration.** Graph access requires PowerModelsAnalytics.jl (LightGraphs/Graphs.jl bridge). DataFrame access requires PowerPlots.jl. The `ref` dict provides adjacency-like structures (`:arcs_from`, `:bus_arcs`, etc.) and `AdmittanceMatrix` struct provides sparse matrices.

**Proven extensibility:** 6+ downstream packages (PowerModelsDistribution, SecurityConstrained, Restoration, ACDC, ITD, Annex) demonstrate the pattern works at scale.

## Section 3: Limitations & Ecosystem

**Critical limitations for evaluation:**
- **Steady-state only** — no SCUC, SCED, unit commitment, time-series simulation
- **No distributed slack** — single-slack-bus only; generators at PQ buses crash (#989)
- **No native SCOPF** — requires PowerModelsSecurityConstrained.jl (last pushed 2024-01-19)
- **No native stochastic OPF** — requires StochasticPowerModels.jl (KU Leuven, 24 stars)
- **No LODF** — PTDF available, LODF requested in open issue #923
- **MATPOWER parsing bugs** — case21k fails (#854), several edge cases open for years

**Community:** 456 stars, 167 forks, 27 contributors, 83 open issues. LANL-led, limited external contribution. No evidence of production/operational deployment — usage entirely academic/research.

**Release cadence slowing:** 3 releases in 2024, 2 in 2025 (latest v0.21.5 on 2025-08-12), none in 2026. Still pre-1.0 after 9+ years.

**License:** BSD-3-Clause with US Government rights (DOE contract). GLPK dependency is GPL-3 (copyleft flag). HiGHS (MIT) is a suitable alternative.

**Documentation gaps:** Multiple open issues since 2017-2020 for docs improvements. Extension development guide terse. No comprehensive LMP/market workflow examples. Multi-network docs incomplete (#169).

**Julia runtime overhead:** 5-15s startup per invocation. First-solve JIT latency significant. PrecompileTools added in v0.21.4 to mitigate. REPL workflow recommended for repeated evaluations.

**Dependencies:** ~90 packages installed in evaluation environment (including solvers and JLL wrappers). Direct deps: InfrastructureModels, JSON, JuMP, NLsolve, Memento, PrecompileTools + stdlib.

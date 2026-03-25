---
tool: matpower
installed_version: "8.1"
release_date: 2025-07-12
latest_version: "8.1"
latest_release_date: 2025-07-12
research_date: 2026-03-24
---

# matpower — Version & Capability Report

## Version Summary

The evaluation environment installs MATPOWER 8.1, downloaded from the official GitHub release archive (`matpower8.1.zip`, SHA-256 verified) per `evaluations/matpower/setup.sh`. The `verify_install.m` script confirms the version string via `mpver()` and validates basic DC power flow on the IEEE 39-bus case. MATPOWER 8.1 was released on July 12, 2025, and is the latest stable release as of the research date.

MATPOWER 8.1 builds on the major architectural overhaul introduced in 8.0 (May 17, 2024), which replaced the legacy procedural internals with the object-oriented MP-Core framework. The 8.x line requires MATLAB 9.1+ or GNU Octave 6.2+ for MP-Core features; older environments fall back to legacy code paths. The evaluation devcontainer uses Octave, which is fully supported. Bundled sub-packages in 8.1 include MP-Opt-Model 5.0, MIPS 1.5.2, MP-Test 8.1, and MOST 1.3.1.

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes | 1.0 (1997) | `rundcpf()` / `run_pf()` with DC option. Core capability since initial release. |
| AC Power Flow (ACPF) | yes | 1.0 (1997) | `runpf()` / `run_pf()`. Newton-Raphson, fast-decoupled, Gauss-Seidel solvers. 8.0 added `fsolve()`-based and implicit Z-bus Gauss solvers for distribution systems. |
| DC Optimal Power Flow (DC OPF) | yes | 2.0 (1997) | `rundcopf()` / `run_opf()` with DC option. Supports piecewise-linear and polynomial cost functions. |
| AC Optimal Power Flow (AC OPF) | yes | 2.0 (1997) | `runopf()` / `run_opf()`. Interior-point (MIPS), fmincon, IPOPT, Knitro, and others via solver plugins. |
| Security-Constrained Unit Commitment (SCUC) | partial | 6.0 (2016, via MOST) | MOST solves multi-period stochastic security-constrained unit commitment with DC network constraints. AC network model formulated but current implementation limited to DC. Requires MOST sub-package (bundled as 1.3.1). |
| Security-Constrained Economic Dispatch (SCED) | partial | 6.0 (2016, via MOST) | MOST handles deterministic and stochastic economic dispatch with contingency constraints. DC-only network model in practice. Single-period ED also solvable via DC OPF with appropriate setup. |
| PTDF / Shift Factor Extraction | yes | 3.2 (2007) | `makePTDF()` builds DC PTDF matrix (nbr x nb). Supports scalar slack bus or slack distribution vector. 8.0 extended to per-bus slack distribution matrices. `makeLODF()` builds line outage distribution factors. Performance optimizations in 7.1 for large cases (70%+ speedup on pegase-9241). |
| Contingency Analysis (N-1) | partial | 3.2 (2007) | No built-in single-command N-1 screening. Users combine `makeLODF()` for fast linear screening or loop `runpf()`/`runopf()` over modified cases. `toggle_softlims` enables soft-limit relaxation for contingency-aware OPF. `connected_components()` detects islanding. |
| Custom Constraint Injection | yes | 4.0 (2011) | Legacy: `add_userfcn()` callback API adds variables, constraints, and costs to OPF formulation. 8.0+: MP-Core extension API and `mp.opt_model` class provide structured constraint injection. `toggle_softlims` is a built-in example of this pattern. |
| Network Graph Access | yes | 3.0 (2004) | `makeYbus()` (admittance), `makeBdc()` (DC B-matrices), `makeIncidence()` (bus-branch incidence), `connected_components()` (graph connectivity). Sparse Cf/Ct connection matrices available. No high-level graph object, but all adjacency/incidence data is extractable from bus/branch arrays. |
| CSV Data Import | no | — | MATPOWER natively loads `.m` (function files) and `.mat` (binary) case formats via `loadcase()`. No built-in CSV parser. Users must write custom Octave/MATLAB code to read CSV and populate the mpc struct. |
| MATPOWER Case Import | yes | 1.0 (1997) | Native format. `loadcase()` reads `.m` and `.mat` files in both version 1 (deprecated) and version 2 case formats. `savecase()` and `save2psse()` (PSS/E RAW export) also available. 8.1 adds `save2psse_rop()` for PSS/E ROP file export. |
| Multi-Period / Time Series | partial | 6.0 (2016, via MOST) | MOST provides multi-period optimal scheduling with ramping constraints, storage, deferrable demand, and stochastic scenarios. DC network model only. Core MATPOWER has no native time-series / multi-period power flow. |
| Warm Start / Solution Reuse | partial | 7.0 (2019) | `opf.start` option controls initialization (flat start, previous solution, etc.). MP-Opt-Model warm-start parameters passed to solvers when available. Effectiveness depends on the underlying solver (e.g., IPOPT, Knitro support warm starts natively). |
| Parallel Computation | no | — | No built-in parallel execution. Users can parallelize via Octave/MATLAB parallel toolboxes externally, but MATPOWER itself provides no parallel dispatch, multi-threaded solvers, or distributed computation API. |

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|----------------------|
| 8.0 | Removed deprecated functions `d2AIbr_dV2()`, `d2ASbr_dV2()` (replaced by `dA2br_dV2()`) | Low. Evaluation scripts unlikely to use second-derivative branch functions. |
| 8.0 | Removed deprecated `opf_model` methods (`add_constraints`, `add_costs`, `add_vars`, `build_cost_params`, `get_cost_params`, `getv`, `linear_constraints`) | Medium. Custom constraint tests must use the new `mp.opt_model` API or legacy `add_userfcn` callbacks. |
| 8.0 | Removed `opf.init_from_mpc` option; use `opf.start` | Low. Evaluation should use `opf.start` for warm-start tests. |
| 8.0 | Removed unused `mpopt` argument from `opf_gen_cost_fcn()` | Low. Only affects custom cost function code referencing old signature. |
| 8.0 | `loadcase()` with 5 outputs now returns `[baseMVA, bus, gen, branch, gencost]` instead of `[baseMVA, bus, gen, branch, info]` | Low. Evaluation scripts use struct output form (`mpc = loadcase(...)`). |
| 8.0 | MOST optimization failure no longer halts to debugger; adds `md.results.success` flag | Low-positive. Easier to detect MOST failures programmatically. |
| 8.0 | Requires Octave 6.2+ for MP-Core features | Low. Devcontainer provides a current Octave version. |
| 8.1 | R2025b `linprog` interior-point algorithm skipped in DC OPF tests due to failures | None. Octave does not use MATLAB's `linprog`. |

## Changelog Analysis

### Architecture (8.0)

The 8.0 release was a major rewrite. The new MP-Core introduces a three-layer architecture: data model (case data), network model (admittance/incidence matrices), and mathematical model (optimization formulation). Legacy functions (`runpf`, `runopf`, `rundcpf`, etc.) are retained and work via MP-Core internally, so existing scripts remain functional. New entry points `run_pf()`, `run_cpf()`, `run_opf()` expose the flexible framework with extension hooks.

### Solver Ecosystem (8.0-8.1)

8.0 added MP-Opt-Model 4.x with parameterized nonlinear equation solvers. 8.1 upgraded to MP-Opt-Model 5.0, adding QCQP support (Gurobi, Knitro, and NLP-based), the open-source HiGHS solver for LP/QP/MILP, and a `relax_integer` option for MILP/MIQP relaxation. Knitro 15.x and MOSEK 11.x compatibility were also added.

### Distribution System Modeling (8.0-8.1)

8.0 introduced an implicit Z-bus Gauss method for radial distribution systems and two real-world Swedish DSO test cases (case533mt). 8.1 added three-phase proof-of-concept capabilities (single-to-three-phase conversion, three-phase shunt and transformer models) and a 1197-bus radial distribution test case.

### Test Cases

8.0 added case60nordic (60-bus Nordic), case8387pegase (8387-bus PEGASE), and the Swedish DSO cases. 8.1 added case1197 (distribution), case59 (Australian network), and a Kundur 11-bus example.

### Bug Fixes (8.0-8.1)

Notable fixes include: fatal error in `int2ext()` with user callbacks (8.0), AC OPF initialization with piecewise-linear costs (8.0), radial power flow numerical errors with multiple generators (8.0), `save2psse()` fatal error with dispatchable loads (8.0/8.1), and Octave 10.x compatibility typos (8.1).

## Sources

1. [MATPOWER GitHub Releases](https://github.com/MATPOWER/matpower/releases) — version list and release notes
2. [MATPOWER All Releases](https://matpower.org/download/all-releases/) — complete release history with dates
3. [MATPOWER 8.0 Release Notes (GitHub)](https://github.com/MATPOWER/matpower/blob/master/docs/relnotes/MATPOWER-Release-Notes-8.0.md) — breaking changes and new features
4. [MATPOWER CHANGES.md (GitHub)](https://github.com/MATPOWER/matpower/blob/master/CHANGES.md) — detailed changelog
5. [MATPOWER Reference Manual 8.1 (PDF)](https://matpower.org/doc/_downloads/13f33e22ecbbad1ede2ee92dbf7e51ac/matpower_ref_manual.pdf) — function reference
6. [MATPOWER User's Manual 8.1 (PDF)](https://matpower.org/docs/MATPOWER-manual.pdf) — usage guide
7. [makePTDF documentation](https://matpower.org/doc/ref-manual/legacy/functions/makePTDF.html) — PTDF function reference
8. [makeLODF documentation](https://matpower.org/documentation/ref-manual/legacy/functions/makeLODF.html) — LODF function reference
9. [MOST GitHub README](https://github.com/MATPOWER/most/blob/master/README.md) — multi-period scheduling tool overview
10. [MOST User's Manual 1.3.1 (PDF)](https://matpower.org/docs/MOST-manual.pdf) — MOST capabilities and limitations
11. [MATPOWER Callback Functions](https://matpower.app/manual/matpower/CallbackFunctions.html) — custom constraint injection API
12. [Linear Shift Factors manual section](https://matpower.app/manual/matpower/LinearShiftFactors.html) — PTDF/LODF usage
13. [connected_components reference](https://matpower.org/docs/ref/matpower5.0/connected_components.html) — graph connectivity function
14. [toggle_softlims reference](https://matpower.org/docs/ref/matpower5.0/toggle_softlims.html) — soft limit extension for OPF
15. `evaluations/matpower/setup.sh` — installation script confirming version 8.1

## Gaps and Uncertainties

- **Exact "since version" for ACPF/DCPF solvers**: Power flow has been present since MATPOWER 1.0 (1997), but specific solver algorithms (e.g., fast-decoupled, Gauss-Seidel) were added incrementally. The version 1.0 attribution covers basic Newton-Raphson PF; detailed solver-by-solver provenance was not traced.
- **MOST DC-only limitation**: The MOST formulation supports AC network constraints in theory, but the implementation is DC-only. It is unclear whether a future release will add AC support or if this is a permanent architectural constraint.
- **SCOPF completeness**: MATPOWER does not include a turnkey SCOPF command. Users must construct SCOPF workflows using `makeLODF()`, `toggle_softlims`, and looped OPF calls. The "partial" rating for contingency analysis and SCUC/SCED reflects this user-assembly requirement.
- **Warm-start effectiveness**: The `opf.start` option and MP-Opt-Model warm-start parameters exist, but their practical effectiveness depends on the solver backend. No benchmarks were found for warm-start speedup in MATPOWER specifically.
- **Parallel computation**: While Octave supports `parfor` and `parcellfun`, MATPOWER itself does not expose parallel interfaces. It is unknown whether any internal operations use multithreaded BLAS/LAPACK via Octave's linear algebra backend.
- **CSV import**: Confirmed absent from native MATPOWER. Custom scripts are required. The third-party Python package `matpowercaseframes` can convert MATPOWER cases to/from pandas DataFrames, but this is outside the Octave evaluation scope.
- **MOST Pro**: A commercial extension (MOST Pro 1.4.1) adds features beyond the open-source MOST 1.3.1 bundled with MATPOWER 8.1. The capabilities of MOST Pro were not evaluated as it requires a paid license.

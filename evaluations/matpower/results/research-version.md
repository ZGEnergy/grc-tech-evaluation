---
tool: matpower
installed_version: "8.1"
release_date: 2025-07-12
latest_version: "8.1"
latest_release_date: 2025-07-12
research_date: 2026-03-13
---

# matpower — Version & Capability Report

## Version Summary

MATPOWER 8.1 is the latest release (July 12, 2025) and is the version installed in this evaluation environment. It was downloaded via `setup.sh` from the official GitHub release. MATPOWER 8.1 builds on the major 8.0 rewrite (May 17, 2024) that introduced the MP-Core object-oriented architecture, replacing the legacy procedural internals. The 8.1 release adds three-phase modeling utilities, MP-Opt-Model 5.0 with QCQP support and HiGHS solver integration, and includes MOST 1.3.1 for multi-period scheduling.

Since the installed version is the latest available, there are no upgrade concerns or version gaps. The evaluation can rely on all documented 8.1 features.

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes | 1.0 (1997) | `rundcpf()` — core capability since inception |
| AC Power Flow (ACPF) | yes | 1.0 (1997) | `runpf()` — Newton-Raphson, fast-decoupled, Gauss-Seidel solvers; radial PF added in 7.0 |
| DC Optimal Power Flow (DC OPF) | yes | 2.0 (1997) | `rundcopf()` — linear formulation using DC power flow model |
| AC Optimal Power Flow (AC OPF) | yes | 2.0 (1997) | `runopf()` — full nonlinear formulation; supports MIPS, IPOPT, Knitro, fmincon solvers |
| Security-Constrained Unit Commitment (SCUC) | partial | 5.0 (2014) | Via MOST 1.x — solves stochastic, security-constrained, multi-period UC with DC network constraints; AC network model not yet implemented in MOST; requires manual problem setup via `most()` function |
| Security-Constrained Economic Dispatch (SCED) | partial | 5.0 (2014) | Via MOST 1.x — supports contingency-constrained ED with DC OPF; single-period or multi-period; no turnkey SCED function, requires MOST problem specification |
| PTDF / Shift Factor Extraction | yes | 3.x (~2006) | `makePTDF()` — builds nbr x nb DC PTDF matrix; supports custom slack distribution; efficient sparse computation for specific transfers added in 7.1 |
| Contingency Analysis (N-1) | partial | 5.0 (2014) | Via MOST — contingency states modeled as separate network islands with probability weighting; no standalone `runCA()` function; users can script N-1 by iterating `runpf()`/`runopf()` with branch removals |
| Custom Constraint Injection | yes | 4.0 (2011) | MP-Opt-Model `add_lin_constraint()`, `add_nln_constraint()`, `add_quad_cost()`; 8.x Extension API allows adding custom variables, constraints, and costs to OPF via callback mechanism |
| Network Graph Access | yes | 3.x (~2006) | Bus-branch data directly accessible as matrices; `makeYbus()` for admittance matrix; `makeBdc()` for B matrices; `connected_components()` for topology analysis; no native graph object, but adjacency/incidence matrices are straightforward to construct |
| CSV Data Import | no | — | `loadcase()` supports only `.m` and `.mat` files natively; CSV requires custom parsing scripts; third-party `matpowercaseframes` (Python) can convert |
| MATPOWER Case Import | yes | 1.0 (1997) | `loadcase()` — supports `.m` (v1 and v2 formats) and `.mat` files; also imports PSS/E `.raw` files via `psse2mpc()` |
| Multi-Period / Time Series | partial | 5.0 (2014) | Via MOST — multi-period DC OPF with ramping constraints, storage, deferrable demands; no built-in time-series AC OPF; each period uses DC network model only |
| Warm Start / Solution Reuse | partial | 7.0 (2019) | `opf.start` option can initialize from a solved case (`mpc.bus(:,VM)`, `mpc.gen(:,PG)` etc.); MIPS 1.5+ supports LU factorization reuse; no formal warm-start API — user manually passes previous solution as starting point |
| Parallel Computation | no | — | No built-in parallel support; MATLAB users can wrap calls in `parfor` (requires Parallel Computing Toolbox, known issues with MATPOWER globals); GNU Octave has limited parallel packages; no native MATPOWER parallelism |

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|----------------------|
| 8.0 | Major rewrite: MP-Core replaces legacy internals; new `run_pf()`, `run_cpf()`, `run_opf()` functions alongside legacy `runpf()`, `runopf()` | Legacy functions still work via backward-compatibility wrappers; evaluation scripts using legacy API are unaffected |
| 8.0 | Deprecated `opt_model` methods removed (`add_constraints`, `add_costs`, etc.) | Must use `add_lin_constraint()`, `add_nln_constraint()`, `add_quad_cost()` etc. |
| 8.0 | `opf.init_from_mpc` option removed | Use `opf.start` option instead |
| 8.0 | Requires MATLAB 9.1+ or Octave 6.2+ | Our devcontainer uses Octave 9.x — no issue |
| 8.1 | Legacy `opt_model` and `mp_idx_manager` classes superseded by `mp.opt_model` | Legacy classes retained for backward compatibility; no immediate breakage |

## Changelog Analysis

**8.0 (May 17, 2024):** Landmark release introducing MP-Core — a three-layer object-oriented architecture (data model, network model, mathematical model) with a task management layer. Added the "flexible framework" (`run_pf`, `run_opf`, `run_cpf`) alongside the legacy framework. Introduced Extension API for customization (new element types, formulations). Added QCQP support and HiGHS solver. Improved radial power flow robustness. Broke backward compatibility on deprecated `opt_model` methods and the `opf.init_from_mpc` option.

**8.1 (July 12, 2025):** Incremental release building on 8.0. Added three-phase conversion utility and prototype three-phase models (shunt, transformer). MP-Opt-Model 5.0 with redesigned optimization classes, quadratic constraint support, HiGHS integration for LP/QP/MILP, and `relax_integer` option. New case files (`case1197`, `case59`). PSS/E ROP export. MOST updated to 1.3.1. Bug fixes for Knitro 15.x and Octave compatibility.

No breaking changes between 8.0 and 8.1 that affect this evaluation. Since 8.1 is both installed and latest, there is no version gap.

## Sources

1. [MATPOWER All Releases](https://matpower.org/download/all-releases/) — full version history and release dates
2. [MATPOWER 8.1 Launch Announcement](https://matpower.org/matpower-8-1-launch/) — 8.1 feature summary
3. [MATPOWER 8.0 Release Announcement](https://matpower.org/2024/05/17/matpower-8-0-released/) — MP-Core architecture overview
4. [What's New in MATPOWER 8](https://matpower.org/whats-new-in-matpower-8/) — detailed 8.0 feature descriptions
5. [MATPOWER CHANGES.md](https://github.com/MATPOWER/matpower/blob/master/CHANGES.md) — detailed changelog
6. [MATPOWER Reference Manual 8.1](https://matpower.org/doc/_downloads/13f33e22ecbbad1ede2ee92dbf7e51ac/matpower_ref_manual.pdf) — function reference
7. [MATPOWER User's Manual 8.1](https://matpower.org/docs/MATPOWER-manual.pdf) — user guide
8. [MOST User's Manual 1.3.1](https://matpower.org/docs/MOST-manual.pdf) — MOST capabilities and API
9. [MOST GitHub README](https://github.com/MATPOWER/most/blob/master/README.md) — MOST overview
10. [makePTDF Documentation (8.1)](https://matpower.org/doc/ref-manual/legacy/functions/makePTDF.html) — PTDF function reference
11. [How to Add an OPF Constraint (8.1)](https://matpower.org/documentation/howto/add-constraint.html) — custom constraint injection guide
12. [MP-Opt-Model GitHub](https://github.com/MATPOWER/mp-opt-model) — optimization model package
13. [connected_components Documentation](https://matpower.org/docs/ref/matpower5.0/connected_components.html) — network topology analysis
14. [MATPOWER Data File Format](https://matpower.app/manual/matpower/DataFileFormat.html) — loadcase file format specification
15. [Linear Shift Factors](https://matpower.app/manual/matpower/LinearShiftFactors.html) — PTDF/LODF theory and usage

## Gaps and Uncertainties

- **SCUC/SCED "since version" attribution:** MOST was first bundled with MATPOWER 5.0 (2014), but earlier standalone versions of MOST existed. The "since 5.0" designation reflects when it became part of the standard MATPOWER distribution.
- **Warm start specifics:** MATPOWER does not have a formal warm-start API. The `opf.start` option and manual initialization from a previous solution provide partial warm-start capability, but solver-level warm start (e.g., passing dual variables) depends on the underlying solver (IPOPT, Knitro).
- **Parallel computation on Octave:** GNU Octave's `parallel` package exists but is not equivalent to MATLAB's Parallel Computing Toolbox. MATPOWER does not use or recommend it. Users who need parallelism must implement it externally.
- **MOST AC network model:** MOST's formulation is general and supports AC, but the current implementation (through 1.3.1) only supports DC power flow network constraints. This is a long-standing limitation.
- **CSV import:** No evidence of native CSV import was found in any MATPOWER version. The `.m` case file format is the canonical input format.
- **makePTDF origin version:** The function exists in MATPOWER 4.0 documentation (2011) and likely predates it. Attributed to "3.x (~2006)" based on copyright dates in source code, but exact introduction version is uncertain.

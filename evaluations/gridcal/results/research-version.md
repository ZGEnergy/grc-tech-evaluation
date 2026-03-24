---
tool: gridcal
installed_version: 5.6.28
release_date: 2026-02-25
latest_version: 5.6.38
latest_release_date: 2026-03-18
research_date: 2026-03-24
---

# gridcal — Version & Capability Report

## Version Summary

The installed version of GridCal (rebranded as VeraGrid/VeraGridEngine since v5.4.0) is **5.6.28**, released on 2026-02-25. The latest available version on PyPI is **5.6.38**, released 2026-03-18 — 10 patch releases and 21 days behind. The 5.6.x series has seen extremely rapid iteration: between the installed version and the latest, there have been releases on 2026-03-03 (5.6.29), 03-06 (5.6.30), 03-09 (5.6.31), 03-11 (5.6.32, 5.6.33), 03-12 (5.6.34), 03-16 (5.6.35), 03-17 (5.6.36), and 03-18 (5.6.37, 5.6.38). None of these releases have tagged GitHub release notes; the GitHub commit history shows only generic "latest changes from eroots repo" merge messages, indicating development occurs in a private eRoots repository. Based on the patch-level versioning and absence of documented breaking changes, the risk of API incompatibility between 5.6.28 and 5.6.38 is low.

The project underwent a significant rebrand from "GridCal" to "VeraGrid" at version 5.4.0 (February 2025) due to trademark conflicts. The Python package was renamed from `GridCalEngine` to `VeraGridEngine`, and the import namespace changed from `GridCalEngine` to `VeraGridEngine`. The core API surface, class names, and function signatures were preserved through the rename. The evaluation uses the `veragridengine` PyPI package with `import VeraGridEngine as vge`.

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes | ~1.0 | `SolverType.Linear` provides DC approximation. Tested against all MATPOWER 8 benchmark grids. ([README](https://github.com/SanPen/VeraGrid/blob/master/README.md)) |
| AC Power Flow (ACPF) | yes | ~1.0 | Multiple solvers: Newton-Raphson, Gauss-Seidel, HELM, Fast Decoupled, Iwamoto-NR, Continuation NR, LACPF. Three-phase unbalanced power flow added in 5.x series. ([README](https://github.com/SanPen/VeraGrid/blob/master/README.md)) |
| DC Optimal Power Flow (DC OPF) | yes | ~3.0 | `SolverType.LINEAR_OPF`. MIP support via HiGHS (built-in since 4.5.0), plus SCIP/CPLEX/Gurobi/CBC through PuLP or OR-Tools frameworks. MIP auto-healing added in 5.0.2 ensures OPF simulations are always feasible. ([Changelog](https://veragrid.readthedocs.io/en/stable/rst_source/change_log.html), [OPF docs](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html)) |
| AC Optimal Power Flow (AC OPF) | yes | 5.1.0 | `SolverType.NONLINEAR_OPF` with Interior Point Solver. Three modes: standard, slacks, max injections. Enhanced in 5.1.0 with HVDC dispatch. Also offers "AC Linear OPF" mode between DC and full NL. ([GitHub release 5.1.0](https://github.com/SanPen/VeraGrid/releases/tag/5.1.0), [OPF docs](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html)) |
| Security-Constrained Unit Commitment (SCUC) | partial | ~5.0 | `OpfDispatchMode.UnitCommitment` exists with `consider_time_up_down` and `consider_ramps` options. Documentation shows multi-period 24-hour commitment examples using MIP via HiGHS. However, this is a simplified UC formulation within the OPF framework — not a full ISO-grade SCUC with all standard constraints (startup cost profiles, detailed min up/down time curves, reserve products). ([OPF docs](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html)) |
| Security-Constrained Economic Dispatch (SCED) | partial | ~5.0 | Linear OPF with `consider_contingencies` option approximates SCED functionality. No dedicated SCED solver or API. Dispatch is handled via `OpfDispatchMode.Normal` with security constraints. Quadratic cost curves with fixed/linear/quadratic coefficients supported. ([OPF docs](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html)) |
| PTDF / Shift Factor Extraction | yes | 3.6.1 (empirical), 4.0.0 (analytical) | `LinearAnalysis` driver computes PTDF and LODF matrices. Version 4.0.0 replaced empirical method with analytical PTDF/LODF (orders of magnitude faster). Time-series variant available via `LinearAnalysisTimeSeriesDriver`. Also supports VTDF (3.6.4+) and net transfer capacity calculation. ([Changelog 4.0.0](https://veragrid.readthedocs.io/en/stable/rst_source/change_log.html), [README](https://github.com/SanPen/VeraGrid/blob/master/README.md)) |
| Contingency Analysis (N-1) | yes | 3.6.1 | `ContingencyAnalysisDriver` with both power-flow and LODF-based methods. Supports contingency groups and filtering. Time-series contingency analysis also available. Contingency reports added to all OPF modes in 4.2.4. Branch contingency multiplier in 4.1.2. ([Changelog](https://veragrid.readthedocs.io/en/stable/rst_source/change_log.html), [README](https://github.com/SanPen/VeraGrid/blob/master/README.md)) |
| Custom Constraint Injection | no | — | No public API for injecting arbitrary user-defined constraints into the OPF formulation. The OPF is formulated internally using PuLP/OR-Tools but the model construction is not exposed for user modification. Flexible slack variables (load/generation shedding with cost weights) provide limited soft-constraint capability but not arbitrary linear constraints. ([OPF docs](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html)) |
| Network Graph Access | yes | ~3.0 | `MultiCircuit.build_graph()` and `MultiCircuit.plot_graph()` provide network topology as a graph. `get_topology_data()` returns topology information. Island detection via `find_islands`. Kron's reduction for network simplification. ([Modelling docs](https://veragrid.readthedocs.io/en/latest/md_source/modelling.html)) |
| CSV Data Import | no | — | No native CSV import for network data. Supports Excel import (`interpret_excel_v3`), JSON, native `.veragrid` format, and equipment catalog databases. Profile data can be loaded from Excel. ([Modelling docs](https://veragrid.readthedocs.io/en/latest/md_source/modelling.html)) |
| MATPOWER Case Import | yes | ~2.0 | `vge.open_file("case.m")` natively parses MATPOWER `.m` files. Tested against all MATPOWER 8 benchmark cases; README claims the continental USA case solves in ~1 second. Also supports PSS/e `.raw`/`.rawx` (v29-35), CGMES/CIM (2.4.15, 3.0), UCTE, DigSilent `.dgs` (partial), PSLF `.epc` (partial), and PyPSA formats. ([README](https://github.com/SanPen/VeraGrid/blob/master/README.md)) |
| Multi-Period / Time Series | yes | ~3.0 | `PowerFlowTimeSeriesDriver` and `OptimalPowerFlowTimeSeriesDriver` support temporal simulation. Time grouping (monthly, weekly, daily, hourly) for OPF time series. Battery state-of-charge tracking across periods. Clustering driver for representative period selection (4.1.0+). Results can be saved to files (4.2.0+). ([Changelog](https://veragrid.readthedocs.io/en/stable/rst_source/change_log.html), [OPF docs](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html)) |
| Warm Start / Solution Reuse | yes | ~4.0 | `PowerFlowOptions.use_stored_guess` and `initialize_with_existing_solution` flags enable warm starting from previous solutions. OPF options include `ips_init_with_pf` to initialize AC OPF from power flow solution. OPF verification workflow dispatches via linear optimization then validates with exact power flow. ([OPF docs](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html)) |
| Parallel Computation | partial | ~4.0 | Time series simulations support parallel execution via the `engine` parameter (VeraGrid, Bentayga, NewtonPA, PGM, GSLV engines). Parallel operation limited to UNIX systems due to Python multiprocessing constraints on Windows. Bentayga and NewtonPA are proprietary/commercial add-ons from eRoots. No GPU acceleration. ([README](https://github.com/SanPen/VeraGrid/blob/master/README.md)) |

### Support Semantics

- **yes** — Feature is fully supported in the installed version.
- **no** — Feature is not available.
- **partial** — Feature exists but with significant limitations. Notes column explains.

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|----------------------|
| 5.4.0 | Rebrand from GridCal to VeraGrid. Package renamed from `GridCalEngine` to `VeraGridEngine`. Import namespace changed accordingly. ([GitHub release v5.4.0](https://github.com/SanPen/VeraGrid/releases/tag/v5.4.0)) | Evaluation already uses `VeraGridEngine` — no impact. Any documentation or examples referencing `GridCalEngine` need import path updates. |
| 5.3.0 | Topology processing overhaul: consolidated ConnectivityNodes, BusBars, and Buses into unified framework. FUBM converter approach integrated. ([GitHub release v5.3.0](https://github.com/SanPen/VeraGrid/releases/tag/v5.3.0)) | May affect how bus/branch topology is accessed programmatically. Improved AC/DC convergence properties are beneficial for evaluation. |
| 5.2.0 | License changed from LGPL to MPLv2. ([GitHub release v5.2.0](https://github.com/SanPen/VeraGrid/releases/tag/v5.2.0)) | No API impact. License change relevant for supply chain evaluation dimension. |
| 5.1.0 | JSON-based file format replaced CSV for native `.gridcal` files. Sparse profile implementation changed memory layout. First production-grade ACOPF. ([GitHub release 5.1.0](https://github.com/SanPen/VeraGrid/releases/tag/5.1.0)) | No impact on MATPOWER import. ACOPF capability is a significant addition for expressiveness tests. |
| 5.0.2 | "The great split" — GridCal split into GUI package (GridCal/VeraGrid) and engine package (GridCalEngine/VeraGridEngine). API naming unified. MIP auto-healing for OPF feasibility. ([GitHub release 5.0.2](https://github.com/SanPen/VeraGrid/releases/tag/5.0.2)) | Evaluation correctly depends only on `veragridengine` (engine-only package without Qt). |
| 4.0.0 | Multi-terminal AC/DC grids. Replaced empirical PTDF with analytical PTDF/LODF (orders of magnitude faster). Outer loop controls replaced with direct integration into numerical methods. ([GitHub release v4.0](https://github.com/SanPen/VeraGrid/releases/tag/v4.0)) | Analytical PTDF is the current implementation used in evaluation. |

## Changelog Analysis

### Installed Version (5.6.28) to Latest (5.6.38)

No tagged GitHub releases exist between 5.6.20 and 5.6.38. The 10 releases from 5.6.29 to 5.6.38 span 2026-03-03 to 2026-03-18 (15 days). GitHub commit messages for this period are generic merges from the private eRoots development repository ("latest changes from eroots repo", version number bumps). Without detailed release notes, the specific changes cannot be enumerated. The rapid release cadence (10 releases in 15 days) and patch-level versioning suggest bug fixes and incremental improvements rather than feature additions.

### Key milestones in the 5.x series

**5.6.20 (2026-02-02, tagged release):** "Countless bug fixes," proper grid reduction, file format export reorganization, substation creation from electrical patterns (breaker-and-a-half, double bar). Short circuits no longer treated as variations.

**5.4.0 (2025-02-02):** Rebrand from GridCal to VeraGrid. Package rename. No functional changes.

**5.3.0 (2025-01-08):** Topology processing overhaul. FUBM integration for improved AC/DC convergence.

**5.2.0 (2024-11-11):** License change from LGPL to MPLv2.

**5.1.0 (2024-04-01):** First production-grade ACOPF with interior point solver. HVDC dispatch in OPF. Sparse profiles for memory-efficient time series.

**5.0.2 (2023-11-18):** Engine/GUI split enabling headless operation. MIP auto-healing for OPF feasibility.

### Features relevant to the 15 canonical capabilities

The 5.x series brought two major capability additions: (1) AC OPF via interior point solver (5.1.0), and (2) improved topology handling for AC/DC grids (5.3.0). All other canonical features (DCPF, ACPF, DC OPF, PTDF, contingency analysis, MATPOWER import, time series, warm start) were already present in the 4.x series and have been incrementally improved. SCUC/SCED remain partial implementations within the OPF framework. Custom constraint injection and CSV import remain unsupported as of 5.6.38.

## Sources

1. [VeraGridEngine on PyPI](https://pypi.org/project/VeraGridEngine/) — version history and release dates (confirmed 5.6.38 as latest, 2026-03-18)
2. [VeraGrid GitHub Repository](https://github.com/SanPen/VeraGrid) — source code, releases, commit history
3. [VeraGrid GitHub Releases](https://github.com/SanPen/VeraGrid/releases) — release notes for tagged versions (5.6.20 and earlier only)
4. [VeraGrid Documentation — Changelog](https://veragrid.readthedocs.io/en/stable/rst_source/change_log.html) — historical changelog (covers up to 5.0.2 only)
5. [VeraGrid Documentation — OPF](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html) — OPF capabilities, dispatch modes, solver support (v5.6.31 docs)
6. [VeraGrid Documentation — Modelling](https://veragrid.readthedocs.io/en/latest/md_source/modelling.html) — element types, file formats, topology (v5.6.31 docs)
7. [VeraGrid README](https://github.com/SanPen/VeraGrid/blob/master/README.md) — feature list, file format support, MATPOWER compatibility
8. Runtime introspection of `VeraGridEngine` 5.6.28 API via devcontainer (`importlib.metadata.version('veragridengine')`)

## Gaps and Uncertainties

- **Changelog gap for 5.6.21–5.6.38:** No tagged GitHub releases exist after 5.6.20. Versions 5.6.21 through 5.6.38 have no public release notes. Development occurs in a private eRoots repository with periodic merges to the public GitHub repo, making it impossible to track individual changes between 5.6.28 and 5.6.38.
- **SCUC/SCED depth unclear:** The `OpfDispatchMode.UnitCommitment` mode exists and the documentation shows 24-hour commitment examples, but its exact constraint set (startup cost profiles, min up/down time enforcement, reserve products, ramp rate modeling fidelity) could not be fully determined from the public API and documentation alone. Testing is needed to verify the scope of the UC formulation.
- **Custom constraint injection:** No public API was found. It may be possible to modify the PuLP/OR-Tools model objects if they are accessible through internal attributes, but this would be undocumented and fragile. The flexible slack variables (load/generation shedding with costs) provide limited soft-constraint capability but not arbitrary linear constraint injection.
- **Parallel computation scope:** The `engine` parameter suggests pluggable compute backends, but actual parallelization behavior (thread vs. process, degree of parallelism) is not documented. Bentayga and NewtonPA engines are proprietary/commercial add-ons from eRoots — their availability and capabilities are unclear for evaluation purposes.
- **"Since Version" estimates:** Many "since version" entries are approximate, based on changelog analysis and feature availability in historical documentation. Exact version provenance could not be determined for features that predate the 3.6.1 changelog entries.
- **Documentation version lag:** The latest ReadTheDocs documentation is for version 5.6.31, while the latest PyPI release is 5.6.38. The changelog on ReadTheDocs only covers up to 5.0.2. There may be undocumented capability additions in recent versions.
- **5.6.28 to 5.6.38 delta risk assessment:** The 10-release gap with no documented changes presents low but non-zero risk. All are patch-level bumps within 15 days, suggesting bug fixes. No evidence of breaking API changes, but this cannot be confirmed without source-level comparison.

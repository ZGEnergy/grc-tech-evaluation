---
tool: gridcal
installed_version: 5.6.28
release_date: 2026-02-25
latest_version: 5.6.34
latest_release_date: 2026-03-12
research_date: 2026-03-13
---

# gridcal — Version & Capability Report

## Version Summary

The installed version of GridCal (now rebranded as VeraGrid/VeraGridEngine) is **5.6.28**, released on 2026-02-25. The latest available version on PyPI is **5.6.34**, released 2026-03-12 — only 16 days and 6 patch releases behind. The 5.6.x series has seen rapid iteration with 15 releases between 2026-02-02 and 2026-03-12, primarily consisting of bug fixes and incremental improvements. There are no known breaking API changes between 5.6.28 and 5.6.34 based on available release information.

The project underwent a significant rebrand from "GridCal" to "VeraGrid" at version 5.4.0 (February 2025) due to trademark conflicts. The Python package was renamed from `GridCalEngine` to `VeraGridEngine`, and the import namespace changed from `GridCalEngine` to `VeraGridEngine`. The core API surface, class names, and function signatures were preserved through the rename. The evaluation uses the `veragridengine` PyPI package with `import VeraGridEngine as vge`.

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes | ~1.0 | `SolverType.Linear` provides DC approximation. Well-tested on all MATPOWER 8 benchmark grids. |
| AC Power Flow (ACPF) | yes | ~1.0 | Multiple solvers: Newton-Raphson, Gauss-Seidel, HELM, Fast Decoupled, Iwamoto-NR, Continuation NR, LACPF. |
| DC Optimal Power Flow (DC OPF) | yes | ~3.0 | `SolverType.LINEAR_OPF`. Supports MIP via HiGHS/SCIP/CPLEX/Gurobi/CBC through PuLP or OR-Tools frameworks. |
| AC Optimal Power Flow (AC OPF) | yes | 5.1.0 | `SolverType.NONLINEAR_OPF` with Interior Point Solver. Three modes: standard, slacks, max injections. Enhanced in 5.1.0 with HVDC dispatch. |
| Security-Constrained Unit Commitment (SCUC) | partial | ~5.0 | `OpfDispatchMode.UnitCommitment` exists with `consider_time_up_down` and `consider_ramps` options in OPF settings. However, this is a simplified UC formulation within the OPF framework — not a full ISO-grade SCUC with all standard constraints (startup costs, min up/down time profiles, etc.). |
| Security-Constrained Economic Dispatch (SCED) | partial | ~5.0 | The linear OPF with contingency consideration (`consider_contingencies` option) approximates SCED functionality. No dedicated SCED solver or API exists. Dispatch is handled via `OpfDispatchMode.Normal` with security constraints. |
| PTDF / Shift Factor Extraction | yes | 3.6.1 (empirical), 4.0.0 (analytical) | `LinearAnalysis` driver computes PTDF and LODF matrices. Version 4.0.0 replaced empirical method with analytical PTDF/LODF (orders of magnitude faster). Time-series variant available via `LinearAnalysisTimeSeriesDriver`. |
| Contingency Analysis (N-1) | yes | 3.6.1 | `ContingencyAnalysisDriver` with both power-flow and LODF-based methods. Supports contingency groups and filtering. Time-series contingency analysis also available. |
| Custom Constraint Injection | no | — | No public API for injecting arbitrary user-defined constraints into the OPF formulation. The OPF is formulated internally using PuLP/OR-Tools but the model construction is not exposed for user modification. |
| Network Graph Access | yes | ~3.0 | `MultiCircuit.build_graph()` and `MultiCircuit.plot_graph()` provide network topology as a graph. `get_topology_data()` returns topology information. Island detection via `find_islands`. |
| CSV Data Import | no | — | No native CSV import for network data. Supports Excel import (`interpret_excel_v3`), JSON, and proprietary `.gridcal` format. Profile data can be loaded from Excel. |
| MATPOWER Case Import | yes | ~2.0 | `vge.open_file("case.m")` natively parses MATPOWER `.m` files. Tested against all MATPOWER 8 benchmark cases. Also supports PSS/e `.raw`/`.rawx`, DigSilent `.dgs`, PowerWorld `.epc`, CIM/CGMES, and PyPSA formats. |
| Multi-Period / Time Series | yes | ~3.0 | `PowerFlowTimeSeriesDriver` and `OptimalPowerFlowTimeSeriesDriver` support temporal simulation. Time grouping options (monthly, weekly, daily, hourly) for OPF time series. Battery state-of-charge tracking across periods. Clustering driver available for representative period selection. |
| Warm Start / Solution Reuse | yes | ~4.0 | `PowerFlowOptions.use_stored_guess` and `initialize_with_existing_solution` flags enable warm starting from previous solutions. OPF options include `ips_init_with_pf` to initialize AC OPF from power flow solution. |
| Parallel Computation | partial | ~4.0 | Time series simulations support parallel execution via the `engine` parameter (VeraGrid, Bentayga, NewtonPA, PGM, GSLV engines). Parallel operation is limited to UNIX systems due to Python multiprocessing constraints on Windows. No GPU acceleration. |

### Support Semantics

- **yes** — Feature is fully supported in the installed version.
- **no** — Feature is not available.
- **partial** — Feature exists but with significant limitations. Notes column MUST explain.

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|----------------------|
| 5.4.0 | Rebrand from GridCal to VeraGrid. Package renamed from `GridCalEngine` to `VeraGridEngine`. Import namespace changed accordingly. | Evaluation already uses `VeraGridEngine` — no impact. Any documentation or examples referencing `GridCalEngine` need import path updates. |
| 5.3.0 | Topology processing overhaul: consolidated ConnectivityNodes, BusBars, and Buses into unified framework. FUBM converter approach integrated. | May affect how bus/branch topology is accessed programmatically. Improved AC/DC convergence properties are beneficial for evaluation. |
| 5.1.0 | JSON-based file format replaced CSV for native `.gridcal` files. Sparse profile implementation changed memory layout. | No impact on MATPOWER import. Internal file format change does not affect evaluation protocol using `.m` files. |
| 5.0.2 | "The great split" — GridCal split into GUI package (GridCal/VeraGrid) and engine package (GridCalEngine/VeraGridEngine). API naming unified. | Evaluation correctly depends only on `veragridengine` (engine-only package without Qt). |

## Changelog Analysis

The 5.6.x series (installed range) has been a period of rapid stabilization:

**Bug Fixes & Stability (5.6.20–5.6.34):** The only tagged GitHub release in this range (5.6.20) describes "countless bug fixes" and proper grid reduction functionality. Commits between 5.6.28 and 5.6.34 are unlabeled merges from the private eRoots development repository, suggesting internal bug fixes without major feature additions.

**File Format & UI (5.6.20):** File format export was reorganized from save-as menu to individual actions. Short circuits are no longer treated as variations. New substation creation capabilities from electrical patterns (breaker-and-a-half, double bar).

**Topology Improvements (5.3.0, Jan 2025):** Major improvements to topological processing and AC/DC power flow convergence via FUBM integration.

**AC OPF Maturation (5.1.0, Apr 2024):** First production-grade ACOPF with generation dispatch and HVDC. Sparse profiles reduced memory for time-series studies.

**Key themes across 5.x series:** The development trajectory shows GridCal/VeraGrid maturing from a primarily linear/DC analysis tool into one with nonlinear OPF capabilities, improved interoperability (CGMES, CIM), and enterprise-grade topology handling. The engine/GUI split in 5.0 enabled headless/programmatic use suitable for evaluation.

## Sources

1. [VeraGridEngine on PyPI](https://pypi.org/project/VeraGridEngine/) — version history and release dates
2. [VeraGrid GitHub Repository](https://github.com/SanPen/VeraGrid) — source code, releases, commit history
3. [VeraGrid Documentation — Changelog](https://veragrid.readthedocs.io/en/stable/rst_source/change_log.html) — historical changelog (covers up to 5.0.2)
4. [VeraGrid GitHub Releases](https://github.com/SanPen/VeraGrid/releases) — release notes for tagged versions
5. [GridCal Documentation — PTDF Theory](https://gridcal.readthedocs.io/en/latest/rst_source/theory/linear/ptdf.html) — PTDF implementation details
6. [VeraGrid README](https://github.com/SanPen/VeraGrid/blob/master/README.md) — feature list and file format support
7. Runtime introspection of `VeraGridEngine` 5.6.28 API (enumerations, class signatures, options objects)

## Gaps and Uncertainties

- **Changelog gap for 5.1–5.6:** The official changelog on ReadTheDocs only covers up to version 5.0.2. Versions 5.1 through 5.6 have no detailed public changelog. Development occurs in a private eRoots repository with periodic merges to the public GitHub repo, making it difficult to track individual changes.
- **SCUC/SCED depth unclear:** The `OpfDispatchMode.UnitCommitment` mode exists but its exact constraint set (startup costs, min up/down time enforcement, reserve requirements) could not be fully determined from the public API alone. Testing is needed to verify the scope of the UC formulation.
- **Custom constraint injection:** No public API was found, but it may be possible to modify the PuLP/OR-Tools model objects if they are accessible through internal attributes. This would be undocumented and fragile.
- **Parallel computation scope:** The `engine` parameter suggests pluggable compute backends, but the actual parallelization behavior (thread vs. process, degree of parallelism) is not documented. The Bentayga and NewtonPA engines may provide additional parallel capabilities but are proprietary/commercial add-ons.
- **"Since Version" estimates:** Many "since version" entries are approximate, based on changelog analysis and feature availability in historical documentation. Exact version provenance could not be determined for features that predate the 3.6.1 changelog entries.
- **5.6.28 to 5.6.34 delta:** The specific changes between the installed version (5.6.28) and latest (5.6.34) could not be determined — commits are unlabeled merges from the private eRoots repo. Risk of breaking changes is low given the patch-level versioning.

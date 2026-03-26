---
tool: pandapower
installed_version: 3.4.0
release_date: 2026-02-09
latest_version: 3.4.0
latest_release_date: 2026-02-09
research_date: 2026-03-24
---

# pandapower — Version & Capability Report

## Version Summary

The installed version of pandapower is **3.4.0**, released on 2026-02-09. This is the latest available version on PyPI, so no version gap exists. The installation includes the `[performance]` extra (numba 0.64.0, lightsim2grid 0.12.2), along with `matpowercaseframes` and `pyomo` as additional project dependencies.

pandapower 3.4.0 sits atop a major version 3 lineage that began with 3.0.0 on 2025-03-06. The 3.x series introduced hybrid AC/DC power flow, VSC elements, DC buses and lines, CGMES v3.0 support, and migrated from setup.py to pyproject.toml. It also dropped Python 3.8 support and removed legacy geodata tables in favor of GeoJSON-based `geo` columns.

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes | 1.x | `pp.rundcpp()` — linearized DC power flow |
| AC Power Flow (ACPF) | yes | 1.x | `pp.runpp()` — Newton-Raphson, with lightsim2grid and power-grid-model backends; also supports 3-phase unbalanced via `runpp_3ph()` |
| DC Optimal Power Flow (DC OPF) | yes | 1.x | `pp.rundcopp()` — uses PYPOWER backend |
| AC Optimal Power Flow (AC OPF) | yes | 1.x | `pp.runopp()` — uses PYPOWER backend; PandaModels.jl available as optional Julia-based solver |
| Security-Constrained Unit Commitment (SCUC) | no | — | No unit commitment formulation. pandapower is a steady-state network analysis tool, not a market/scheduling tool. |
| Security-Constrained Economic Dispatch (SCED) | no | — | No security-constrained economic dispatch. OPF does not model N-1 security constraints in the optimization. |
| PTDF / Shift Factor Extraction | yes | 1.x | `pandapower.pypower.makePTDF.makePTDF()` — computes Power Transfer Distribution Factors from the DC model |
| Contingency Analysis (N-1) | yes | 2.x | `pandapower.contingency.run_contingency()` for standard N-1; `run_contingency_ls2g()` for accelerated analysis via lightsim2grid |
| Custom Constraint Injection | partial | 1.x | OPF supports predefined constraint types (bus voltage limits, branch loading limits, generator P/Q limits) but does NOT support arbitrary user-defined constraints in the PYPOWER OPF. Users would need to build a custom Pyomo model or use PandaModels.jl for fully custom constraints. |
| Network Graph Access | yes | 1.x | `pandapower.topology.create_nxgraph()` — full NetworkX graph representation with specialized power-system search algorithms |
| CSV Data Import | no | — | No native CSV import. File I/O supports JSON, Excel, pickle, and SQL. Users must manually construct DataFrames from CSV and populate the pandapower network. |
| MATPOWER Case Import | yes | 1.x | `pandapower.converter.matpower.from_mpc.from_mpc()` reads .m files; `pandapower.converter.pypower.from_ppc.from_ppc()` converts PYPOWER case dicts; `matpowercaseframes` package also available |
| Multi-Period / Time Series | yes | 2.x | `pandapower.timeseries.run_timeseries()` — controller-based loop over time steps with DataSource and OutputWriter infrastructure |
| Warm Start / Solution Reuse | yes | 1.x | `init="results"` parameter in `runpp()` and `runopp()` reuses the previous solution as starting point |
| Parallel Computation | partial | 2.x | No built-in parallel power flow dispatcher. Acceleration via numba JIT compilation (makeYbus, etc.) and lightsim2grid C++ backend. Users can parallelize time-series runs externally (e.g., multiprocessing). |

### Canonical Feature-Suite Mapping

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
- **partial** — Feature exists but with significant limitations. When `partial` is used, the Notes column MUST explain what is limited.
- **Since Version** — The version that introduced the feature. Set to `unknown` if the changelog does not provide this information.

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|----------------------|
| 3.4.0 | Station Controller `voltage_ctrl` renamed to `control_modus` (bool to enum) | No impact on evaluation suites (controller internals). |
| 3.3.0 | Removed deprecated functions: `get_connected_lines`, `get_connected_switches`, `connected_bus_in_line`, `get_line_path` | Topology operations must use current API names. Suite C graph tests unaffected if using `create_nxgraph`. |
| 3.3.0 | Removed general imports; reorganized `create.py` into modular files | Import paths changed but backwards-compatible. No evaluation impact. |
| 3.3.0 | Renamed `q_capability_curve_characteristic` to `q_capability_characteristic` | No direct evaluation impact (reactive capability curve feature). |
| 3.0.0 | Removed Python 3.8 support | No impact; evaluation uses Python 3.12. |
| 3.0.0 | Removed `vk_percent_characteristic`, `vkr_percent_characteristic` from trafo; removed `tap_phase_shifter` from `net.trafo` | Transformer modeling changes. Could affect Suite A/G if tests used old characteristic parameters. |
| 3.0.0 | TrafoController parameter rename: `trafotable`/`trafotype` to `element`; `tid` to `element_index` | Controller API change. No evaluation impact unless controller tests use old names. |
| 3.0.0 | Removed `bus_geodata` and `line_geodata` tables; replaced with `geo` column (GeoJSON) | Plotting/geodata changes. No power flow or OPF impact. |
| 3.0.0 | Changed `from "inductive"/"ind"` to `"underexcited"` and `"capacitive"/"cap"` to `"overexcited"` | Reactive power terminology change. Could affect OPF constraint setup. |

## Changelog Analysis

### 3.0.0 (2025-03-06) — Major Release

The 3.0 release was the most significant in the evaluation-relevant period. Key themes:

- **Hybrid AC/DC Power Flow**: Added VSC elements, DC buses, DC lines, and a unified AC/DC power flow solver. This extends expressiveness for modern grid topologies.
- **New Controllers**: DERController, discrete shunt controller, station controller with voltage and reactive power control, DISCrete tap control with hunting detection.
- **Converter Expansion**: CGMES v3.0 reading, JAO European EHV grid converter, PowerFactory converter enhancements.
- **State Estimation**: AF-WLS estimator for non-observable grids, shunt estimation results.
- **Infrastructure**: Migration to pyproject.toml, removed setup.py.

### 3.1.x (2025-05-26 to 2025-06-16) — State Estimation Focus

- State estimation RAM and speed optimizations with sparse matrices.
- Iteration count output for convergence monitoring.
- Reactive capability curve support for generators and static generators.
- Multiple zero injection measurement creation options.

### 3.2.x (2025-10-08 to 2025-10-27) — DC Elements and Controllers

- Back2Back VSC converter with tests.
- Load_dc and Source_dc for DC loads and generators.
- DMR controller for metallic return line current.
- Station Controller with droop control.
- Python 3.13 support.
- Plotly switched from mapbox to maplibre.

### 3.3.x (2025-12-15 to 2026-01-14) — Modularization

- Julia implementation now using juliacall (relevant for PandaModels.jl integration).
- Static Var Compensator with Voltage Control.
- Separate per-phase MVA attributes for three-phase modeling.
- Removed deprecated topology functions.
- scipy version pinned to <1.16 for Python 3.10 compatibility.

### 3.4.0 (2026-02-09) — Current Release

- `enforce_p_lims` optional argument for considering generator/sgen active power limits in power flow.
- DC elements added to DC power flow.
- Python 3.14 support in test pipeline.
- Removed extra dependencies from "all" set; added "dev" set.

### Themes Relevant to Evaluation Suites

- **Suite A (Power Flow / OPF)**: Core ACPF and DCPF stable throughout. OPF via PYPOWER unchanged. No SCUC/SCED introduced.
- **Suite B (PTDF / Contingency / Time Series)**: PTDF via makePTDF unchanged. Contingency analysis stable with lightsim2grid acceleration. Time series stable.
- **Suite C (Custom Constraints / Graph)**: NetworkX graph access stable. Custom constraint injection remains limited to predefined OPF constraint types.
- **Suite D (Warm Start / Parallel)**: `init="results"` warm start unchanged. No new parallel computation features. numba and lightsim2grid provide single-run acceleration.
- **Suite G (Data Import)**: MATPOWER converter stable. No CSV import added. CGMES v3.0 and JAO converters added in 3.0.

## Sources

1. PyPI pandapower page: <https://pypi.org/project/pandapower/>
2. GitHub CHANGELOG.rst: <https://github.com/e2nIEE/pandapower/blob/develop/CHANGELOG.rst>
3. pandapower documentation — Power Flow: <https://pandapower.readthedocs.io/en/latest/powerflow.html>
4. pandapower documentation — OPF: <https://pandapower.readthedocs.io/en/latest/opf.html>
5. pandapower documentation — OPF Formulation: <https://pandapower.readthedocs.io/en/latest/opf/formulation.html>
6. pandapower documentation — Contingency: <https://pandapower.readthedocs.io/en/latest/contingency.html>
7. pandapower documentation — Time Series: <https://pandapower.readthedocs.io/en/latest/timeseries.html>
8. pandapower documentation — Topology: <https://pandapower.readthedocs.io/en/latest/topology.html>
9. pandapower documentation — File I/O: <https://pandapower.readthedocs.io/en/latest/file_io.html>
10. pandapower documentation — Converters: <https://pandapower.readthedocs.io/en/latest/converter.html>
11. Runtime introspection of installed pandapower 3.4.0 in devcontainer

## Gaps and Uncertainties

- **"Since Version" precision**: Most features predate the 3.x changelog window. Features marked as "1.x" or "2.x" are based on their presence in early documentation and the fact that they were not listed as new in the 3.x changelog. Exact introduction versions would require reviewing the full pre-3.0 changelog.
- **PandaModels.jl custom constraints**: pandapower can delegate OPF to PandaModels.jl (Julia), which supports custom constraints via JuMP. However, `pandamodels` is not installed in the current environment, so this path is untested. The 3.3.0 changelog notes migration to `juliacall` for Julia integration.
- **Parallel computation**: pandapower does not document a built-in parallel dispatcher for running multiple independent power flows concurrently. The `run_timeseries` function is sequential. External parallelism (e.g., Python multiprocessing) is possible but not provided by pandapower itself.
- **CSV import**: While pandapower has no dedicated CSV reader, pandas DataFrames are the internal data structure, so CSV-to-DataFrame-to-pandapower is straightforward. Whether this counts as "supported" depends on evaluation rubric interpretation.
- **SCED/SCUC**: These are fundamentally market/scheduling formulations. pandapower's OPF minimizes generation cost subject to network constraints but does not model unit commitment (binary on/off decisions), startup/shutdown costs, ramp rates, or N-1 security within the optimization. This is a design scope limitation, not a missing feature.
- **3.3.3 and 3.2.2 patch releases**: PyPI shows release dates of 2026-03-13 for both 3.3.3 and 3.2.2, which postdate the 3.4.0 release (2026-02-09). These appear to be backport patches to older release branches. Their changelogs were not individually fetched but are likely bug-fix-only releases.

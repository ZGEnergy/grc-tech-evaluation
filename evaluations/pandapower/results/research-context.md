# pandapower — Research Context (Combined)

**Tool:** pandapower v3.4.0 | **Date:** 2026-03-06 | **Contract:** FA714626C0006

---

# Part 1: API & Formulations

## Key Findings

- pandapower represents networks as a `pandapowerNet` object (subclass of dict) containing ~30+ pandas DataFrames -- one per element type (bus, line, gen, load, trafo, etc.) plus corresponding `res_*` result tables.
- Supports AC power flow (`pp.runpp`) with 6 solver algorithms: Newton-Raphson, Iwamoto NR, backward/forward sweep, Gauss-Seidel, and two fast-decoupled variants. DC power flow via `pp.rundcpp`.
- AC OPF (`pp.runopp`) and DC OPF (`pp.rundcopp`) use PYPOWER's interior point method internally. OPF results include **LMPs** directly in `net.res_bus.lam_p` and `net.res_bus.lam_q`.
- Extensive PowerModels.jl interface (`pp.runpm*`) supports 13+ functions including AC/DC OPF, optimal transmission switching (OTS), transmission network expansion planning (TNEP), storage OPF, and various relaxations (SDP, SOC, QC formulations).
- **No native SCUC or SCED.** pandapower has no unit commitment formulation -- it is a steady-state power flow and OPF tool, not a production cost model.
- Contingency analysis via `pandapower.contingency.run_contingency()` supports N-1 analysis with optional lightsim2grid acceleration, but no built-in SCOPF optimizer.
- Distributed slack is supported via `slack_weight` parameters on `ext_grid` and `gen` elements, enabled with `distributed_slack=True` in `runpp`.
- Cost functions support both polynomial (`create_poly_cost` with up to quadratic terms) and piecewise-linear (`create_pwl_cost`) formulations for active and reactive power.
- I/O formats: JSON (native), Excel, pickle, SQLite, PostgreSQL, MATPOWER `.m`/`.mat` import/export, and dict-of-DataFrames.

## Formulation Coverage

| Problem | Supported | Entry Point | Solver |
|---------|-----------|-------------|--------|
| AC Power Flow (balanced) | Yes | `pp.runpp()` | NR/Iwamoto/BFSW/GS/FD, lightsim2grid |
| DC Power Flow | Yes | `pp.rundcpp()` | Linear solve (PYPOWER) |
| AC OPF | Yes | `pp.runopp()` or `pp.runpm_ac_opf()` | Interior point (PYPOWER) or Ipopt (PowerModels.jl) |
| DC OPF | Yes | `pp.rundcopp()` or `pp.runpm_dc_opf()` | Interior point (PYPOWER) or Ipopt (PowerModels.jl) |
| OPF with relaxations (SOC, SDP, QC) | Yes (via PowerModels.jl) | `pp.runpm(pm_model=...)` | Ipopt, MOSEK, SCS |
| Optimal Transmission Switching | Yes (via PowerModels.jl) | `pp.runpm_ots()` | Juniper (MINLP) |
| Contingency Analysis (N-1) | Yes | `contingency.run_contingency()` | Sequential PF |
| Security-Constrained OPF (SCOPF) | **No** | -- | -- |
| Unit Commitment (SCUC) | **No** | -- | -- |
| Economic Dispatch (SCED) | **No** | -- | -- |
| State Estimation | Yes | `estimation.estimate()` | WLS variants, LP |
| Short-Circuit (IEC 60909) | Yes | `shortcircuit.calc_sc()` | Analytical |

## Key API Entry Points

- **ACPF**: `pp.runpp(net, algorithm='nr', distributed_slack=False)`
- **DCPF**: `pp.rundcpp(net)`
- **AC OPF**: `pp.runopp(net)` — results in `net.res_bus.lam_p`
- **DC OPF**: `pp.rundcopp(net)` — results in `net.res_bus.lam_p`
- **Contingency**: `pandapower.contingency.run_contingency(net, nminus1_cases)`
- **Timeseries**: `pandapower.timeseries.run_timeseries(net, time_steps)`
- **MATPOWER import**: `pandapower.converter.matpower.from_mpc.from_mpc(mpc_file, f_hz=60)`
- **NetworkX graph**: `pandapower.topology.create_nxgraph(net)`

---

# Part 2: Extensions & Architecture

## Key Findings

- pandapower's core data structure (`pandapowerNet`) is a dict-of-DataFrames, making it trivially interoperable with pandas.
- The controller framework (`BasicCtrl` / `Controller` base classes) provides the primary extension mechanism: users subclass `Controller` and override lifecycle hooks (`time_step`, `initialize_control`, `control_step`, `is_converged`, `finalize_control`, `finalize_step`, `repair_control`).
- NetworkX graph conversion is first-class via `pandapower.topology.create_nxgraph()`, returning a `nx.MultiGraph` with bus nodes and branch edges.
- The inherited PYPOWER `userfcn` callback system provides five hook stages for the OPF pipeline: `ext2int`, `formulation`, `int2ext`, `printpf`, `savecase`. Custom linear constraints can be added to the OPF model via `opf_model.add_constraints()`.
- The internal architecture follows a two-layer pattern: user-facing pandas DataFrames converted to MATPOWER-style numpy arrays (`ppc`/`ppci`) for computation.
- PTDF, LODF, and OTDF matrices are available via `pandapower.pypower.makePTDF` and `pandapower.pypower.makeLODF`, operating on internal `ppc` arrays.
- Julia/PowerModels.jl integration via `runpm()` with a `pp_to_pm_callback` parameter for injecting custom data.
- There is **no formal plugin registry** or plugin discovery mechanism. Extension is via subclassing, monkey-patching, or callback parameters.
- **No custom element creation API** — adding new element types requires modifying internals.

## Internal Architecture

Two-layer conversion pipeline:
```
pandapowerNet -> _pd2ppc() -> ppc (full) -> _ppc2ppci() -> ppci (in-service only) -> solver -> results back to net.res_*
```

Key internal data accessible after `runpp()`:
- `net._ppc` — full MATPOWER-format dict with `bus`, `gen`, `branch`, `baseMVA`, `internal`
- `net._ppc['internal']` — contains `Ybus`, `Yf`, `Yt`, `V`, `J` (Jacobian), `Sbus`, `ref`, `pv`, `pq`
- `net._pd2ppc_lookups` — mapping from pandapower indices to ppc indices

## PTDF/LODF

- `makePTDF(baseMVA, bus, branch, slack)` — DC PTDF matrix (nbr x nb), supports sparse solvers and distributed slack
- `makeLODF(branch, PTDF)` — Line Outage Distribution Factor matrix (nbr x nbr)
- `makeOTDF(PTDF, LODF, outage_branches)` — Outage Transfer Distribution Factor matrix
- Requires converting pandapower net to ppc format first

## Custom OPF Constraints

Via PYPOWER `userfcn` system at the `formulation` stage:
- `opf_model.add_constraints(name, A, l, u, varsets)` for linear constraints `l <= A * x <= u`
- Operates at PYPOWER level (numpy arrays), not pandapower level (DataFrames)
- Users must understand internal ppc indexing

---

# Part 3: Limitations & Ecosystem

## Key Findings

- **No built-in SCUC, SCOPF, or stochastic OPF.** Tests A-5, A-6, A-8, A-9 will require significant workarounds or external formulation.
- **OPF convergence is a documented weakness.** The developers themselves describe their PYPOWER OPF support as "minimal."
- **LMP / dual value extraction is not straightforward.** pandapower exposes `net.res_bus.lam_p` after OPF but LMP decomposition is entirely manual.
- **PTDF/LODF functions exist but are not natively exposed** in the pandapower API surface.
- **Distributed slack is supported** via `distributed_slack=True` but has reported behavioral inconsistencies.
- **N-1 contingency analysis is supported** with native and lightsim2grid-accelerated variants, but no SCOPF exists.
- **No PSS/E RAW import.**
- **Active development**: 10 releases in 12 months, latest v3.4.0 (Feb 2026).
- **Primarily academic/research tool.** Backed by University of Kassel and Fraunhofer IEE. ~1,100 GitHub stars, ~90 contributors.
- **BSD 3-Clause license.** All dependencies permissively licensed.

## Release History (Last 12 Months)

| Version | Date | Highlights |
|---------|------|------------|
| 3.4.0 | 2026-02-09 | `enforce_p_lims`, DC elements in DCPF, Python 3.14 support |
| 3.3.0 | 2025-12-16 | SVC control, CIM v3.0, juliacall migration |
| 3.2.0 | 2025-10-08 | Parallel contingency analysis (multiprocessing) |
| 3.1.0 | 2025-05-26 | Q capability curves, allocation factor WLS estimator |
| 3.0.0 | 2025-03-06 | **Major breaking release**: MW/MVAr units, sign convention changes |

## Ecosystem

| Package | Stars | Description |
|---------|-------|-------------|
| pandapower | 1,113 | Power system modeling & analysis |
| pandapipes | 209 | Pipe network simulation |
| simbench | 129 | Benchmark network datasets |
| pandahub | 15 | MongoDB data hub |
| PandaModels.jl | 13 | Julia/PowerModels.jl bridge |

## Community & Adoption

- ~1,100 stars, ~550 forks, ~90 contributors, ~10,700 commits
- ~3,600 weekly PyPI downloads, 487 dependent projects
- No evidence of ISO/RTO production use or North American utility deployment
- Academic/research focus: European distribution grid studies

## Critical Gaps for Evaluation

| Test | Issue | Severity |
|------|-------|----------|
| A-5 (SCUC) | No unit commitment | Major — likely fail |
| A-6 (SCED) | Depends on A-5 | Major — likely fail |
| A-8 (Stochastic OPF) | No native stochastic formulation | Major — external workaround needed |
| A-9 (SCOPF) | No security-constrained OPF | Major — manual constraint enumeration via B-1 |
| A-10 (Lossy DC OPF) | LMP decomposition not provided | Moderate — manual extraction |
| A-11 (Distributed slack OPF) | Distributed slack in PF only, not OPF | Moderate — needs verification |
| C-3/C-7 (Solver swap) | PYPOWER uses internal solver, not HiGHS/GLPK | Moderate — PowerModels.jl may be needed |

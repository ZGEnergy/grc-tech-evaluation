# gridcal — Research: Limitations & Ecosystem

## Key Findings

- **Rebranding in progress:** GridCal was renamed to VeraGrid in Feb 2026 after a trademark dispute. The PyPI package is now `veragridengine` (engine-only) and `veragrid` (with GUI). The Python import is `VeraGridEngine`. Documentation, URLs, and community references are fragmented across both names.
- **Single-maintainer project:** 30 contributors total, but one developer (SanPen / Santiago Penate Vera) accounts for ~87% of all commits (9,523 of ~10,900+). Bus factor is effectively 1.
- **ACOPF has known bugs:** Open issues #430 (ACOPF crashes with non-dispatchable generators) and #397 (OPF not fulfilling ramp/time-up-down constraints, load shedding not controllable). These directly affect evaluation Suite C tests.
- **Linear OPF is the default and primary OPF:** The `SolverType.LINEAR_OPF` (DC-OPF) is the default. The nonlinear ACOPF uses an interior-point solver (IPS) implemented in-house, not a mature NLP solver like Ipopt.
- **No external NLP solver integration for ACOPF:** Unlike pandapower (which wraps Pyomo/Ipopt), GridCal's ACOPF is a custom Newton-Raphson IPS implementation. This limits solver maturity for AC OPF.
- **Heavy dependency footprint:** 62 transitive dependencies including opencv-python, pvlib, windpowerlib, pymoo — many unrelated to core power flow. The package bundles renewable energy modeling, computer vision, and evolutionary optimization.
- **Documentation is sparse and broken:** The GitHub wiki pages return loading errors. The old gridcal.org is under construction. ReadTheDocs at veragrid.readthedocs.io exists but many internal links 404. No standalone API reference tutorial beyond auto-generated docs.
- **Proprietary engine layer (GSLV):** The codebase includes hooks for a proprietary C++ engine (`pygslv`) requiring a license. This is the commercial product from eRoots Analytics. The open-source engine is pure Python + NumPy/SciPy/Numba.
- **Small community:** ~516 GitHub stars, 123 forks, 29 open issues, 4 GitHub Discussions. No StackOverflow tag. No third-party ecosystem packages. PyPI downloads: ~200k (gridcalengine, lifetime) + ~23k (veragridengine, since Dec 2025).
- **Active development cadence:** Very frequent releases (5.6.0 through 5.6.34 between Feb-Mar 2026 alone), but no changelogs beyond version-number commit messages. CI is limited to a single pylint workflow.

## Detailed Notes

### Rebranding: GridCal to VeraGrid

In February 2026 (release v5.4.0, tagged "Last GridCal"), the project was renamed due to a trademark dispute. Per the release notes: "Because a company registered the GridCal name, we have been forced to rename the project... under the EU law, there is very little that an open source project can do against a trademark." The community voted on the new name "VeraGrid."

**Impact on evaluation:**
- PyPI package: `gridcalengine` (frozen at 5.4.1) → `veragridengine` (active, 5.6.x)
- Import: `GridCalEngine` → `VeraGridEngine`
- All existing tutorials, StackOverflow answers, blog posts reference the old name
- The gridcal.org domain shows "under construction"

Sources:
- [v5.4.0 release notes](https://github.com/SanPen/GridCal/releases/tag/v5.4.0)
- [PyPI veragridengine](https://pypi.org/project/veragridengine/)
- [PyPI gridcalengine](https://pypi.org/project/gridcalengine/)

### Known Limitations: OPF

**Issue #397 — OPF not fulfilling constraints (open, reported Jun 2025):**
Ramp-up/ramp-down constraints and minimum-up/minimum-down time constraints are not enforced correctly. Load shedding cannot be fully disabled even with very high load cost. Reported on v5.3.14. No fix as of Mar 2026.
- [GitHub Issue #397](https://github.com/SanPen/GridCal/issues/397)

**Issue #430 — ACOPF crashes with non-dispatchable generators (open):**
Running ACOPF with `enabled_dispatch=False` generators causes the solver to crash when flushing results. The results object cannot handle non-dispatchable generator outputs.
- [GitHub Issue #430](https://github.com/SanPen/GridCal/issues/430)

**Issue #421 — ACOPF bug with NY grid (closed):**
Indicates ACOPF had issues on larger realistic grids.
- [GitHub Issue #421](https://github.com/SanPen/GridCal/issues/421)

**Issue #423 — Power flow prior to ACOPF causes size mismatch (closed):**
Running power flow before ACOPF caused matrix size mismatch in f and J.
- [GitHub Issue #423](https://github.com/SanPen/GridCal/issues/423)

**OPF solver architecture:**
- Default: `SolverType.LINEAR_OPF` — DC-OPF using PTDF-based LP formulation via PuLP or OR-Tools with HiGHS solver
- Alternative: `SolverType.NONLINEAR_OPF` — Custom interior-point solver (IPS) implementation
- MIP solvers supported: HiGHS (default/bundled), SCIP, CPLEX, Gurobi, Xpress, CBC, PDLP
- MIP frameworks: PuLP (default), OR-Tools
- No integration with Pyomo, JuMP, or established NLP solvers (Ipopt, KNITRO)

Source: `VeraGridEngine/Simulations/OPF/opf_options.py` (installed package)

### Known Limitations: Short Circuit

**Issue #426 — Broken mid-line fault short circuit (open):**
The `split_branch()` function references non-existent properties (`branch.G`, `bus.Zf`), making mid-line fault calculations fail entirely. A fix was proposed in the issue but not merged.
- [GitHub Issue #426](https://github.com/SanPen/GridCal/issues/426)

### Known Limitations: File Format Support

**Issue #414 — PSS/E exporting broken (open):**
PSS/E (RAW) export is not functional.
- [GitHub Issue #414](https://github.com/SanPen/GridCal/issues/414)

**Issue #337 — PSS/E transformer import issues (open):**
Problems reading transformer data from PSS/E format files.
- [GitHub Issue #337](https://github.com/SanPen/GridCal/issues/337)

**Issue #458 — CIM import issues (open):**
UK DNO CIM files cannot be imported.
- [GitHub Issue #458](https://github.com/SanPen/GridCal/issues/458)

**Supported formats (from IO directory):** MATPOWER (.m), CIM/CGMES (XML/RDF), PSS/E RAW, DGS, EPC, IIDM, UCTE, native .gridcal/.veragrid (JSON-based)

### Known Limitations: Contingency Analysis

**Issue #413 — Linear contingency formulation needs review (open):**
The function `add_linear_branches_contingencies_formulation` has been flagged for review.
- [GitHub Issue #413](https://github.com/SanPen/GridCal/issues/413)

**Issue #364 — SCOPF with numerical circuit (open):**
Running Security-Constrained OPF with the numerical circuit representation is an open feature request.
- [GitHub Issue #364](https://github.com/SanPen/GridCal/issues/364)

### Dependency Tree

62 transitive packages installed. Notable dependencies:

| Dependency | Purpose | License |
|---|---|---|
| numpy, scipy, pandas | Core numerical | BSD |
| numba, llvmlite | JIT compilation for performance | BSD |
| highspy | HiGHS MIP/LP solver | MIT |
| pulp | MIP modeling framework | BSD |
| networkx | Graph algorithms | BSD |
| matplotlib | Plotting | PSF |
| opencv-python | Computer vision (map/diagram?) | Apache 2.0 |
| pvlib | Photovoltaic modeling | BSD |
| windpowerlib | Wind power modeling | MIT |
| pymoo | Multi-objective optimization | Apache 2.0 |
| scikit-learn | Machine learning (clustering) | BSD |
| rdflib | RDF/XML parsing for CIM | BSD |
| h5py, pyarrow | Data storage formats | BSD / Apache 2.0 |
| geopy, pyproj | Geographic calculations | MIT / MIT |
| autograd | Automatic differentiation | MIT |

**Concern:** opencv-python alone is ~50MB and pulls in system-level dependencies. pvlib/windpowerlib are domain-specific renewable energy packages unneeded for core power system simulation. This bloats the install and increases supply-chain surface area.

### Community and Ecosystem

- **GitHub:** 516 stars, 123 forks, 30 contributors (as of Mar 2026)
- **Issues:** 459 total (29 open), relatively low activity
- **Discussions:** Only 4 GitHub Discussions
- **Third-party packages:** None found. One tutorial repo (`GridCalTutorials` by SanPen, 0 stars), one academic playground repo (3 stars), one UPC research repo (0 stars)
- **Stack Overflow:** No dedicated tag
- **PyPI downloads:** ~200k lifetime for `gridcalengine` + ~23k for `veragridengine` (since Dec 2025)
- **Academic citations:** No CITATION.cff file. The HELM power flow algorithm has been published academically by the lead developer.
- **Commercial backing:** eRoots Analytics (Barcelona) provides the proprietary GSLV engine and commercial services. Listed clients include Redeia, Schneider Electric, GE Vernova, Acciona Energia, Engie, RTE, ETH Zurich.

### Documentation Quality

- **ReadTheDocs (veragrid.readthedocs.io):** Exists for v5.6.31. Has topic structure covering modeling, analysis types, and API docs. However, many deep links return 404. Auto-generated API reference exists but depth/completeness is uncertain.
- **GitHub Wiki:** 7 pages listed but most return loading errors. Content is from the pre-rename era.
- **Tutorials:** One official tutorial repo (`GridCalTutorials`) with 0 stars. A YouTube video linked from the wiki. No comprehensive "getting started" guide found.
- **Code docstrings:** The API module exposes ~349 public objects; spot-checking shows most have docstrings. However, the OPF options constructor has incomplete parameter documentation (many `:param:` entries are blank).
- **Changelog:** No structured changelog. Releases are tagged with version numbers only; commit messages are often just the version number (e.g., "5.6.31", "stuff").

### Release History

| Version | Date | Notes |
|---|---|---|
| 5.6.34 | ~Mar 2026 | Latest on PyPI |
| 5.6.20 | Feb 2, 2026 | Latest GitHub release |
| v5.4.0 | Feb 2, 2026 | "Last GridCal" — rename to VeraGrid |
| v5.3.0 | Jan 8, 2025 | Better topology and ACDC power flow |
| v5.2.0 | Nov 11, 2024 | Relicensed from LGPL to MPLv2 |
| v5.1.20 | Jul 23, 2024 | "End of Siroco" |
| 5.0.2 | Nov 18, 2023 | "The great split" (engine separated from GUI) |

**Release cadence:** Very high frequency (34 patch releases in 5.6.x since Feb 2026). However, GitHub releases lag behind PyPI (only 5.6.20 on GitHub vs 5.6.34 on PyPI). No changelogs accompany releases.

### License History

- Pre-2022: GPLv3
- Jan 2022 (v4.4.2): Changed to LGPL
- Nov 2024 (v5.2.0): Changed to MPL-2.0 (current)
- MPL-2.0 is permissive for file-level modifications — compatible with proprietary use

Source: [Issue #300](https://github.com/SanPen/GridCal/issues/300), release notes

### Solver Capabilities

Power flow solvers available:
- Newton-Raphson (NR)
- Gauss-Seidel
- Fast Decoupled
- Holomorphic Embedding (HELM) — unique to GridCal
- Iwamoto-Newton-Raphson
- Continuation Newton-Raphson (CPF)
- Levenberg-Marquardt
- Linear AC (LACPF)
- DC (Linear)
- Backwards-Forward Substitution (BFS, for radial networks)
- Powell's Dog Leg

Other capabilities: contingency analysis, state estimation, short circuit, stochastic power flow, small signal stability, clustering, reliability, investment optimization, ATC/NTC, RMS dynamic simulation.

### Proprietary GSLV Engine

The codebase includes integration points for a proprietary C++ engine called GSLV (`pygslv`), requiring a license from eRoots Analytics. The open-source engine runs pure Python with NumPy/SciPy/Numba acceleration. The GSLV engine is described on the eRoots website as handling "thousands of scenarios rapidly" with "RMS dynamic simulations and optimal power flow calculations."

Source: `VeraGridEngine/Utils/ThirdParty/gslv/gslv_activation.py`

## Sources

1. [GitHub: SanPen/GridCal (now VeraGrid)](https://github.com/SanPen/GridCal) — repo stats, issues, releases
2. [PyPI: veragridengine](https://pypi.org/project/veragridengine/) — package metadata
3. [PyPI: gridcalengine](https://pypi.org/project/gridcalengine/) — legacy package
4. [pepy.tech/projects/gridcalengine](https://pepy.tech/projects/gridcalengine) — download stats (~200k)
5. [pepy.tech/projects/veragridengine](https://pepy.tech/projects/veragridengine) — download stats (~23k)
6. [veragrid.readthedocs.io](https://veragrid.readthedocs.io/en/latest/) — documentation
7. [eRoots Analytics](https://www.eroots.tech) — commercial entity behind GridCal/VeraGrid
8. Installed package source: `VeraGridEngine` v5.6.28 in devcontainer at `/workspace/evaluations/gridcal/.venv/lib/python3.12/site-packages/VeraGridEngine/`
9. [GitHub Issue #397](https://github.com/SanPen/GridCal/issues/397) — OPF constraint violations
10. [GitHub Issue #430](https://github.com/SanPen/GridCal/issues/430) — ACOPF non-dispatchable crash
11. [GitHub Issue #426](https://github.com/SanPen/GridCal/issues/426) — Short circuit driver bug
12. [GitHub Issue #414](https://github.com/SanPen/GridCal/issues/414) — PSS/E export broken
13. [GitHub Issue #364](https://github.com/SanPen/GridCal/issues/364) — SCOPF feature request
14. [GitHub Issue #413](https://github.com/SanPen/GridCal/issues/413) — Contingency formulation review
15. [v5.4.0 release](https://github.com/SanPen/GridCal/releases/tag/v5.4.0) — rename announcement
16. [v5.2.0 release](https://github.com/SanPen/GridCal/releases/tag/v5.2.0) — license change to MPLv2

## Gaps and Uncertainties

- **Scalability on large networks:** No benchmarks found for 10k+ bus networks. The pure Python engine with Numba JIT may struggle at scale compared to C/C++/Julia solvers. Needs empirical testing with ACTIVSg 10k and FNM cases.
- **ACOPF correctness and convergence:** The custom IPS implementation has no published validation against standard IEEE test cases or MATPOWER reference solutions. Issues #397 and #430 suggest the ACOPF is not production-ready.
- **MATPOWER import fidelity:** Basic case39 loads correctly (39 buses, 10 generators, 35 lines + 11 transformers = 46 branches). Fidelity of cost curve import, generator limits, and transformer tap ratios needs verification against MATPOWER reference power flow.
- **Time-series OPF performance:** The linear OPF formulates the entire time horizon as a single LP. Memory and solve-time scaling with 8,760 hours on large networks is unknown.
- **Documentation completeness:** Could not verify depth of ReadTheDocs API docs — many links 404. The actual quality of auto-generated API docs needs manual inspection.
- **GSLV engine impact:** Unclear whether performance claims on the eRoots website refer to the open-source engine or the proprietary GSLV. Evaluation must use only the open-source engine.
- **Numba JIT warm-up:** First-run penalty for Numba-compiled functions could affect benchmarking. Need to warm up before timing.
- **Three-phase support:** Issue #425 (open) requests three-phase transformer modeling. A `PowerFlowDriver3Ph` exists but its completeness/correctness is uncertain.
- **State estimation:** Issue #419 flags missing observability analysis features and pseudo-measurement handling.
- **Dynamic simulation:** RMS simulation capability exists but GUI integration is incomplete (Issue #427). EMT capability is unclear — the GitHub topics include "emt" but no EMT solver type is visible in the enum.

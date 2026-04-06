# State Estimation Tooling Investigation

> Cross-cutting investigation for Issue #115 Item 8.
> Research date: 2026-03-28.

## Summary

**None of the six evaluated tools provide production-ready state estimation (SE) for transmission-scale grids.** Two tools (pandapower, GridCal) have native SE implementations, but both have critical limitations that prevent production use at target ISO scale. Two others (MATPOWER, PowerModels ecosystem) have SE in extras or ecosystem packages, but these are dormant or distribution-only. PyPSA and PowerSimulations.jl have no SE capability at all.

Outside the six evaluated tools, **JuliaGrid.jl** (MIT license, University of Sarajevo) is the most complete open-source SE framework — validated at 70,000-bus scale with AC SE, DC SE, PMU-only linear SE, observability analysis, and bad data detection. **power-grid-model** (Alliander/LF Energy, MPL-2.0) provides fast C++-backed SE but targets distribution grids.

No open-source tool provides hybrid SCADA+PMU state estimation or a production-ready real-time SE pipeline.

## Per-Tool Findings

### pandapower — Native SE, Not Production-Ready at Scale

**Status:** Most feature-rich Python SE implementation available.

| Aspect | Assessment |
|--------|------------|
| Algorithms | WLS, IRWLS (SHGM robust), LP/LAV, scipy optimization, AF-WLS (novel, for non-observable distribution grids) |
| Bad data detection | Chi-squared + largest normalized residual — docs warn "not very robust at this time"; open bug since 2022 (#1451) |
| Observability analysis | Measurement count heuristic only (2n−k); no topological observability analysis |
| Scalability | Convergence failures reported above ~89 buses (case89pegase); SimBench ~1000-bus networks fail |
| PMU support | `va`/`ia` measurement types accepted; thin testing, known test bug (#2524) |
| Three-phase SE | Not supported |
| Production deployments | None known |
| Recent activity | Concentrated in v3.0.0–v3.1.2 (Mar–Jun 2025); no SE changes since |

**Verdict:** Suitable for research and small-network prototyping. Would require significant hardening (scaling fixes, robust bad data detection, observability analysis) for target ISO-scale operational use.

### GridCal — Native SE, Educational Quality

**Status:** WLS framework exists but has critical gaps.

| Aspect | Assessment |
|--------|------------|
| Algorithms | 4 WLS solvers: Newton-Raphson, Levenberg-Marquardt, Gauss-Newton, Decoupled LU (broken) |
| Bad data detection | Coded (b-test) but **entirely commented out** in all solvers |
| Observability analysis | Can detect unobservable buses; no redundancy profiling. Issue #419 (open 7 months, stalled) |
| Scalability | Untested beyond textbook cases |
| PMU support | None |
| Filename | `state_stimation_driver.py` (typo — indicative of limited review) |

**Verdict:** Educational/textbook quality only. Missing bad data detection alone disqualifies it for real grid operations.

### MATPOWER — Dormant Community Extras

**Status:** Two SE modules in `extras/`, both academic legacy code.

| Module | Author | Last Active | Key Feature |
|--------|--------|-------------|-------------|
| `extras/se/` (mx-se) | Rui Bo | 2019 | WLS + observability analysis (`isobservable`) |
| `extras/state_estimator/` | J.S. Thorp | ~2013 | WLS + chi-squared bad data detection |

Both use dense matrices (no sparse optimization), have no PMU support, no robust estimation, and zero integration with MATPOWER 8's `mp.extension` API. Three open bugs on mx-se (filed 2024) remain unaddressed.

**Verdict:** Academic demonstrations only. Not maintained.

### PowerModels.jl — Distribution-Only Ecosystem Package

**Status:** No native SE in PowerModels core.

**PowerModelsDistributionStateEstimation.jl (PMDSE):** 40 stars, BSD-3, KU Leuven. Supports WLS, WLAV, MLE with relaxed variants and 3 bad data detection methods. **Distribution networks only** — cannot be applied to transmission SE without major modification. Last release v0.7.0 (Oct 2023).

No `PowerModelsStateEstimation.jl` exists for transmission networks.

**Verdict:** Not applicable for target ISO transmission-level SE.

### PyPSA — No SE

**Status:** Zero SE capability, zero community efforts (no issues, PRs, forks, or discussions).

PyPSA's numerical building blocks (Y-bus, Newton-Raphson, scipy sparse) could theoretically support a custom WLS SE implementation (~500–1000 lines for a basic version), but this would be building from scratch.

**Verdict:** Confirmed gap. SE must come from a companion tool.

### PowerSimulations.jl — No SE

**Status:** Zero SE capability across the entire NREL Sienna ecosystem (57 repositories checked). Sienna is scoped to operations simulation (unit commitment, economic dispatch), which is a fundamentally different problem class.

**Verdict:** No SE, no plans for SE.

## Open-Source SE Landscape

### Tier 1: JuliaGrid.jl — Most Complete Open-Source SE

| Metric | Value |
|--------|-------|
| Repository | github.com/mcosovic/JuliaGrid.jl |
| Stars | 48 |
| License | MIT |
| Language | Julia |
| Last push | 2026-02-06 |
| Contributors | 2 (essentially single-author) |
| Publication | arXiv:2502.18229, Feb 2025 / SoftwareX |

**SE capabilities:**
- Nonlinear AC SE (polar coordinates, SCADA-type measurements)
- Linear PMU-only SE (rectangular coordinates — deterministic, no convergence issues)
- DC state estimation
- WLS, LAV, orthogonal WLS estimators
- Observability analysis (for both SCADA and PMU configurations)
- Bad data detection (chi-squared + largest normalized residual)
- Optimal PMU placement (integer LP via JuMP)

**Scale validation:** 10,000, 20,000, and 70,000-bus systems benchmarked. Bad data analysis on 70k buses (577,242 measurements) completes in ~1.2 seconds.

**Limitations:** Single-author academic project (bus factor = 1). No hybrid SCADA+PMU fusion. Julia language adds a deployment dependency.

### Tier 2: power-grid-model (Alliander/LF Energy)

| Metric | Value |
|--------|-------|
| Repository | github.com/PowerGridModel/power-grid-model |
| Stars | 211 |
| License | MPL-2.0 |
| Language | C++ core, Python bindings |
| Activity | 10,360+ commits, 800+ releases |

**SE capabilities:** Newton-Raphson and iterative linear SE, three-phase asymmetric support, native batch parallelism.

**Limitation:** Designed for **distribution grids**, not transmission. LF Energy project page explicitly directs transmission users to PowSyBl Open Load Flow. No direct PyPSA converter (requires PyPSA → pandapower → PGM two-hop conversion).

### Tier 3: ANDES / CURENT LTB

| Metric | Value |
|--------|-------|
| Repository | github.com/CURENT/andes |
| Stars | 346 |
| License | GPL-3.0+ (copyleft — problematic for proprietary use) |
| Language | Python |

SE listed as one of five analysis routines, but documentation is sparse and the tool's strength is transient dynamics simulation. LTB platform (ANDES + DiME messaging) is the closest thing to a real-time SE platform in open source, but it's a research platform, not deployable.

### Notable Gaps in the Landscape

1. **No hybrid SCADA+PMU SE** exists in open source — all tools provide separate traditional or PMU-based SE
2. **No production-ready real-time SE pipeline** — all tools are batch/offline solvers
3. **ML-based SE** (PINNs, GNNs) shows promise but is not production-ready

## Recommendation for Phase 2 Stage 2

Since PyPSA (the recommended Phase 2 tool) has no SE capability, state estimation will require either a companion tool or custom development. Three viable paths:

### Path A: pandapower SE via PyPSA bridge (simplest)
- Use PyPSA for OPF/planning, export to pandapower for SE
- Existing (beta) `pypsa.Network.import_from_pandapower_net()` bridge
- **Risk:** pandapower SE convergence fails above ~89 buses; bridge is beta for complex topologies

### Path B: JuliaGrid.jl as SE core (most capable)
- JuliaGrid provides the most complete SE feature set (PMU support, observability, bad data, 70k-bus scale)
- Would require Julia in the deployment stack and a data bridge to PyPSA
- **Risk:** Single-author project, Julia deployment dependency

### Path C: Custom WLS SE on PyPSA's network model (most control)
- Build a lightweight WLS SE using PyPSA's Y-bus + scipy sparse
- Estimated effort: 2–4 weeks for basic WLS, longer for bad data detection + observability
- **Risk:** Significant development effort; reinventing existing solutions

**Bottom line:** No evaluated tool provides production-ready SE for target ISO-scale transmission grids. Phase 2 Stage 2 will require dedicated SE tooling work regardless of which path is chosen. The decision should be deferred to Phase 2 scoping, informed by the data pipeline architecture and measurement availability (SCADA vs PMU).

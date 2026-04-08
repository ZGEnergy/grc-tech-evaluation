# PowSyBl State Estimation Investigation

_Research date: 2026-03-27_

## Summary

PowSyBl (Power System Blocks) is an open-source Java framework for power system modeling
and simulation, initiated by RTE (the French TSO) and contributed to LF Energy in 2019.
It is the most production-deployed open-source grid analysis framework in Europe, now
underpinning cross-border capacity calculation for 30+ TSOs.

**State estimation verdict: PowSyBl does NOT currently provide a state estimation
implementation.** The grid model (IIDM) includes observability extensions to store SE
results (added 2022), but no SE solver exists in any public PowSyBl repository. SE does
not appear on the 2026 roadmap. The framework's strengths are load flow, security
analysis, sensitivity analysis, and remedial action optimization -- not SE.

## Ecosystem Overview

PowSyBl is a modular ecosystem of ~20 repositories under `github.com/powsybl/`. Key
components:

| Component | Purpose |
|---|---|
| **powsybl-core** | Grid model (IIDM), exchange format importers/exporters (CGMES, MATPOWER, PSS/E, UCTE, IEEE-CDF, PowerFactory), simulation APIs |
| **powsybl-open-loadflow** | AC Newton-Raphson and DC load flow, security analysis, sensitivity analysis (KLU sparse solver) |
| **powsybl-open-rao** | Remedial action optimization engine |
| **powsybl-dynawo** | Dynamic simulation via Dynawo (DynaFlow steady-state, DynaWaltz time-domain) |
| **powsybl-entsoe** | ENTSO-E-specific processes (GLSK, merging, flow-based) |
| **powsybl-metrix** | Multi-variant network simulation |
| **powsybl-optimizer** | Optimal power flow |
| **powsybl-diagram** | Single-line and network-area diagram generation |
| **powsybl-network-store** | Network model persistence (Cassandra-backed) |
| **powsybl-network-viewer** | TypeScript/web visualization components |
| **pypowsybl** | Python bindings via GraalVM native image |
| **powsybl.jl** | Julia bindings (network I/O and element access) |

## State Estimation Capabilities

### What exists

- **Observability extensions in IIDM** (powsybl-core, since September 2022, issue #1787):
  The grid model can store SE _results_ via `InjectionObservability` and
  `BranchObservability` extensions. These record whether an element is observable,
  plus standard deviations and redundancy indicators for P, Q, V measurements per
  side. There is also a `ThreeWindingsTransformerPhaseAngleClock` extension and
  tap-changer estimability flags.
- **No SE solver**: No `StateEstimation` class, API, or implementation exists in
  powsybl-open-loadflow, powsybl-core, or any other public PowSyBl repository. GitHub
  code search across the entire `powsybl` org returns zero results for
  `StateEstimation` or `state_estimation`.
- **Not on the roadmap**: The 2026 roadmap (quarterly releases 2026.0 through 2026.3)
  covers load flow improvements, HVDC/TCSC simulation, operator strategies, and
  diagram enhancements. State estimation is not mentioned. The 2027+ "best effort"
  bucket also does not include SE.

### What this means

PowSyBl was designed for planning and operational security analysis, not for real-time
state estimation. RTE likely uses proprietary or commercial SE tools (e.g., from GE or
Siemens EMS) for their control center, while PowSyBl handles the offline/planning
workloads. The observability extensions exist so that SE results from external tools
can be annotated onto the IIDM grid model.

## Open Load Flow Details

powsybl-open-loadflow v2.1.x provides:

- **AC load flow**: Full Newton-Raphson with KLU sparse solver (native code). Supports
  voltage regulation, phase shifters, slack distribution, reactive limits.
- **DC load flow**: Linear DC approximation.
- **Security analysis**: N-1 and N-k contingency analysis. Benchmarked at 5-29 ms per
  contingency on RTE 6515-bus network (single core).
- **Sensitivity analysis**: Active/reactive power flow sensitivities to injections, PSTs,
  HVDC setpoints.

### Benchmark numbers (Dell Precision 5680, i7-13700H, single core)

| Network | AC Load Flow (basic) | AC Load Flow (standard) |
|---|---|---|
| IEEE 14 | 179 us | 188 us |
| IEEE 118 | 1.37 ms | 1.88 ms |
| IEEE 300 | 3.5 ms | 5.9 ms |
| RTE 1888 (French EHV) | 24.7 ms | 30.7 ms |
| RTE 6515 (French EHV+HV) | 118 ms | 191 ms |

These are competitive with pandapower and faster than MATPOWER for large networks,
though LightSim2Grid (C++ Newton-Raphson for Grid2Op) is reportedly 4-7x faster than
pypowsybl for specific benchmarks.

## pypowsybl (Python Bindings)

pypowsybl wraps the Java framework via GraalVM native image compilation. Available
modules (as of the latest docs):

- `pypowsybl.network` -- grid model creation, import/export (CGMES, MATPOWER, PSS/E, etc.)
- `pypowsybl.loadflow` -- AC and DC load flow
- `pypowsybl.security` -- security analysis
- `pypowsybl.sensitivity` -- sensitivity analysis
- `pypowsybl.rao` -- remedial action optimization
- `pypowsybl.flowdecomposition` -- flow decomposition
- `pypowsybl.dynamic` -- dynamic simulation (via Dynawo)
- `pypowsybl.shortcircuit` -- short circuit analysis
- `pypowsybl.voltage_initializer` -- voltage initialization

**No `pypowsybl.state_estimation` module exists.** SE is not exposed in the Python API.

### pypowsybl interoperability

- Imports: CGMES, MATPOWER (.m), PSS/E (.raw/.rawx), IEEE-CDF, UCTE, PowerFactory
- Exports: CGMES, XIIDM, JIIDM, BIIDM, UCTE
- Includes a pandapower-to-PowSyBl network converter
- ANDES (dynamic simulation) has a `to_pypowsybl()` bridge for diagram generation
- No direct PyPSA converter exists in either direction

## Scale & Production Use

### RTE and the French grid

RTE operates ~100,000 km of transmission lines, ~2,500 substations, 63 kV to 400 kV.
PowSyBl has been validated on:

- **RTE 1888**: French EHV (Extra-High Voltage) system
- **RTE 6515**: Full French EHV + HV system
- **RTE 7000**: Published on HuggingFace (`rte-france/RTE7000`), ~7,000 buses
  representing the complete French transmission network in node-breaker topology

### European production deployments

PowSyBl is in production use by:

- **RTE** (France, initiator) -- grid planning and security analysis
- **Elia** (Belgium) -- grid analysis
- **CORESO** (pan-European RCC) -- operational security via CorNet program
- **TSCNET** (RCC) -- operational coordination
- **Baltic RCC** -- operational grid security studies
- **SeleneCC** -- European Merging Function implementation

Major milestone (December 2024): CorNet go-live of the **European Merging Function**,
consolidating individual TSO grid models into a unified Common Grid Model for 30+ TSOs.
PowSyBl Open Load Flow, Cost Sharing, and OpenRAO are the core engines.

### Vendors and contractors

Artelys (French optimization firm), AIA, Power Info, and CRESYM contribute to the
ecosystem. Artelys specifically improved Open Load Flow robustness under contract to RTE.

## License & Governance

- **License**: Mozilla Public License 2.0 (MPL-2.0) -- file-level copyleft, compatible
  with proprietary integration
- **Foundation**: LF Energy (Linux Foundation Energy)
- **Lifecycle stage**: Early Adoption (as of May 2023) -- focused on industry adoption,
  ready for production consideration. Not yet Graduated.
- **Security**: OpenSSF Best Practices silver badge (2023), security audit completed (2024)
- **Language**: Java (core), Python (pypowsybl via GraalVM), Julia (powsybl.jl)
- **Governance**: Technical Steering Committee (TSC) with representatives from RTE, Elia,
  and community contributors

## PyPSA Integration Path

There is **no direct PyPSA-PowSyBl converter** in either ecosystem. However, several
indirect paths exist:

1. **MATPOWER format bridge**: Both PyPSA (via pandapower import) and PowSyBl natively
   read MATPOWER `.m` files. This is the simplest interchange format for static network
   data.

2. **CGMES as interchange**: PowSyBl has the most mature open-source CGMES
   importer/exporter. PyPSA does not natively support CGMES, but there is community
   discussion about adding it (OpenMod forum, Dec 2024). A pypowsybl CGMES import
   followed by MATPOWER export could bridge the gap.

3. **pandapower bridge**: pypowsybl includes a pandapower-to-PowSyBl converter.
   pandapower has limited PyPSA interop. This is a lossy two-hop path.

4. **Custom scripting**: Both pypowsybl and PyPSA expose DataFrames for network elements.
   A custom Python script mapping between the two models is feasible but requires manual
   effort for each network type.

For target ISO SE specifically, CGMES is not the natural format (target ISO uses CIM but in a
different profile). The MATPOWER bridge or custom conversion would be more practical.

## Production Readiness Assessment

| Criterion | Assessment |
|---|---|
| **State estimation** | Not available. No SE solver, no roadmap item. |
| **Load flow** | Production-grade. Validated on real European grids by multiple TSOs. |
| **Scale** | Proven at 7,000+ bus transmission scale (French grid). |
| **Maturity** | LF Energy Early Adoption. In production at RTE, Elia, CORESO, etc. |
| **Python API** | pypowsybl is functional but SE is not exposed. |
| **target ISO relevance** | Limited. European-centric (CGMES, ENTSO-E processes). No native support for target ISO-specific data formats or market structures. |
| **SE alternative** | Would need to be paired with a separate SE tool (pandapower, JuliaGrid, or custom WLS implementation). |

### Bottom line for target ISO SE evaluation

PowSyBl is not a candidate for state estimation. It is an excellent load flow and
security analysis framework with unmatched European TSO adoption, but its scope
explicitly excludes SE. For the target ISO transmission-scale SE use case, the relevant
open-source options remain:

- **pandapower** -- has WLS SE, but Python-only and scaling concerns
- **JuliaGrid** -- purpose-built SE framework with WLS, LAV, PMU support
- **PowerModelsStateEstimation.jl** -- Julia SE on PowerModels
- **Custom WLS on PowSyBl load flow** -- theoretically possible (use PowSyBl for
  Jacobian computation, implement WLS externally) but no existing implementation

## Sources

- [PowSyBl Open Load Flow - GitHub](https://github.com/powsybl/powsybl-open-loadflow)
- [PowSyBl Core - GitHub](https://github.com/powsybl/powsybl-core)
- [pypowsybl - GitHub](https://github.com/powsybl/pypowsybl)
- [PowSyBl Benchmark - GitHub](https://github.com/powsybl/powsybl-benchmark)
- [Observability Extensions Issue #1787](https://github.com/powsybl/powsybl-core/issues/1787)
- [PowSyBl Roadmap Wiki](https://github.com/powsybl/.github/wiki/Roadmap)
- [PowSyBl - LF Energy](https://lfenergy.org/projects/powsybl/)
- [LF Energy Project Lifecycle](https://tac.lfenergy.org/process/lifecycle.html)
- [PowSyBl European Grid Sovereignty - LF Energy](https://lfenergy.org/powsybl-a-community-led-open-source-project-for-european-grid-sovereignty/)
- [PowSyBl Case Study - Linux Foundation Europe](https://linuxfoundation.eu/resources/powsybl-open-source-powering-europe)
- [Artelys improves PowSyBl for RTE](https://www.artelys.com/news/grid-power-flow-powsybl-open-source-rte/)
- [LF Energy PowSyBl Release Announcement](https://lfenergy.org/latest-lf-energy-powsybl-release-offers-enhancements-to-load-flow-accuracy-sensitivity-analysis-and-security/)
- [pypowsybl API Reference](https://github.com/powsybl/pypowsybl/blob/main/docs/reference/index.rst)
- [PowSyBl Open Load Flow Docs](https://powsybl.readthedocs.io/projects/powsybl-open-loadflow/en/stable/)
- [pypowsybl Interface in ANDES](https://docs.andes.app/en/latest/examples/pypowsybl.html)
- [PyPSA and CGMES Discussion - OpenMod Forum](https://forum.openmod.org/t/pypsa-and-the-cim-cgmes-does-it-make-sense-to-go-down-this-road/5033)
- [RTE Wikipedia](https://en.wikipedia.org/wiki/R%C3%A9seau_de_Transport_d'%C3%89lectricit%C3%A9)

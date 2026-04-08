# Python State Estimation Landscape

Research date: 2026-03-27

## Summary

PyPSA has no native state estimation (SE). The Python ecosystem offers a small number of
production-grade SE implementations. The two strongest candidates for Phase 2 integration are
**power-grid-model** (LF Energy / Alliander) and **pandapower** (Fraunhofer IEE). ANDES
(CURENT) lists SE as a feature but is primarily a transient dynamics tool. Everything else in
the landscape is either academic one-off code, unmaintained, or distribution-only with
restrictive licensing.

| Tool | SE Algorithms | Stars | License | Last Release | Maintained | Transmission? |
|------|--------------|-------|---------|-------------|------------|---------------|
| power-grid-model | WLS (Newton-Raphson), iterative linear | 211 | MPL-2.0 | 2026-03-26 | Very active (800+ releases) | No (distribution) |
| pandapower | WLS + chi-squared / normalized residual bad-data | 1,100 | BSD-3 | 2026-03-26 | Active | Yes |
| ANDES | Listed but underdocumented | 346 | GPL-3.0 | 2026-03-12 (v2.0.0) | Active | Yes |
| OpenPy-DSSE | Hybrid WLS (traditional + PMU) | 14 | CC BY-NC-SA 4.0 | 2022-12 | No | No (distribution) |
| PYPOWER | None | ~300 | BSD-3 | 2025-07 | Low activity | Yes (no SE) |
| Roseau Load Flow | Unconfirmed (tagged but not documented) | 63 | Proprietary (free <=10 buses) | 2026-03 | Active | No (distribution) |
| OpenDSS (via opendssdirect.py / py-dss-interface) | None natively | N/A | BSD / EPRI | Active | Active | No (distribution) |

## Tool Survey

### power-grid-model (LF Energy / Alliander)

- **Repository**: https://github.com/PowerGridModel/power-grid-model
- **PyPI**: `pip install power-grid-model` (or via conda)
- **Architecture**: C++ core with Python bindings -- very high performance
- **License**: MPL-2.0 (permissive, compatible with commercial use)
- **Activity**: 10,360+ commits, 800+ releases, v1.13.31 as of 2026-03-26. Backed by
  Alliander (Dutch DSO) and hosted under Linux Foundation Energy.

**State Estimation Capabilities:**
- Two SE calculation methods: `newton_raphson` and `iterative_linear`
- Newton-Raphson SE added in v1.7 (production-ready)
- Supports separate specification of active/reactive power measurement error margins
- Measurement types: voltage magnitude, power injection, power flow, current magnitude
- Full three-phase asymmetric calculation support
- Native parallel computing for batch calculations

**Limitations for Phase 2:**
- Designed for **distribution** grids, not transmission. The LF Energy project page
  explicitly directs transmission users to PowSyBl Open Load Flow instead.
- No direct PyPSA import/export. `power-grid-model-io` supports pandapower and Vision
  formats but not PyPSA natively. Integration path: PyPSA -> pandapower -> PGM.
- Focused on steady-state; no dynamic SE (EKF/UKF).

### ANDES (CURENT, University of Tennessee)

- **Repository**: https://github.com/CURENT/andes
- **PyPI**: `pip install andes` (v2.0.0, 2026-03-12)
- **License**: GPL-3.0+ (copyleft -- viral license, problematic for proprietary integration)
- **Stars**: 346
- **Activity**: 4,810 commits, 18 releases. Active development.

**State Estimation:**
- Listed as one of five analysis routines alongside power flow, time-domain simulation,
  eigenvalue analysis, and continuation power flow.
- However, SE documentation is sparse. The main use case and community focus is on
  transient dynamics simulation (DAE-based models with 100+ device models).
- Reads PSS/E RAW/DYR, MATPOWER, JSON, Excel formats.
- Returns results as NumPy arrays / Pandas DataFrames.

**Assessment:**
- ANDES is a serious tool for dynamics but SE appears to be a secondary feature.
- GPL-3.0 license is a significant constraint for any proprietary deployment.
- Could be valuable if the Phase 2 SE needs to be tightly coupled with dynamic simulation.

### pandapower (Fraunhofer IEE) -- reference only

Already evaluated separately in this project, but included here for completeness as the
strongest Python SE implementation.

- **WLS state estimation** with full tutorial and API documentation
- Measurement types: voltage magnitude, active/reactive power (bus, line, transformer),
  current magnitude
- Bad-data detection: chi-squared test and normalized residual test
- Direct PyPSA interoperability via `pypsa.Network.import_from_pandapower_net()` (beta)
- BSD-3 license, 1,100+ stars, very active

### PYPOWER

- **Repository**: https://github.com/rwl/PYPOWER
- **PyPI**: `pip install PYPOWER` (v5.1.19, 2025-07-10)
- **License**: BSD-3
- **Features**: DC/AC power flow (Newton-Raphson, Fast Decoupled), DC/AC OPF
- **State Estimation**: **None**. PYPOWER is a Python port of MATPOWER but does not include
  MATPOWER's SE module.
- Low development activity. pandapower supersedes it for all practical purposes.

### OpenDSS Python Interfaces

Two Python packages provide access to OpenDSS:

1. **opendssdirect.py** (DSS-Extensions): cross-platform Python bindings to an alternative
   OpenDSS engine. BSD license. Active development.
2. **py-dss-interface** (EPRI): Python bindings to official EPRI OpenDSS. Active.

**State Estimation**: OpenDSS itself has **no built-in SE**. It is a distribution system
simulator focused on time-series power flow, harmonics, and fault analysis. SE would need
to be implemented externally using OpenDSS as the network model backend.

### OpenPy-DSSE

- **Repository**: https://github.com/jlara6/OpenPy-DSSE
- **PyPI**: `pip install py-open-dsse`
- **License**: CC BY-NC-SA 4.0 (non-commercial, share-alike -- **not usable commercially**)
- **Stars**: 14, **Last commit**: 2022-12, **Not maintained**

**Features:**
- Hybrid WLS combining traditional measurements and D-PMU (distribution PMU) data
- Solution methods: nonlinear WLS, linear PMU, nonlinear PMU
- Measurement types: voltage magnitude, branch power flow, current magnitude, smart meter,
  zero injection, pseudo-measurements, phasor measurements
- Communicates with OpenDSS for network modeling

**Assessment**: Academically interesting but non-commercial license and abandoned
development make it unsuitable for production use. The hybrid WLS + PMU approach is
worth studying for algorithm design inspiration.

### Standalone WLS / EKF Libraries

No dedicated Python library exists for power system SE using EKF or UKF. The options are:

- **FilterPy** (`pip install filterpy`): General-purpose Bayesian filtering library with
  EKF, UKF, particle filter implementations. Could be used to build a custom dynamic SE
  on top of a power system model, but requires writing all the power-system-specific
  measurement functions and Jacobians.
- **statsmodels WLS**: General weighted least squares regression, not power-system-aware.
- Academic GitHub repos (IEEE 14-bus WLS implementations): single-commit, no tests, no
  maintenance, no documentation. Not suitable for production.

### GridCal and pandapower

Both are covered in separate evaluations in this project and excluded from this survey.

## PyPSA Integration Feasibility

### Path 1: PyPSA + pandapower SE (Recommended)

1. Build / maintain the network model in PyPSA (OPF, unit commitment, market clearing)
2. Export to pandapower via `pypsa.Network.export_to_pandapower()` or build a parallel
   pandapower net from the same data source
3. Inject SCADA/PMU measurements into the pandapower measurement tables
4. Run `pandapower.estimation.estimate()` for WLS SE with bad-data detection
5. Map estimated voltages/flows back to PyPSA components

**Pros**: Mature SE, BSD license, documented API, existing PyPSA<->pandapower bridge.
**Cons**: Bridge is beta (missing 3-winding transformers, switches, tap positions).
Maintaining two parallel network representations adds complexity.

### Path 2: PyPSA + power-grid-model SE

1. Build network in PyPSA
2. Convert PyPSA -> pandapower -> power-grid-model via `power-grid-model-io`
3. Run PGM SE (Newton-Raphson or iterative linear)
4. Map results back

**Pros**: C++ performance, LF Energy backing, asymmetric three-phase support.
**Cons**: Two-hop conversion (PyPSA->pp->PGM), distribution-grid focus may miss
transmission-level modeling needs for target ISO, no direct PyPSA converter.

### Path 3: Custom SE on PyPSA network model

1. Extract bus admittance matrix (Y-bus) from PyPSA network
2. Implement WLS SE using scipy.sparse + numpy (Jacobian construction, Gauss-Newton
   iteration, chi-squared bad-data detection)
3. Optionally use FilterPy for dynamic SE (EKF/UKF) wrapper

**Pros**: Full control, no license constraints, tailored to target ISO transmission topology.
**Cons**: Significant development effort (2-4 weeks for a basic WLS, longer for dynamic SE),
requires power systems expertise for correct Jacobian derivation and numerical stability.

### Path 4: PyPSA + ANDES SE

Feasible in principle (both read MATPOWER cases), but GPL-3.0 license creates viral
licensing concerns, and ANDES SE documentation is insufficient to assess production
readiness. Not recommended without further investigation.

## Recommended Candidates for Phase 2

### Tier 1: pandapower SE via PyPSA bridge

**Best fit for Phase 2 Stage 2.** Mature WLS implementation with bad-data detection,
permissive license, active maintenance, and an existing (beta) PyPSA conversion path.
The primary risk is the beta status of the PyPSA-pandapower bridge for complex network
topologies (target ISO has 3-winding transformers and phase shifters).

**Action items:**
- Test the PyPSA->pandapower bridge with the target ISO network topology
- Verify measurement injection workflow in pandapower
- Benchmark SE solve time for target ISO-scale networks (~3,000 buses)

### Tier 2: power-grid-model (if distribution-level SE is needed)

Best-in-class performance for distribution grids. If Phase 2 requires distribution-level
SE (e.g., behind-the-meter DER visibility), PGM is the strongest option. Not ideal for
target ISO transmission-level SE due to its distribution focus.

### Tier 3: Custom WLS SE on PyPSA

Fall-back if pandapower bridge proves inadequate for the target ISO topology. Building a
lightweight WLS SE directly on PyPSA's Y-bus avoids the conversion overhead but requires
dedicated development time.

### Not recommended

- **ANDES**: GPL-3.0 license, underdocumented SE, dynamics-focused
- **OpenPy-DSSE**: Non-commercial license, abandoned
- **PYPOWER**: No SE capability
- **OpenDSS**: No SE capability
- **Roseau Load Flow**: Proprietary license, distribution-only, SE unconfirmed

## Sources

- [ANDES GitHub](https://github.com/CURENT/andes)
- [ANDES PyPI](https://pypi.org/project/andes/)
- [power-grid-model GitHub](https://github.com/PowerGridModel/power-grid-model)
- [power-grid-model LF Energy page](https://lfenergy.org/projects/power-grid-model/)
- [power-grid-model v1.7 SE announcement](https://lfenergy.org/power-grid-model-v1-7-now-available-adding-the-newton-raphson-calculation-method-for-enhanced-state-estimation/)
- [power-grid-model-io pandapower converter](https://power-grid-model-io.readthedocs.io/en/stable/converters/pandapower_converter.html)
- [pandapower SE documentation](https://pandapower.readthedocs.io/en/v2.3.1/estimation.html)
- [pandapower SE tutorial notebook](https://github.com/e2nIEE/pandapower/blob/master/tutorials/state_estimation.ipynb)
- [PyPSA import_from_pandapower_net](https://docs.pypsa.org/v0.30.2/api/_source/pypsa.Network.import_from_pandapower_net.html)
- [PYPOWER PyPI](https://pypi.org/project/PYPOWER/)
- [OpenDSSDirect.py GitHub](https://github.com/dss-extensions/OpenDSSDirect.py)
- [py-dss-interface PyPI](https://pypi.org/project/py-dss-interface/)
- [OpenPy-DSSE GitHub](https://github.com/jlara6/OpenPy-DSSE)
- [GitHub state-estimation topic (Python)](https://github.com/topics/state-estimation?l=python)
- [Roseau Load Flow GitHub](https://github.com/RoseauTechnologies/Roseau_Load_Flow)
- [FilterPy EKF docs](https://filterpy.readthedocs.io/en/latest/kalman/ExtendedKalmanFilter.html)

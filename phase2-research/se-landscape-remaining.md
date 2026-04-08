# Remaining Non-Python SE Landscape

## Summary

This document surveys state estimation (SE) capabilities in non-Python open-source power
system tools that were not covered in the prior Python-focused or academic landscape reports.

| Tool | Language | Has SE? | License | Maturity |
|------|----------|---------|---------|----------|
| InterPSS | Java | No | Apache 2.0 | Medium -- active but narrow scope |
| PSAT | MATLAB/Octave | No (native) | GPL | High -- widely used in academia |
| HELM-based tools | Various | No dedicated SE | Various | Low -- power flow only |
| GridPACK | C++ (HPC) | Yes | BSD 2-Clause | Medium-High -- PNNL-backed |
| DPsim | C++ | No (native) | MPL 2.0 | Medium -- real-time simulation focus |
| RTDS | Proprietary HW+SW | N/A (commercial) | Commercial | High -- industry standard for HIL |
| JuliaGrid | Julia | Yes -- comprehensive | MIT | Medium -- recent (2025), strong SE |
| PowerModelsDistSE | Julia | Yes -- distribution | BSD | Medium -- research prototype |
| GridAPPS-D SE | C++ | Yes -- distribution | BSD | Medium -- DOE/PNNL-backed |
| PowSyBl | Java | No (not yet) | MPL 2.0 | High -- but SE on roadmap only |
| OpenDSS | Delphi/COM | Partial -- via external | BSD | High -- EPRI-backed, SE via COM |

**Key findings:**
- The strongest non-Python SE implementations are **JuliaGrid** (transmission-scale WLS/LAV
  with PMU support, tested to 70k buses) and **GridPACK** (C++ HPC SE with Kalman filter).
- **GridAPPS-D** provides a C++ WLS distribution SE within the DOE platform.
- Most other tools (InterPSS, PSAT, DPsim, PowSyBl) focus on power flow and dynamics,
  with SE either absent or only achievable through external integration.
- RTDS is fully commercial and not applicable to an open-source evaluation.

---

## InterPSS (Java)

**State estimation: No**

InterPSS (Internet technology-based Power System Simulator) is a Java-based open-source
simulator developed by an international team (US, Canada, China). It uses an Eclipse-based
plugin architecture.

**Implemented capabilities:**
- AC and DC load flow
- Short circuit analysis
- Transient stability simulation
- Distribution system analysis
- DC power supply system analysis

**Planned (not yet implemented):** relay coordination, harmonics, dynamic (small-signal)
stability, reliability.

State estimation is not mentioned in the documentation, GitHub repositories
(ipss-common, ipss-plugin, ipss-odm, ipss20, ExtendedPiecewiseAlgo), or the project
overview. The plugin architecture could theoretically support SE as an extension, but
no such plugin exists.

- **GitHub:** https://github.com/InterPSS-Project
- **Website:** https://sites.google.com/a/interpss.org/interpss/Home
- **License:** Apache 2.0 (per GitHub)
- **Last active:** 2026 (repositories show recent commits)

---

## PSAT (MATLAB/Octave)

**State estimation: No (native)**

PSAT (Power System Analysis Toolbox) by Federico Milano is one of the most widely used
open-source power system toolboxes in academia. It runs on MATLAB and GNU Octave.

**Core capabilities:**
- Power flow (Newton-Raphson)
- Continuation power flow (CPF)
- Optimal power flow (OPF)
- Small-signal stability analysis (eigenvalue)
- Time-domain simulation
- N-1 contingency analysis
- PMU placement analysis
- FACTS and wind turbine models
- Simulink-based network editor

**Regarding SE:** Despite some third-party academic papers using PSAT in conjunction with
state estimation research, PSAT itself does not include a built-in SE module. The
documentation (version 2.1.11) lists power flow, CPF, OPF, small-signal stability, and
time-domain simulation as the supported routines -- SE is not among them. Researchers have
used PSAT's COM/scripting interface to feed network models into external SE algorithms
(typically in MATLAB), but this is user-implemented, not a PSAT feature.

- **Website:** http://faraday1.ucd.ie/psat.html (cert expired as of 2026-03)
- **GitHub mirror:** https://github.com/cuihantao/PSAT
- **License:** GPL
- **Status:** Mature but largely in maintenance mode; last documented version 2.1.11

---

## HELM-based SE

**State estimation: No**

The Holomorphic Embedding Load Flow Method (HELM) is a mathematically guaranteed
convergent power flow technique (no iterative divergence risk). Open-source
implementations exist:

- **HELMpy** (Python 3) -- power flow solvers only (HELM + Newton-Raphson). No SE.
- **JosepFanals/HELM** (Python) -- HELM power flow implementation. No SE.
- **GridCal** includes a HELM power flow solver adapted from ASU research, but GridCal's
  SE module uses conventional WLS, not HELM-based estimation.

No open-source project implements state estimation using the holomorphic embedding
approach. HELM remains a power flow technique; its mathematical properties (analytic
continuation, Pade approximants) have not been adapted for SE in any publicly available
code.

---

## GridPACK (C++ HPC)

**State estimation: Yes**

GridPACK is a C++ framework from Pacific Northwest National Laboratory (PNNL) for
developing power grid applications on high-performance computing (HPC) platforms. It is
one of the few non-Python tools with a mature, purpose-built SE module.

**SE capabilities:**
- Weighted Least Squares (WLS) state estimation
- Kalman filter dynamic state estimation (added as a separate application module)
- Designed for distributed/parallel execution on HPC clusters using MPI
- Demonstrated scaling on the IEEE 118-bus system in distributed SE prototype

**Other applications:**
- AC power flow
- Dynamic simulation (transient stability)
- Contingency analysis
- Real-time path rating

**Architecture:** GridPACK provides a component-based framework where network topology is
distributed across MPI processes. Custom bus/branch components define the SE measurement
model. Mappers convert the network model into sparse algebraic systems solved via PETSc
or other backends.

- **GitHub:** https://github.com/GridOPTICS/GridPACK
- **Docs:** https://gridpack.readthedocs.io/en/latest/
- **License:** BSD 2-Clause
- **Backed by:** US DOE / PNNL
- **Language:** C++ (93.9%), with Python wrappers available

---

## DPsim (C++)

**State estimation: No (native)**

DPsim is a real-time capable dynamic power system simulator developed at RWTH Aachen
(Institute for Automation of Complex Power Systems). The simulation core is C++ with
Python bindings.

**Core capabilities:**
- Electromagnetic transient (EMT) simulation
- Dynamic phasor (DP) simulation
- Steady-state power flow (for initialization)
- Real-time execution (time steps down to 50 microseconds)
- CIM/CGMES model import
- VILLASnode interface for hardware-in-the-loop

**Regarding SE:** DPsim itself does not implement state estimation. However, it is part
of the SOGNO platform (sogno.energy), which pairs DPsim with **pyVolt** -- a separate
Python package that performs SE using CIM network models. In the SOGNO architecture,
DPsim acts as the real-time simulator providing synthetic measurements, and pyVolt
consumes those measurements for SE. This is an integration pattern, not a native DPsim
feature.

- **GitHub:** https://github.com/sogno-platform/dpsim
- **License:** MPL 2.0
- **pyVolt (companion SE):** https://github.com/sogno-platform/pyvolt (Python, separate package)

---

## RTDS

**State estimation: N/A (commercial product)**

RTDS (Real-Time Digital Simulator) is a **commercial** hardware+software platform from
RTDS Technologies Inc. (Winnipeg, Canada). It is not open source.

**What it is:**
- Custom FPGA-based hardware running electromagnetic transient simulations in real time
- Industry standard for hardware-in-the-loop (HIL) testing of protection relays, HVDC
  controls, and FACTS devices
- Used by utilities, equipment manufacturers, and research labs worldwide

**Regarding SE:** RTDS does not perform state estimation itself. It is used as a
real-time simulation environment to *test and validate* external SE algorithms.
Researchers have connected RTDS to MATLAB-based SE via software-in-the-loop (SIL),
feeding simulated RTU/PMU measurements to external estimators. RTDS provides the
"ground truth" simulation, not the estimation.

- **Website:** https://www.rtds.com/
- **License:** Commercial (proprietary hardware + software)
- **Open-source components:** None. Some researchers use open-source tools (OpenModelica,
  ATP-EMTP) alongside RTDS for model development, but RTDS itself is closed.

---

## Other Tools Found

### JuliaGrid (Julia) -- Noteworthy

**State estimation: Yes -- comprehensive**

JuliaGrid is an open-source Julia package specifically designed for power system state
estimation. Published in a 2025 paper (arXiv:2502.18229), it is the most feature-complete
open-source SE framework outside of Python.

**SE algorithms:**
- Nonlinear WLS (polar coordinates, Gauss-Newton)
- Robust WLS (orthogonal method, Peters-Wilkinson method)
- Least Absolute Value (LAV) estimator
- Linear SE with PMUs only (rectangular coordinates)
- DC state estimation (voltage angles only)

**Measurement support:**
- SCADA legacy: bus voltage magnitude, branch current magnitude, active/reactive power
  flows and injections
- PMU: voltage and current phasors (polar or rectangular), correlated error handling

**Additional features:**
- Observability analysis (flow islands, maximal observable islands)
- Observability restoration via pseudo-measurements
- Optimal PMU placement
- Bad data detection via normalized residuals
- Sparse inverse for efficient residual computation

**Scale tested:** 10,000 / 25,000 / 70,000 bus systems. On a 70,000-bus system,
processed 577,242 measurements with bad data analysis completing in ~1.2 seconds.

- **GitHub:** https://github.com/mcosovic/JuliaGrid.jl
- **Docs:** https://mcosovic.github.io/JuliaGrid.jl/stable/
- **License:** MIT
- **Paper:** https://arxiv.org/abs/2502.18229

### PowerModelsDistributionStateEstimation.jl (Julia)

**State estimation: Yes -- distribution systems**

Extension of PowerModelsDistribution.jl (LANL) for three-phase unbalanced distribution
network SE. Research-oriented flexible framework.

**Capabilities:**
- Multiple power flow formulations for SE (AC, LinDist, SDP relaxation)
- WLS and other estimation criteria
- Three-phase unbalanced models
- Designed for benchmarking SE formulations, not production speed

- **GitHub:** https://github.com/Electa-Git/PowerModelsDistributionStateEstimation.jl
- **License:** BSD
- **Affiliation:** KU Leuven / Electa research group

### GridAPPS-D State Estimator (C++)

**State estimation: Yes -- distribution systems**

A C++ WLS state estimator built as a core service in the DOE GridAPPS-D platform for
advanced distribution management systems.

**Capabilities:**
- Weighted Least Squares estimation
- Processes voltage, current, power, and switch status measurements
- Integrated with CIM-based distribution network models
- Real-time streaming via ActiveMQ message bus

- **GitHub:** https://github.com/GRIDAPPSD/gridappsd-state-estimator
- **License:** BSD
- **Backed by:** US DOE / PNNL
- **Dependencies:** SuiteSparse, ActiveMQ-CPP

### PowSyBl (Java) -- No SE Yet

PowSyBl is a major Java-based open-source framework from RTE (French TSO), hosted under
LF Energy. It supports load flow, security analysis, sensitivity analysis, short-circuit,
and dynamic simulation. State estimation is **not yet implemented** but appears on the
project roadmap (observability extensions issue #1787 in powsybl-core). Given PowSyBl's
industrial backing and the CIM/CGMES data model support, SE could eventually appear.

- **Website:** https://www.powsybl.org/
- **License:** MPL 2.0

### OpenDSS (Delphi/COM) -- Partial

OpenDSS (EPRI) supports distribution state estimation conceptually through its COM
interface. The recommended approach is to extract the system Y-matrix and voltage data
via COM, then run SE in an external program (MATLAB, Python). OpenDSS provides the
detailed feeder model and load allocation ("calibration") but not a self-contained SE
solver. Third-party libraries like OpenPy-DSSE (Python) bridge this gap.

- **Website:** https://www.epri.com/pages/sa/opendss
- **License:** BSD

---

## Sources

- [InterPSS Overview](https://sites.google.com/a/interpss.org/interpss/Home/overview)
- [InterPSS GitHub](https://github.com/InterPSS-Project)
- [InterPSS arXiv paper](https://arxiv.org/pdf/1711.10875)
- [PSAT GitHub mirror](https://github.com/cuihantao/PSAT)
- [PSAT documentation (Amazon)](https://www.amazon.com/Power-System-Analysis-Toolbox-Documentation/dp/B091F4NGZ8)
- [HELMpy GitHub](https://github.com/HELMpy/HELMpy)
- [GridPACK PNNL](https://www.pnnl.gov/projects/gridpacktm-open-source-framework-developing-high-performance-computing-simulations-power)
- [GridPACK GitHub](https://github.com/GridOPTICS/GridPACK)
- [GridPACK Distributed SE paper](https://www.pnnl.gov/publications/distributing-power-grid-state-estimation-hpc-clusters-system-architecture-prototype)
- [DPsim GitHub](https://github.com/sogno-platform/dpsim)
- [SOGNO State Estimation example](https://sogno.energy/docs/examples/state-estimation/)
- [pyVolt GitHub](https://github.com/sogno-platform/pyvolt)
- [RTDS Technologies](https://www.rtds.com/)
- [JuliaGrid paper (arXiv)](https://arxiv.org/abs/2502.18229)
- [JuliaGrid GitHub](https://github.com/mcosovic/JuliaGrid.jl)
- [JuliaGrid docs](https://mcosovic.github.io/JuliaGrid.jl/stable/)
- [PowerModelsDistributionStateEstimation.jl](https://github.com/Electa-Git/PowerModelsDistributionStateEstimation.jl)
- [GridAPPS-D State Estimator](https://github.com/GRIDAPPSD/gridappsd-state-estimator)
- [GridAPPS-D docs](https://gridappsd.readthedocs.io/en/master/hosted_applications/)
- [PowSyBl](https://www.powsybl.org/)
- [PowSyBl roadmap](https://github.com/powsybl/.github/wiki/Roadmap)
- [OpenDSS and State Estimation](https://opendss.epri.com/OpenDSSandStateEstimation.html)

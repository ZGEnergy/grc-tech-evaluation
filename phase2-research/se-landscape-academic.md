# Academic & Cutting-Edge SE Landscape

> Research compiled 2026-03-27. Focused on open-source state estimation (SE) tools
> and recent academic work relevant to transmission-level SE for target ISO grid modeling.

## Summary

The open-source SE landscape is dominated by a handful of tools, each with different
maturity levels and scope:

| Tool | Language | SE Scope | PMU Support | Scale Validated | License |
|------|----------|----------|-------------|-----------------|---------|
| **JuliaGrid** | Julia | AC, DC, PMU-only | Yes (native) | 70,000 bus | MIT |
| **pandapower** | Python | AC (WLS, robust) | No native PMU SE | Medium-scale | BSD-3 |
| **GridCal** | Python | AC (WLS) | Limited | Medium-scale | LGPL |
| **ANDES (CURENT LTB)** | Python | Static + dynamic | Via LTB platform | Transmission-scale | GPL-3 |
| **PMDSE.jl** | Julia | Distribution SE | No | Distribution only | BSD-3 |
| **MATPOWER** | MATLAB/Octave | AC (WLS) | No | Medium-scale | BSD-3 |

**Key finding:** JuliaGrid (published Feb 2025) is currently the most complete open-source
SE framework. It is the only tool that natively supports AC SE, DC SE, and linear
PMU-based SE with observability analysis, bad data detection (chi-squared + largest
normalized residual), and validation at 70,000-bus scale. For a target ISO-scale
implementation, JuliaGrid is the strongest candidate as a computational core.

pandapower remains the most accessible Python option but lacks PMU-specific SE
formulations, observability analysis, and has reported issues with bad data analysis
at scale (tens of thousands of buses).

No single open-source tool provides a production-ready, real-time hybrid SCADA+PMU
state estimator out of the box. This remains a gap that would require custom
integration work.
## PMU-Based State Estimation

### Why PMU SE Matters

PMU-based (linear) SE exploits the fact that synchrophasor measurements provide
direct voltage/current phasors, making the measurement-to-state relationship
**linear**. This eliminates the iterative Gauss-Newton process required for
traditional SCADA-based (nonlinear) SE, enabling:
- Solve times fast enough for PMU reporting rates (up to 60 Hz)
- No convergence issues (direct linear solve)
- Higher accuracy from synchronized time-stamped measurements

### Open-Source Tools with PMU SE

**JuliaGrid** is the standout. It implements:
- **PMU State Estimation** as a dedicated linear model using rectangular coordinates
  (real/imaginary parts of bus voltages and branch current phasors)
- WLS estimator for PMU-only SE with robust variants (orthogonal method,
  Peters-Wilkinson method) for ill-conditioned measurement sets
- Observability analysis specific to PMU placement
- Bad data detection for PMU measurements

Reference: Cosovic et al., "JuliaGrid: An Open-Source Julia-Based Framework for
Power System State Estimation," arXiv:2502.18229, Feb 2025. Published in
SoftwareX (2025/2026).

**OpenPMU** is an open-source PMU hardware+software platform (Python-based phasor
estimator) that produces synchrophasors from sampled values. It is a data
acquisition tool, not an SE solver, but could serve as a PMU data source for
an SE pipeline.

**ComEd DLSE** (distribution linear SE) demonstrated PMU-rate SE (60 Hz solve rate)
in a real utility deployment, described in a 2024 Springer publication. The
implementation itself is not open-source but validates the feasibility of
PMU-rate linear SE at utility scale.

### PMU Data Resources

Texas A&M provides **synthetic PMU data** for their ACTIVSg test cases, and an
open-source library of 1,694 real transmission-level PMU events was published in
IEEE Transactions on Power Systems (2023), providing the largest public dataset
for benchmarking PMU-based SE algorithms.
## Hybrid SE (SCADA + PMU)

Hybrid SE combines slow SCADA measurements (2-10 second scan rates, unsynchronized)
with fast PMU measurements (30-60 Hz, GPS-synchronized). This is the realistic
operational scenario for any modern grid including target ISO.

### Approaches in the Literature

1. **Two-stage sequential**: Run traditional WLS SE on SCADA, then refine with
   PMU measurements in a linear post-processing step. Most common in production
   EMS implementations (e.g., GE, Siemens, ABB/Hitachi).

2. **Extended Kalman Filter (EKF) fusion**: Treats the different measurement rates
   as a multi-rate estimation problem. A 2024 paper in Energies proposes EKF-based
   fusion that handles SCADA/PMU rate mismatch natively.

3. **Unified WLS with mixed measurements**: Augments the traditional SE
   measurement vector with PMU phasor measurements. Requires careful handling of
   different coordinate systems (polar for SCADA, rectangular for PMU).

### Open-Source Status

**No mature open-source hybrid SE implementation exists.** The closest options:

- **JuliaGrid** provides separate AC SE (for SCADA-type measurements) and PMU SE
  modules. A hybrid pipeline could be built by running both and combining results,
  but there is no built-in fusion mechanism.

- **ORNL** published work on a hybrid SCADA/PMU online state estimator (Parashar
  et al., IEEE PES 2013), but no open-source release accompanied it.

- **SCADA BR** is an open-source web-based SCADA system that has been demonstrated
  with PMU integration in a lab setting (IEEE 2014 paper), but it is a monitoring
  platform, not an SE solver.

- **Co-simulation frameworks** (e.g., OpenDSS + OMNET++ at IIT Madras) have
  demonstrated hybrid SE in research settings but are not packaged as reusable
  SE tools.

### Implication for target ISO

Building a hybrid SE for target ISO would likely require:
1. JuliaGrid (or custom Julia/Python code) as the SE computational core
2. Custom data fusion logic for SCADA + PMU measurement streams
3. Integration with a real-time data pipeline (e.g., streaming PMU via C37.118)
## Transmission-Scale SE Tools

For target ISO grid modeling, the SE tool must handle transmission-scale networks
(thousands of buses, HV/EHV voltage levels).

### Tools Validated at Transmission Scale

**JuliaGrid** -- Validated on 10,000, 20,000, and 70,000-bus systems. The Feb 2025
paper includes benchmarks showing competitive performance with commercial tools.
Julia's JIT compilation and sparse linear algebra (KLU factorization) provide
the performance needed for large-scale SE.

**ANDES / CURENT LTB** -- Designed for transmission-scale simulation. ANDES
supports power flow via Newton-Raphson and includes a state estimation routine,
though SE is not its primary focus. The LTB platform architecture (ANDES +
DiME messaging + AGVis visualization) is designed for closed-loop real-time
simulation including SE in the loop.

**pandapower** -- Built on PYPOWER (Python port of MATPOWER). Handles
transmission-scale power flow well but the SE module has reported numerical
issues at scale. The JuliaGrid paper notes pandapower's bad data analysis
"may encounter issues when applied to large-scale power systems."

**MATPOWER** -- The SE module (`runse`) uses WLS via MATLAB/Octave. Mature and
well-tested but limited to basic WLS without PMU support or robust estimators.
Not designed for real-time operation.

### Tools NOT Suitable for Transmission SE

**PowerModelsDistributionStateEstimation.jl (PMDSE)** -- Explicitly scoped to
distribution networks. Built on PowerModelsDistribution.jl which models
unbalanced three-phase systems. Not applicable to balanced transmission SE.

**GridLAB-D** -- Distribution-focused agent-based simulator (PNNL). No
transmission SE capability.

**OpenDSS** -- Distribution system simulator (EPRI). No built-in SE; some
community attempts exist but are not maintained.
## Real-Time SE Implementations

Real-time SE requires solving the estimation problem within the measurement
scan cycle (seconds for SCADA, milliseconds for PMU-rate).

### Current State

**No open-source tool provides a production-ready real-time SE pipeline.** All
existing tools are batch/offline solvers that take a measurement snapshot and
return an estimate. The real-time wrapper (data ingestion, time alignment,
triggering, result publication) must be built separately.

**JuliaGrid** has the best potential for real-time use due to:
- Julia's compiled performance (competitive with C/Fortran for numerical code)
- Automatic detection and reuse of computed data structures between solves
- Linear PMU SE that avoids iterative convergence (deterministic solve time)

**CURENT LTB** is the closest to a real-time platform. Its architecture includes:
- DiME (Distributed Messaging Environment) for streaming data between components
- ANDES running in a simulation loop with measurement injection
- A state estimator module that receives measurements and returns estimates
- The platform has been demonstrated in hardware-in-the-loop settings

**ComEd's DLSE** (proprietary) demonstrated 60 Hz SE solve rate using PMU data,
proving real-time PMU-rate SE is feasible. The algorithmic approach (linear SE)
is straightforward to replicate with JuliaGrid's PMU SE module.

### Architecture Implications

A real-time SE system for target ISO would need:
1. **Data layer**: C37.118 PDC (phasor data concentrator) for PMU streams,
   ICCP/DNP3 for SCADA
2. **Time alignment**: Buffer and align SCADA snapshots with PMU windows
3. **SE solver**: JuliaGrid or equivalent, called per scan cycle
4. **State publication**: Push estimated states to downstream applications
   (contingency analysis, SCOPF, visualization)
## ML-Based Approaches

Machine learning for SE is an active research area with several promising
directions, though all remain at the research stage.

### Physics-Informed Neural Networks (PINNs)

PINNs embed power flow equations as loss function constraints, allowing the
network to learn SE while respecting Kirchhoff's laws and Ohm's law.

- **Physics-informed GNN for SE** (Li et al., Applied Energy, 2024): Combines
  graph neural networks with physical power flow constraints. Validated on IEEE
  14, 57, and 118-bus systems. Achieves >20% lower MSE than conventional WLS
  in scenarios with high measurement noise or missing data.

- **PINNs for accelerated SE** (arXiv:2310.03088, 2023): Demonstrates 87x
  speedup over conventional Gauss-Newton SE by using a trained neural network
  as a warm-start or direct estimator. Most beneficial when the network
  topology is stable and measurements arrive at high frequency.

- **Open source**: github.com/gmisy/Physics-Informed-Neural-Networks-for-Power-Systems
  provides a framework for PINN-based power system applications including SE.

### Graph Neural Networks (GNNs)

GNNs naturally map to power network topology (buses = nodes, branches = edges).

- **GNN for SE** (Kundacina et al., arXiv:2201.04056): Uses IGNNITION framework
  to train a GNN that estimates complex bus voltages from PMU measurements.
  Training data generated synthetically via JuliaGrid's linear WLS solver.
  Open source: github.com/ognjenkundacina/graph-neural-network-state-estimation

- **Topology-aware GNN** (IEEE Trans. Power Systems, 2024): Handles topology
  changes and PMU data loss in real-time, combining graph convolution with
  multi-head attention layers.

- **Master's thesis** (Univ. Freiburg, 2024): Comprehensive GNN-based SE with
  benchmarks against WLS on IEEE test cases.

### Practical Assessment

ML-based SE is **not ready for production** on a target ISO-scale grid:
- Training requires large labeled datasets (synthetic or historical SE solutions)
- Topology changes (switching, outages) invalidate trained models unless the
  architecture handles dynamic graphs
- Regulatory/reliability requirements demand explainable, deterministic methods
- Most promising near-term use: warm-starting conventional SE, or providing
  fast approximate estimates between SCADA scan cycles

ML approaches may become relevant as a **complement** to traditional SE
(e.g., filling in pseudo-measurements for unobservable areas, detecting bad
data, or providing fast approximate SE between scan cycles).
## Key Research Groups & Projects

### CURENT (Center for Ultra-Wide-Area Resilient Electric Energy Transmission)
- **Affiliation**: University of Tennessee Knoxville (UTK), formerly with Cornell
- **Key output**: ANDES, AMS, LTB platform
- **SE relevance**: LTB includes SE in its closed-loop simulation architecture;
  ANDES has a state estimation routine for transmission systems
- **GitHub**: github.com/CURENT
- **Note**: GPL-3 license on ANDES may limit commercial use

### Fraunhofer IEE + University of Kassel
- **Key output**: pandapower (500,000+ downloads as of 2024)
- **SE relevance**: WLS SE with robust estimators (IRWLS, Huber, SHGM, QL, QC),
  chi-squared and normalized residual bad data detection
- **Limitation**: No PMU SE, no observability analysis, scale issues
- **GitHub**: github.com/e2nIEE/pandapower

### TU Berlin (Digital Transformation in Energy Systems, ENSYS)
- **Key output**: PyPSA framework
- **SE relevance**: PyPSA does NOT include state estimation. Focus is on
  capacity expansion and optimal power flow for planning studies.
- **Relevance to project**: PyPSA is in our evaluation set but not for SE

### University of Sarajevo (Mcosovic group)
- **Key output**: JuliaGrid
- **SE relevance**: Most complete open-source SE framework. AC SE, DC SE, PMU SE,
  observability analysis, bad data detection, LAV estimator
- **GitHub**: github.com/mcosovic/JuliaGrid.jl

### KU Leuven / Electa Group
- **Key output**: PowerModelsDistributionStateEstimation.jl
- **SE relevance**: Flexible distribution SE with multiple formulations (WLS, WLAV,
  MLE) and power flow approximations. Research-oriented benchmarking tool.
- **GitHub**: github.com/Electa-Git/PowerModelsDistributionStateEstimation.jl

### LANL (Los Alamos National Laboratory)
- **Key output**: PowerModels.jl, PowerModelsDistribution.jl
- **SE relevance**: Underlying optimization framework used by PMDSE.jl.
  PowerModels.jl itself focuses on OPF, not SE.
- **GitHub**: github.com/lanl-ansi

### NREL (National Renewable Energy Laboratory)
- **Key output**: Sienna ecosystem (PowerSystems.jl, PowerSimulations.jl,
  PowerFlows.jl)
- **SE relevance**: No SE module in Sienna. Focus is on production cost modeling
  and dynamic simulation. However, PowerSystems.jl provides excellent data
  infrastructure for Julia-based power system tools.

### Texas A&M (Overbye group)
- **Key output**: ACTIVSg synthetic grid test cases (200 to 70,000 bus),
  synthetic PMU data
- **SE relevance**: Provides the benchmark networks and PMU datasets needed to
  validate SE at scale. The 2,000-bus and 10,000-bus cases with time-series
  data are particularly useful for SE testing.
- **Repository**: electricgrids.engr.tamu.edu
## IEEE Benchmarks

### Standard IEEE Test Cases for SE

These are the workhorses for SE algorithm validation:

| Case | Buses | Generators | Lines | Notes |
|------|-------|-----------|-------|-------|
| IEEE 14 | 14 | 5 | 20 | Minimum viable test; too small for scale testing |
| IEEE 30 | 30 | 6 | 41 | Common in textbook examples |
| IEEE 57 | 57 | 7 | 80 | Moderate complexity |
| IEEE 118 | 118 | 19 | 186 | Most common SE benchmark in papers |
| IEEE 300 | 300 | 69 | 411 | Largest classic IEEE case |

### Texas A&M ACTIVSg Synthetic Grids

For realistic large-scale SE validation:

| Case | Buses | Footprint | PMU Data | Time Series |
|------|-------|-----------|----------|-------------|
| ACTIVSg200 | 200 | Illinois | No | No |
| ACTIVSg500 | 500 | South Carolina | No | No |
| ACTIVSg2000 | 2,000 | Texas | Yes | Yes (1 year) |
| ACTIVSg10k | 10,000 | Western US | No | Yes (1 year) |
| ACTIVSg25k | 25,000 | Northeast US | No | No |
| ACTIVSg70k | 70,000 | Eastern US | No | No |

The ACTIVSg2000 case is particularly relevant for target ISO-scale SE testing because
it includes synthetic PMU data and represents a realistic transmission grid.

### UW Power Systems Test Case Archive

The University of Washington maintains the original IEEE test case archive
(labs.ece.uw.edu/pstca/) in MATPOWER-compatible format. These are the canonical
versions used by most open-source tools.

### MATPOWER Case Files

MATPOWER ships with 60+ test cases including all IEEE standards plus Polish,
PEGASE (European), and RTE (French) systems up to 13,659 buses. These are
available in the `data/networks/` directory of this evaluation project.
## Sources

### Papers
- Cosovic et al., "JuliaGrid: An Open-Source Julia-Based Framework for Power System State Estimation," arXiv:2502.18229, Feb 2025 / SoftwareX 2025
- Thurner et al., "pandapower -- An Open Source Python Tool for Convenient Modeling, Analysis and Optimization of Electric Power Systems," IEEE Trans. Power Systems, 2018
- Kundacina et al., "State Estimation in Electric Power Systems Leveraging Graph Neural Networks," arXiv:2201.04056, 2022
- Li et al., "Physics-informed graphical neural network for power system state estimation," Applied Energy, 2024
- Vanin et al., "PowerModelsDistribution.jl: An Open-Source Framework for Exploring Distribution Power Flow Formulations," EPSR, 2020
- Birchfield et al., "ACTIVSg synthetic grids" and "Synthetic PMU data," Texas A&M, 2016-2023
- Open-source PMU data library, IEEE Trans. Power Systems, 2023

### Repositories
- JuliaGrid: https://github.com/mcosovic/JuliaGrid.jl
- pandapower: https://github.com/e2nIEE/pandapower
- PMDSE.jl: https://github.com/Electa-Git/PowerModelsDistributionStateEstimation.jl
- CURENT LTB: https://github.com/CURENT
- GNN SE: https://github.com/ognjenkundacina/graph-neural-network-state-estimation
- PINNs for Power Systems: https://github.com/gmisy/Physics-Informed-Neural-Networks-for-Power-Systems
- OpenPMU: https://github.com/OpenPMU/OpenPMUdocs
- Texas A&M test cases: https://electricgrids.engr.tamu.edu/
- UW PSTCA: https://labs.ece.uw.edu/pstca/
- best-of-ps (curated list): https://github.com/ps-wiki/best-of-ps

### Documentation
- JuliaGrid docs: https://mcosovic.github.io/JuliaGrid.jl/stable/
- pandapower SE docs: https://pandapower.readthedocs.io/en/latest/estimation.html
- Sienna: https://nrel-sienna.github.io/Sienna/
- CURENT LTB: https://curent.github.io/

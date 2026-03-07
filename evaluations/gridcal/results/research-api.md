# GridCal (VeraGrid) -- Research: API & Formulations

**Tool version studied:** VeraGridEngine 5.6.28 (installed); latest on PyPI: 5.6.30
**Import name:** `VeraGridEngine` (aliased as `vge` or `gce` in examples)
**PyPI package:** `veragridengine`
**License:** MPL-2.0
**Repository:** <https://github.com/SanPen/VeraGrid> (renamed from <https://github.com/SanPen/GridCal>)

> GridCal was renamed to VeraGrid circa v5.5+. The engine package changed from
> `GridCalEngine` to `VeraGridEngine`. The API surface, class names, and module
> layout are otherwise identical. Documentation at <https://veragrid.readthedocs.io>
> still uses "GridCal" in some stable-branch URLs.

## Key Findings

1. **Rich API with convenience functions.** Top-level `vge.power_flow()`, `vge.linear_opf()`, `vge.nonlinear_opf()`, `vge.open_file()` provide one-call access to major analyses. Lower-level Driver classes offer full control.

2. **13 power-flow solver algorithms** via `SolverType` enum: Newton-Raphson, Gauss-Seidel, HELM, Levenberg-Marquardt, Fast Decoupled, Iwamoto-NR, Powell Dog-Leg, Continuation-NR, Linear (DC), LACPF, BFS, and more.

3. **DC OPF and AC OPF are separate code paths.** DC OPF uses MIP solvers (HiGHS, SCIP, CPLEX, Gurobi, Xpress, CBC) via PuLP or OR-Tools. AC OPF uses a custom interior-point solver (Newton-Raphson IPS with KKT conditions).

4. **Unit commitment is a dispatch mode**, not a separate driver. Set `OpfDispatchMode.UnitCommitment` in `OptimalPowerFlowOptions` to add binary on/off variables, min-up/down time, startup/shutdown costs, and ramp constraints.

5. **Extensive file format support.** Import: MATPOWER (.m), PSS/e (.raw/.rawx v29-35), CIM 16, CGMES 2.4.15/3.0, DigiSilent (.dgs), PSLF (.epc), UCTE, PyPSA, pandapower, IIDM. Export: native .veragrid/.xlsx/.json, CGMES, PSS/e.

6. **MultiCircuit is the central data container.** Buses, branches, generators, loads, batteries, shunts, HVDC lines, VSCs are stored as typed device lists. Island detection and splitting are handled automatically.

7. **Results are numpy arrays with DataFrame accessors.** `results.voltage` (complex), `results.Sf` (complex branch flows), `results.bus_shadow_prices`, plus `results.get_bus_df()` / `results.get_branch_df()` for pandas DataFrames.

8. **Three-phase unbalanced power flow** is a first-class citizen via `vge.power_flow3ph()` and `PowerFlowDriver3Ph`.

9. **Linear analysis (PTDF/LODF)** has dedicated drivers (`LinearAnalysisDriver`) returning full sensitivity matrices.

10. **Hydro-electric OPF extension** adds fluid nodes, paths, turbines, pumps, and P2X devices with mass-balance coupling to electrical dispatch.

## Detailed Notes

### API Entry Points

Source: `.venv/lib/python3.12/site-packages/VeraGridEngine/api.py`

The top-level API is defined in `api.py` and re-exported through `__init__.py`. All functions accept a `MultiCircuit` grid object and return typed result objects.

| Function | Purpose | Returns |
|----------|---------|---------|
| `vge.open_file(filename)` | Load grid from any supported format | `MultiCircuit` |
| `vge.save_file(grid, filename)` | Save grid to native format | None |
| `vge.save_cgmes_file(grid, filename, boundary_set)` | Export CGMES | `Logger` |
| `vge.power_flow(grid, options)` | Snapshot AC/DC power flow | `PowerFlowResults` |
| `vge.power_flow3ph(grid, options)` | Three-phase unbalanced PF | `PowerFlowResults3Ph` |
| `vge.power_flow_ts(grid, options, time_indices)` | Time-series power flow | `PowerFlowResults` |
| `vge.linear_power_flow(grid, options)` | PTDF-based linear PF | `LinearAnalysisResults` |
| `vge.linear_power_flow_ts(grid, options)` | Time-series linear PF | `LinearAnalysisTimeSeriesResults` |
| `vge.linear_opf(grid, options)` | DC OPF (MIP-based) | `OptimalPowerFlowResults` |
| `vge.nonlinear_opf(grid, options)` | AC OPF (interior-point) | `NonlinearOPFResults` |
| `vge.simple_opf(grid, options)` | Greedy dispatch OPF | `OptimalPowerFlowResults` |
| `vge.balanced_pf(grid, options, opf_options)` | OPF + PF verification | `OptimalPowerFlowResults` |
| `vge.short_circuit(grid, fault_index, fault_type)` | Short-circuit analysis | `ShortCircuitResults` |
| `vge.continuation_power_flow(grid, options)` | Voltage stability (CPF) | CPF results |
| `vge.contingencies_ts(circuit)` | Time-series N-1 contingency | `ContingencyAnalysisTimeSeriesResults` |
| `vge.clustering(circuit, n_points)` | Time-series clustering | `ClusteringResults` |

Source: [VeraGridEngine/api.py](https://github.com/SanPen/VeraGrid) (installed at `.venv/.../VeraGridEngine/api.py`)

### Driver Pattern

For full control, use the Driver classes directly:

```python
driver = vge.PowerFlowDriver(grid=grid, options=options)
driver.run()
results = driver.results
```

All drivers follow this pattern. Time-series drivers additionally accept `time_indices` arrays and optional `clustering_results`. The OPF driver can accept `opf_results` to initialize a subsequent power-flow verification run.

Key drivers (in `VeraGridEngine/Simulations/`):
- `PowerFlowDriver`, `PowerFlowDriver3Ph`, `PowerFlowTimeSeriesDriver`
- `OptimalPowerFlowDriver`, `OptimalPowerFlowTimeSeriesDriver`
- `LinearAnalysisDriver`, `LinearAnalysisTimeSeriesDriver`
- `ShortCircuitDriver`
- `ContinuationPowerFlowDriver`
- `ContingencyAnalysisDriver`, `ContingencyAnalysisTimeSeriesDriver`
- `ClusteringDriver`
- `StateEstimationDriver` (in `Simulations/StateEstimation/`)
- `SmallSignalStability` (in `Simulations/SmallSignalStability/`)
- `InvestmentsEvaluationDriver` (in `Simulations/InvestmentsEvaluation/`)
- `NodalCapacityTimeSeriesDriver` (in `Simulations/NodalCapacity/`)
- `ReliabilityDriver` (in `Simulations/Reliability/`)

Source: `VeraGridEngine/Simulations/` directory listing

### Power Flow Solver Types

Defined in `VeraGridEngine/enumerations.py`, class `SolverType`:

| Enum Value | Description |
|-----------|-------------|
| `NR` | Newton-Raphson (default) |
| `GAUSS` | Gauss-Seidel |
| `Decoupled_LU` | Decoupled LU Decomposition |
| `GN` | Gauss-Newton |
| `Linear` | DC power flow (linear approximation) |
| `HELM` | Holomorphic Embedding Load-flow Method |
| `PowellDogLeg` | Powell's Dog Leg |
| `IWAMOTO` | Iwamoto-Newton-Raphson |
| `CONTINUATION_NR` | Continuation Newton-Raphson |
| `LM` | Levenberg-Marquardt |
| `FASTDECOUPLED` | Fast Decoupled |
| `LACPF` | Linear AC power flow |
| `LINEAR_OPF` | Linear OPF (used in OPF context) |
| `NONLINEAR_OPF` | Nonlinear OPF (used in OPF context) |
| `GREEDY_DISPATCH_OPF` | Greedy dispatch |
| `Proportional_OPF` | Proportional OPF |
| `BFS` | Backwards-Forward substitution (for PGM engine) |
| `BFS_linear` | BFS linear (for PGM engine) |
| `Constant_Impedance_linear` | Constant impedance linear (for PGM engine) |
| `NoSolver` | No solver |

Each numerical method has its own implementation file in `Simulations/PowerFlow/NumericalMethods/`:
- `newton_raphson_fx.py`, `gauss_power_flow.py`, `helm_power_flow.py`
- `iwamoto_newton_raphson.py`, `levenberg_marquadt_fx.py`
- `fast_decoupled.py`, `linearized_power_flow.py`, `powell_fx.py`

The `retry_with_other_methods` option (default `True`) in `PowerFlowOptions` automatically tries alternative solvers if the primary one fails.

Source: `VeraGridEngine/enumerations.py` lines 214-293

### MIP Solvers (for DC OPF)

Defined in `VeraGridEngine/enumerations.py`, class `MIPSolvers`:

| Enum Value | Solver |
|-----------|--------|
| `HIGHS` | HiGHS (default, open-source) |
| `SCIP` | SCIP |
| `CPLEX` | IBM CPLEX |
| `GUROBI` | Gurobi |
| `XPRESS` | FICO Xpress |
| `CBC` | COIN-OR CBC |
| `PDLP` | PDLP |

MIP framework choices (`MIPFramework` enum): `PuLP` (default) or `OrTools`.

Source: `VeraGridEngine/enumerations.py` lines 323-378

### Engine Types

The `EngineType` enum allows alternative computation backends:

| Enum Value | Description |
|-----------|-------------|
| `VeraGrid` | Native Python engine (default) |
| `Bentayga` | Bentayga engine |
| `NewtonPA` | Newton Power Analytics |
| `PGM` | Power Grid Model |
| `GSLV` | GSLV engine |

Only VeraGrid is bundled; others require separate installation.

Source: `VeraGridEngine/enumerations.py` lines 294-322

### Data Model

#### MultiCircuit (Central Container)

`MultiCircuit` inherits from `Assets` and is the primary container for all grid data.

Key constructor parameters:
- `name: str` -- grid name
- `Sbase: float = 100` -- base power in MVA
- `fbase: float = 50.0` -- base frequency in Hz
- `idtag: str` -- UUID identifier

Source: `VeraGridEngine/Devices/multi_circuit.py` line 125

#### Bus

Class: `VeraGridEngine.Devices.Substation.bus.Bus`

Key parameters:
- `Vnom: float` -- nominal voltage (kV)
- `vmin/vmax: float` -- voltage limits (p.u., default 0.9/1.1)
- `angle_min/angle_max: float` -- angle limits (rad)
- `is_slack: bool` -- slack bus designation
- `is_dc: bool` -- DC bus flag
- `Vm0/Va0: float` -- initial voltage guess (p.u. / rad)
- `area: Area`, `zone: Zone`, `country: Country` -- aggregation references
- `substation: Substation`, `voltage_level: VoltageLevel` -- substation hierarchy
- `longitude/latitude: float` -- geographic coordinates
- `ph_a/ph_b/ph_c/ph_n` -- phase flags for unbalanced analysis

Source: `VeraGridEngine/Devices/Substation/bus.py`

#### Generator

Class: `VeraGridEngine.Devices.Injections.generator.Generator`

Key parameters:
- `P: float` -- active power (MW)
- `power_factor: float` -- power factor (default 0.8)
- `vset: float` -- voltage setpoint (p.u.)
- `Pmin/Pmax: float` -- active power limits (MW)
- `Qmin/Qmax: float` -- reactive power limits (MVAr)
- `Snom: float` -- nominal apparent power (MVA)
- `Cost/Cost2/Cost0: float` -- generation cost coefficients (linear, quadratic, constant)
- `StartupCost/ShutdownCost: float` -- UC cost parameters
- `MinTimeUp/MinTimeDown: float` -- UC time constraints
- `RampUp/RampDown: float` -- ramp rate limits
- `enabled_dispatch: bool` -- dispatchable in OPF
- `must_run: bool` -- must-run constraint
- `R1/X1/R0/X0/R2/X2: float` -- sequence impedances (for short-circuit)
- `is_controlled: bool` -- voltage control enabled
- Dynamic parameters: `M` (inertia), `D` (damping), `Sbase`, `freq`

Source: `VeraGridEngine/Devices/Injections/generator.py`

#### Other Device Types

Devices are organized under `VeraGridEngine/Devices/`:

**Injection Devices** (attached to buses):
- `Load` -- ZIP model (constant impedance/current/power), star/delta configurations
- `Generator` -- dispatchable generation with cost curves
- `Battery` -- storage with state-of-charge tracking
- `StaticGenerator` -- non-dispatchable generation (wind/solar)
- `Shunt` -- fixed reactive compensation
- `ControllableShunt` -- switchable reactive compensation
- `CurrentInjection` -- current source injection
- `ExternalGrid` -- grid equivalent / slack source

**Branch Devices** (connect buses):
- `Line` -- transmission/distribution line (pi-model)
- `Transformer2W` -- two-winding transformer with tap changer
- `Transformer3W` -- three-winding transformer (modeled with middle bus)
- `Switch` -- switching device
- `SeriesReactance` -- series compensation
- `Winding` -- individual winding (for 3W transformer)
- `HvdcLine` -- simplified HVDC link (2-generator model)
- `VSC` -- Voltage Source Converter (detailed AC-DC model)
- `UPFC` -- Unified Power Flow Controller
- `DcLine` -- DC network branch

**Aggregation Devices:**
- `Area`, `Zone`, `Country`, `Region`, `Community`, `Municipality`
- `ContingencyGroup`, `Contingency`
- `InvestmentsGroup`, `Investment`
- `RemedialActionGroup`, `RemedialAction`

**Fluid Devices** (for hydro OPF):
- `FluidNode` -- reservoir with min/max levels and inflow
- `FluidPath` -- connection between fluid nodes
- `FluidTurbine` -- hydro turbine (fluid to electric)
- `FluidPump` -- pump (electric to fluid)
- `FluidP2X` -- power-to-X device

**Substation Hierarchy:**
- `Substation` > `VoltageLevel` > `BusBar` > `Bus`

Source: `VeraGridEngine/Devices/` directory listing

#### Adding Devices to a Grid

Devices are added via typed `add_*` methods on `MultiCircuit`/`Assets`:

```python
grid = vge.MultiCircuit(name="test", Sbase=100, fbase=60.0)
bus1 = grid.add_bus(vge.Bus(name="Bus 1", Vnom=230))
bus2 = grid.add_bus(vge.Bus(name="Bus 2", Vnom=230))
grid.add_generator(vge.Generator(name="Gen 1", P=100, Cost=10.0), bus=bus1)
grid.add_load(vge.Load(name="Load 1", P=80, Q=20), bus=bus2)
grid.add_line(vge.Line(bus_from=bus1, bus_to=bus2, name="Line 1-2", r=0.01, x=0.1, b=0.02, rate=200))
```

Source: `VeraGridEngine/Devices/assets.py` (add methods at lines 754+)

### OPF Formulations

#### DC OPF (Linear)

Entry point: `vge.linear_opf(grid, options)` or `OptimalPowerFlowDriver`

Default solver: `SolverType.LINEAR_OPF` with `MIPSolvers.HIGHS`

Formulation (from docs):
- **Variables:** Generator active power (Pg), voltage angles (theta), load/generation shedding slacks, branch flow slacks
- **Objective:** Minimize generation cost + slack penalties
- **Constraints:** Nodal power balance via susceptance matrix, branch flow limits (both directions), generator P limits
- **Power injection:** `P = C_bus_gen * Pg + C_bus_bat * Pb - C_bus_load * (LSlack + Load)`

OPF options relevant to DC OPF:
- `consider_contingencies: bool` -- add N-1 security constraints
- `skip_generation_limits: bool` -- relax generator bounds
- `consider_ramps: bool` -- add ramp constraints (time-series)
- `consider_time_up_down: bool` -- add min up/down time (UC)
- `area_spinning_reserve: bool` -- reserve constraints
- `dispatch_mode: OpfDispatchMode` -- Normal, UnitCommitment, InterAreaRedispatch, NodalCapacity, GenerationExpansionPlanning
- `add_losses_approximation: bool` -- approximate losses in linear formulation

Time-series OPF: `OptimalPowerFlowTimeSeriesDriver` solves multi-period dispatch with temporal coupling.

Source: `VeraGridEngine/Simulations/OPF/opf_options.py`, [OPF docs](https://veragrid.readthedocs.io/en/stable/md_source/optimal_power_flow.html)

#### AC OPF (Nonlinear)

Entry point: `vge.nonlinear_opf(grid, options)`

Uses custom interior-point solver (IPS) with Newton-Raphson iterations on KKT system.

Configuration via `OptimalPowerFlowOptions`:
- `solver=SolverType.NONLINEAR_OPF`
- `ips_tolerance: float = 1e-4` -- convergence threshold
- `ips_iterations: int = 100` -- max Newton steps
- `ips_trust_radius: float = 1.0` -- step scaling
- `ips_init_with_pf: bool` -- initialize from power flow solution
- `ips_control_q_limits: bool` -- enforce reactive bounds
- `acopf_mode: AcOpfMode` -- `ACOPFstd`, `ACOPFslacks`, `ACOPFMaxInjections`

Extended variables (beyond DC): bus voltage magnitudes, generator Q, transformer taps (module and phase), HVDC power, soft constraint slacks.

Results include Lagrange multipliers: `lam_p` (active), `lam_q` (reactive) -- these are the nodal prices / shadow prices.

Source: `VeraGridEngine/Simulations/OPF/ac_opf_worker.py`, `VeraGridEngine/Simulations/OPF/Formulations/ac_opf_problem.py`

### Supported Problem Formulations Summary

| Analysis | Snapshot | Time-Series | Notes |
|----------|----------|-------------|-------|
| AC Power Flow | `power_flow()` | `power_flow_ts()` | 13 solver algorithms |
| DC Power Flow | `power_flow(options=PFO(solver_type=SolverType.Linear))` | Same | Linear approximation |
| 3-Phase Unbalanced PF | `power_flow3ph()` | -- | ABC phase model |
| DC OPF | `linear_opf()` | `OptimalPowerFlowTimeSeriesDriver` | MIP-based, supports UC |
| AC OPF | `nonlinear_opf()` | -- | Interior-point solver |
| Greedy Dispatch | `simple_opf()` | -- | Heuristic dispatch |
| Linear Analysis (PTDF/LODF) | `linear_power_flow()` | `linear_power_flow_ts()` | Sensitivity factors |
| Contingency Analysis | `ContingencyAnalysisDriver` | `contingencies_ts()` | Linear, PF, OPF, or HELM methods |
| Short Circuit | `short_circuit()` | -- | Sequence & 3-phase methods |
| Continuation PF | `continuation_power_flow()` | -- | Voltage stability / PV curves |
| State Estimation | `StateEstimationDriver` | -- | Weighted least squares |
| Stochastic PF | `StochasticPowerFlowDriver` | -- | Monte Carlo / Latin Hypercube |
| Small-Signal Stability | `SmallSignalStabilityDriver` | -- | Eigenvalue analysis |
| Investment Optimization | `InvestmentsEvaluationDriver` | -- | MVRSM + MIP |
| Reliability | `ReliabilityDriver` | -- | Sequential Monte Carlo |
| Net Transfer Capacity | `NTCDriver` | `NTCTimeSeriesDriver` | Inter-area capacity |
| Nodal Hosting Capacity | `NodalCapacityTimeSeriesDriver` | Yes | Max DER injection |
| RMS Dynamic Simulation | `RmsDynamicDriver` | -- | Electromechanical transients |
| Clustering | `clustering()` | -- | Time-series reduction |

### Input/Output Formats

#### Supported Import Formats

| Format | Extensions | Parser Module |
|--------|-----------|---------------|
| MATPOWER | `.m` | `IO/matpower/` |
| PSS/e RAW | `.raw` (v29-35) | `IO/raw/raw_parser_writer.py` |
| PSS/e RAWX | `.rawx` | `IO/raw/rawx_parser_writer.py` |
| CIM 16 | `.xml`, `.zip` | `IO/cim/cim16/` |
| CGMES 2.4.15/3.0 | `.xml`, `.zip` | `IO/cim/cgmes/` |
| DigiSilent | `.dgs` | `IO/dgs/` |
| PSLF (PowerWorld) | `.epc` | `IO/epc/` |
| UCTE | `.uct` | `IO/ucte/` |
| IIDM (PowSyBl) | `.xiidm` | `IO/iidm/` |
| PyPSA | `.nc`, `.h5` | `IO/others/pypsa_parser.py` |
| pandapower | `.json` | `IO/others/pandapower_parser.py` |
| DPX | `.dpx` | `IO/others/dpx_parser.py` |
| iPA | `.ipa` | `IO/others/ipa_parser.py` |
| RTE XML | `.xml` | `IO/others/rte_parser.py` |
| ANAREDE (PWF) | `.pwf` | `IO/others/anarede.py` |
| Native VeraGrid | `.veragrid`, `.xlsx`, `.json`, `.ejson`, `.sqlite`, `.h5` | `IO/veragrid/` |

Source: `VeraGridEngine/IO/file_open.py` imports and `FileType` enum

#### Supported Export Formats

| Format | Notes |
|--------|-------|
| Native `.veragrid` | SQLite-based binary format |
| Excel `.xlsx` | Multiple sheet versions (v1-v4) |
| JSON `.json` / `.ejson` | Serialized grid model |
| CGMES | 2.4.15 and 3.0 with profile selection |
| PSS/e `.raw` / `.rawx` | Via raw_parser_writer |

Source: `VeraGridEngine/api.py` (`save_file`, `save_cgmes_file`), `FileType` enum

### Result Access Patterns

#### PowerFlowResults

```python
results = vge.power_flow(grid)

# Direct numpy array access
results.voltage          # CxVec -- complex bus voltages (p.u.)
results.Sbus             # CxVec -- complex bus power injections (MW + jMVAr)
results.Sf               # CxVec -- complex "from" branch flows
results.St               # CxVec -- complex "to" branch flows
results.loading          # CxVec -- branch loading (fraction)
results.losses           # CxVec -- branch losses (MW + jMVAr)
results.converged        # bool
results.error            # float -- convergence residual

# pandas DataFrame access
results.get_bus_df()     # columns: Vm, Va, P, Q
results.get_branch_df()  # columns: Pf, Qf, Pt, Qt, loading, Ploss, Qloss
```

Source: `VeraGridEngine/Simulations/PowerFlow/power_flow_results.py` lines 447+

#### OptimalPowerFlowResults (DC OPF)

```python
results = vge.linear_opf(grid)

results.voltage              # CxVec -- bus voltages
results.bus_shadow_prices    # Vec -- nodal prices (LMPs)
results.generator_power      # Vec -- generator dispatch (MW)
results.generator_shedding   # Vec -- generation curtailment
results.load_shedding        # Vec -- load shedding
results.Sf / results.St      # Vec -- branch flows (MW, real only)
results.loading              # Vec -- branch loading
results.overloads            # Vec -- branch overload slack
results.battery_power        # Vec -- battery dispatch
results.hvdc_Pf              # Vec -- HVDC flows
results.tap_angle / tap_module  # Vec -- transformer tap positions
results.converged            # bool
```

Source: `VeraGridEngine/Simulations/OPF/opf_results.py`

#### NonlinearOPFResults (AC OPF)

```python
results = vge.nonlinear_opf(grid)

results.Vm / results.Va      # Vec -- voltage magnitude/angle
results.voltage               # CxVec -- complex voltage
results.Pg / results.Qg       # Vec -- generator P/Q dispatch
results.Sf / results.St       # CxVec -- complex branch flows
results.lam_p / results.lam_q # Vec -- dual variables (nodal prices)
results.tap_module / results.tap_phase  # Vec -- transformer controls
results.hvdc_Pf               # Vec -- HVDC dispatch
results.converged              # bool
results.error                  # float
results.iterations             # int
```

Source: `VeraGridEngine/Simulations/OPF/Formulations/ac_opf_problem.py` lines 25-120

#### LinearAnalysisResults (PTDF/LODF)

```python
results = vge.linear_power_flow(grid)

results.PTDF     # Mat (n_branch x n_bus) -- Power Transfer Distribution Factors
results.LODF     # Mat (n_branch x n_branch) -- Line Outage Distribution Factors
results.Sf       # Vec -- branch flows
results.Sbus     # Vec -- bus injections
results.HvdcDF   # Mat -- HVDC distribution factors
results.VscDF    # Mat -- VSC distribution factors
```

Source: `VeraGridEngine/Simulations/LinearFactors/linear_analysis_results.py`

### Simulation Types (Complete List)

The `SimulationTypes` enum (lines 2076+) catalogs all 35+ simulation types, including:
PowerFlow, PowerFlow3ph, StateEstimation, ShortCircuit, MonteCarlo, PowerFlowTimeSeries,
ContinuationPowerFlow, LatinHypercube, StochasticPowerFlow, Cascade, OPF, OPF_NTC,
OPFTimeSeries, TransientStability, TopologyReduction, LinearAnalysis, NonLinearAnalysis,
ContingencyAnalysis, NetTransferCapacity, InvestmentsEvaluation, NodalCapacity, Reliability,
RmsDynamic, SmallSignal, and more.

Source: `VeraGridEngine/enumerations.py` lines 2076-2145

## Sources

1. [VeraGrid GitHub Repository (README)](https://github.com/SanPen/VeraGrid)
2. [VeraGridEngine on PyPI](https://pypi.org/project/VeraGridEngine/)
3. [VeraGrid Documentation -- Grid Modelling](https://veragrid.readthedocs.io/en/latest/md_source/modelling.html)
4. [VeraGrid Documentation -- Optimal Power Flow](https://veragrid.readthedocs.io/en/stable/md_source/optimal_power_flow.html)
5. [VeraGrid Documentation -- Main Page](https://veragrid.readthedocs.io/en/latest/)
6. Installed source: `VeraGridEngine/api.py` (v5.6.28)
7. Installed source: `VeraGridEngine/enumerations.py` (v5.6.28)
8. Installed source: `VeraGridEngine/Devices/multi_circuit.py`
9. Installed source: `VeraGridEngine/Devices/Substation/bus.py`
10. Installed source: `VeraGridEngine/Devices/Injections/generator.py`
11. Installed source: `VeraGridEngine/Simulations/PowerFlow/power_flow_options.py`
12. Installed source: `VeraGridEngine/Simulations/PowerFlow/power_flow_results.py`
13. Installed source: `VeraGridEngine/Simulations/OPF/opf_options.py`
14. Installed source: `VeraGridEngine/Simulations/OPF/opf_results.py`
15. Installed source: `VeraGridEngine/Simulations/OPF/Formulations/ac_opf_problem.py`
16. Installed source: `VeraGridEngine/Simulations/OPF/ac_opf_worker.py`
17. Installed source: `VeraGridEngine/Simulations/LinearFactors/linear_analysis_results.py`
18. Installed source: `VeraGridEngine/IO/file_open.py`
19. Installed source: `VeraGridEngine/__version__.py`
20. [GridCal GitHub Repository (original)](https://github.com/SanPen/GridCal)

## Gaps and Uncertainties

- **SCUC/SCED as distinct formulations:** Unit commitment appears as a dispatch mode (`OpfDispatchMode.UnitCommitment`) within the same `OptimalPowerFlowDriver`, not as a separate driver. Need to verify during testing whether binary variables, min-up/down times, and startup costs are actually implemented in the MIP formulation or just exposed as options.

- **AC OPF scalability:** The custom interior-point solver is pure Python/NumPy. Performance on large networks (1000+ buses) needs empirical testing. No evidence of compiled (C/Fortran) solver integration for the AC OPF path.

- **Time-series AC OPF:** The `nonlinear_opf()` API function does not have a time-series variant. It is unclear whether `OptimalPowerFlowTimeSeriesDriver` supports `SolverType.NONLINEAR_OPF` or only linear formulations.

- **Generator cost curves:** The generator model has `Cost` (linear), `Cost2` (quadratic), and `Cost0` (constant) parameters. The DC OPF documentation shows only linear cost in the objective. Need to verify whether quadratic cost is supported in DC OPF or only in AC OPF.

- **External solver engines:** `EngineType` lists Bentayga, NewtonPA, PGM, and GSLV as alternative computation backends, but these are not bundled. Need to verify which are available and what they add.

- **RMS Dynamic Simulation:** Listed in SimulationTypes but the maturity/completeness is unclear. The contributors list mentions dynamic model hosts and events, but documentation coverage is sparse.

- **Sparse documentation for advanced features:** State estimation, stochastic PF, reliability, and investment optimization have dedicated drivers but limited API documentation. The primary documentation source is the source code itself.

- **pandapower and PyPSA import fidelity:** Parsers exist (`pandapower_parser.py`, `pypsa_parser.py`) but round-trip fidelity and supported device subset are not documented.

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

---

## Extensions & Architecture

## Key Findings

- **Three-tier architecture** with clear separation: object-oriented data model (`MultiCircuit`/`Assets`), compiled numerical arrays (`NumericalCircuit`), and structured results (`ResultsTemplate`). This is a deliberate design choice to separate human-friendly modeling from computation-friendly arrays.
- **Plugin system exists** but lives in the GUI package (`VeraGrid`), not the engine (`VeraGridEngine`). Plugins are JSON-declared Python files placed in `~/.VeraGrid/plugins/`, with two hook points: a `main_fcn` (general-purpose, receives the `MainGUI` instance) and an `investments_fcn` (receives `InvestmentsEvaluationDriver`).
- **No formal callback/hook API** in the engine itself. The `DriverTemplate` base class uses Qt-compatible signal placeholders (`DummySignal`) for progress/done reporting, but these are not extensible event hooks. There is no pre/post-simulation callback mechanism.
- **NetworkX is a first-class dependency.** `MultiCircuit.build_graph()` returns a `nx.MultiDiGraph` with buses as nodes and branches as weighted edges (weight = reactance). A directed power-flow graph variant (`build_graph_real_power_flow()`) is also provided.
- **DataFrame interoperability is strong.** Results can be exported to `pd.DataFrame` via `ResultsTable.to_df()`, power flow results via `PowerFlowResults.export_all()`, and profiles via `MultiCircuit.export_profiles()`. Pandas is used throughout for time series handling.
- **No user-facing API to add custom OPF constraints.** The LP/MIP formulations are hard-coded in `Simulations/OPF/Formulations/`. Users cannot inject constraints without modifying source code. The MIP interface abstracts solver choice (PuLP, OR-Tools, HiGHS) but not the formulation.
- **Multi-engine architecture** supports five computation backends via `EngineType` enum: VeraGrid (native), Bentayga, NewtonPA, PGM (Power Grid Model), and GSLV. Backend selection is per-driver, and each has a dedicated compiler (`circuit_to_*.py`).
- **Rich import/export format support:** MATPOWER (.m), PSS/e RAW/RAWX, CIM/CGMES, DGS, EPC, IIDM, UCTE, pandapower (pickle/JSON/SQLite), PyPSA, and native VeraGrid (.veragrid/.ejson). Parsers for pandapower and PyPSA perform bidirectional conversion.
- **Sparse matrix access** is available through `MultiCircuit.get_bus_branch_connectivity_matrix()` (returns Cf, Ct, C) and `get_adjacent_matrix()`. The admittance matrix (Ybus) is built inside `NumericalCircuit` via the `Topology/admittance_matrices.py` module.
- **866 Python source files** in the engine package; monolithic but well-organized into Devices, Simulations, DataStructures, Compilers, IO, Topology, Utils, and Templates.

## Detailed Notes

### Internal Architecture and Separation of Concerns

The architecture follows a three-layer design documented in the official structure page:

1. **`MultiCircuit` (Data Model Layer):** An object-oriented "database" inheriting from `Assets`. Contains lists of device objects (buses, lines, generators, loads, etc.) with full property metadata, UUIDs, and profile support. Objects reference each other directly (e.g., a branch references its `bus_from` and `bus_to` objects). This layer is human-readable and GUI-friendly. Source: `VeraGridEngine/Devices/multi_circuit.py` (3199 lines), `VeraGridEngine/Devices/assets.py`.

2. **`NumericalCircuit` (Computation Layer):** A compiled snapshot of the data model at a specific time step. Contains typed numpy arrays and sparse matrices organized into data structures (`BusData`, `PassiveBranchData`, `GeneratorData`, etc.). Created by the compiler (`Compilers/circuit_to_data.py`). Multiple NumericalCircuits can exist independently for safe parallelism. Source: `VeraGridEngine/DataStructures/numerical_circuit.py`.

3. **`ResultsTemplate` (Results Layer):** Structured output container. Each simulation type has its own results class (e.g., `PowerFlowResults`, `OptimalPowerFlowResults`) inheriting from `ResultsTemplate`. Results never overwrite input data. Each result variable is registered with type information for serialization. Source: `VeraGridEngine/Simulations/results_template.py`.

The compilation step (`compile_numerical_circuit_at()`) converts the object-oriented model to array-oriented numerical data, which is documented as a deliberate design to separate "management convenience from computational speed."

Sources:
- [VeraGrid Structure Documentation](https://veragrid.readthedocs.io/en/latest/md_source/structure.html)
- `VeraGridEngine/Compilers/circuit_to_data.py`
- `VeraGridEngine/DataStructures/numerical_circuit.py`

### Driver Pattern (Simulation Execution)

All simulations follow a uniform Driver pattern:

```
Driver = SomeDriver(grid=MultiCircuit, options=SomeOptions, ...)
Driver.run()
results = Driver.results  # SomeResults instance
```

The `DriverTemplate` base class (`Simulations/driver_template.py`) provides:
- Progress reporting via `DummySignal` placeholders (compatible with Qt signals when used in GUI)
- Timing (`tic()`/`toc()`)
- Cancellation support (`cancel()`, `is_cancel()`)
- Serialization via `get_save_data() -> DriverToSave`
- Logger for warnings/errors

`TimeSeriesDriverTemplate` extends this with time indexing and clustering support.

The `driver_handler.py` module provides a factory function `create_driver()` that instantiates drivers by `SimulationTypes` enum, useful for deserialization.

Source: `VeraGridEngine/Simulations/driver_template.py`, `VeraGridEngine/Simulations/driver_handler.py`

### Plugin System

The plugin system is documented at [VeraGrid Plugins Documentation](https://veragrid.readthedocs.io/en/latest/md_source/plugins.html).

**Plugin structure** requires three files in `~/.VeraGrid/plugins/`:
- `plugins.plugin.json` — declares name, path, icon, and function entry points
- `plugin.py` — the Python implementation
- `icon.svg` — optional custom icon

**Two hook points:**
1. `main_fcn`: Receives the `MainGUI` instance, giving full access to the circuit object and all GUI controls. This is a general-purpose extension point.
2. `investments_fcn`: Receives an `InvestmentsEvaluationDriver` instance. This is used when `InvestmentEvaluationMethod.FromPlugin` is selected, enabling custom investment optimization algorithms.

**Installation:** Drag-and-drop `.vgplugin` files into the GUI.

**Limitation:** The plugin system is entirely GUI-side. The engine (`VeraGridEngine`) has no plugin infrastructure. The `plugins_path()` function in `IO/file_system.py` merely returns the filesystem path `~/.VeraGrid/plugins/` — there is no plugin loader, registry, or lifecycle management in the engine.

The `InvestmentsEvaluationOptions.plugin_fcn_ptr` is the only engine-level callback, accepting a `Callable` that receives the `InvestmentsEvaluationDriver`:

```python
# In investments_evaluation_driver.py, line 319:
elif self.options.solver == InvestmentEvaluationMethod.FromPlugin:
    self.options.plugin_fcn_ptr(self)
```

Source: `VeraGridEngine/IO/file_system.py` (line 36), `VeraGridEngine/Simulations/InvestmentsEvaluation/investments_evaluation_options.py`, `VeraGridEngine/Simulations/InvestmentsEvaluation/investments_evaluation_driver.py` (line 319)

### NetworkX Graph Access

`MultiCircuit` imports and uses `networkx` directly:

**`build_graph() -> nx.MultiDiGraph`** (line 368 of `multi_circuit.py`):
- Nodes = bus indices (integers)
- Edges = branches (lines, transformers, DC lines, HVDC, switches) with weight = reactance (X)
- Returns a `MultiDiGraph` allowing parallel edges

**`build_graph_real_power_flow(current_flow) -> nx.DiGraph`** (line 407):
- Directed graph based on actual power flow direction
- Requires solved power flow results (`current_flow` array)

**`plot_graph()`** (line 741): Uses `nx.draw_spring()` for quick visualization.

NetworkX is also used internally in topology detection algorithms. The package imports `import networkx as nx` at the top of `multi_circuit.py`.

Source: `VeraGridEngine/Devices/multi_circuit.py` lines 14, 368-430

### DataFrame and Data Export

**Results to DataFrame:**
- `ResultsTable.to_df() -> pd.DataFrame` — converts any results table to a DataFrame
- `ResultsTable.get_data_frame() -> pd.DataFrame` — alias for the above
- `ResultsTable.save_to_excel(filename)` and `save_to_csv(filename)` — direct file export
- `PowerFlowResults.export_all() -> (df_bus, df_branch)` — returns bus and branch result DataFrames

**Model data to DataFrame:**
- `MultiCircuit.export_pf(filename, results)` — exports power flow results to Excel with bus and branch sheets
- `MultiCircuit.export_profiles(filename)` — exports load/generator profiles to Excel as DataFrames
- `TapChanger.to_df() -> pd.DataFrame` — individual device DataFrame export
- `LineLocations.to_df() -> pd.DataFrame` — geographic line coordinate export

**Results serialization:**
- `ResultsTemplate.get_dict()` and `parse_data()` — JSON-compatible dict conversion for all registered result variables
- `ResultsTemplate.to_json(filename)` — direct JSON export

Pandas is a core dependency used throughout for time indexing (`pd.DatetimeIndex`) and tabular data.

Source: `VeraGridEngine/Simulations/results_table.py`, `VeraGridEngine/Simulations/results_template.py`, `VeraGridEngine/Devices/multi_circuit.py` (lines 743-800)

### Sparse Matrix and Admittance Matrix Access

**Connectivity matrices:**
- `MultiCircuit.get_bus_branch_connectivity_matrix() -> (Cf, Ct, C)` — returns from-bus, to-bus, and combined incidence matrices as `csc_matrix`
- `MultiCircuit.get_adjacent_matrix() -> csc_matrix` — bus adjacency matrix (C^T @ C)

**Admittance matrix:**
- Built inside `NumericalCircuit` via `Topology/admittance_matrices.py`
- Uses numba-JIT compiled functions for performance
- Accessible after compilation: `nc = compile_numerical_circuit_at(grid, t_idx=None)` then access `nc` data structures

The topology module (`Topology/topology.py`) implements island detection using numba-optimized DFS on CSC sparse matrices, independent of NetworkX.

Source: `VeraGridEngine/Devices/multi_circuit.py` (lines 878-920), `VeraGridEngine/Topology/admittance_matrices.py`, `VeraGridEngine/Topology/topology.py`

### OPF Constraint Architecture

The OPF is implemented in `Simulations/OPF/Formulations/`:
- `linear_opf_ts.py` — DC-OPF for time series using MIP solver
- `ac_opf_problem.py` — AC-OPF formulation
- `linear_opf_ts_b.py` — alternative linear OPF variant

The MIP interface (`Utils/MIP/selected_interface.py`) abstracts across:
- PuLP (always available)
- OR-Tools (optional)
- HiGHS (via SimpleMip)

Constraints are built programmatically inside the formulation functions (e.g., Kirchhoff balance, generator limits, branch flow limits). There is **no user-facing API to add custom constraints**. Modifying the OPF requires editing the formulation source files directly.

Solver selection is via `MIPSolvers` and `MIPFramework` enums in the options.

Source: `VeraGridEngine/Simulations/OPF/Formulations/linear_opf_ts.py`, `VeraGridEngine/Utils/MIP/selected_interface.py`

### Multi-Engine Support

The `EngineType` enum defines five computation backends:

| Engine | Compiler | Description |
|--------|----------|-------------|
| `VeraGrid` | `circuit_to_data.py` | Native Python/NumPy/Numba engine |
| `Bentayga` | `circuit_to_bentayga.py` | External C++ engine |
| `NewtonPA` | `circuit_to_newton_pa.py` | Newton Power Analytics |
| `PGM` | `circuit_to_pgm.py` | Power Grid Model (C library) |
| `GSLV` | `circuit_to_gslv.py` | GSLV engine |

Each compiler translates the `MultiCircuit` into the target engine's native data format. Engine selection is per-driver call. This is a form of extensibility — new engines can be added by creating a new compiler module and adding an `EngineType` enum value, though it requires modifying the engine source code.

Source: `VeraGridEngine/enumerations.py` (line 294), `VeraGridEngine/Compilers/`

### Import/Export Format Interoperability

**Import parsers (IO module):**
- MATPOWER `.m` files (`IO/matpower/`)
- PSS/e RAW and RAWX (`IO/raw/`)
- CIM/CGMES XML (`IO/cim/`)
- DGS (DIgSILENT) (`IO/dgs/`)
- EPC (`IO/epc/`)
- IIDM (`IO/iidm/`)
- UCTE-DEF (`IO/ucte/`)
- pandapower pickle/JSON/SQLite (`IO/others/pandapower_parser.py`)
- PyPSA Network objects (`IO/others/pypsa_parser.py`)
- ANAREDE (`IO/others/anarede.py`)
- RTE (`IO/others/rte_parser.py`)

**Export formats:**
- Native VeraGrid (`.veragrid`, `.ejson`, `.xlsx`)
- CGMES
- PSS/e RAW/RAWX

**pandapower interop:** The parser (`IO/others/pandapower_parser.py`) requires pandapower to be installed. It can read pandapower pickles, JSON, SQLite, and Excel files and convert them to `MultiCircuit`. Auto-detection functions (`is_pandapower_pickle()`, etc.) are provided.

**PyPSA interop:** The parser (`IO/others/pypsa_parser.py`) converts a `pypsa.Network` object into a `MultiCircuit`, handling buses, lines, transformers, generators, loads, HVDC links, batteries, and shunts. It handles coordinate projection (EPSG conversion) and time series profiles. PyPSA must be installed as an optional dependency.

Source: `VeraGridEngine/IO/others/pandapower_parser.py`, `VeraGridEngine/IO/others/pypsa_parser.py`

### Dynamic Simulation Framework

The `Devices/Dynamic/` module provides a block-diagram-based RMS (Root Mean Square) dynamic simulation framework:
- `DynamicModelHost` — container for block diagram models
- `BlockDiagramNode` / `BlockDiagramConnection` — graph structure for dynamic model topology
- `RmsModelTemplate` — templates for dynamic component models
- Templates in `Templates/Rms/` for generators, loads, lines, buses

The `Utils/Symbolic/` module provides a custom symbolic math engine for generating numba-compiled dynamic equations from block diagrams, enabling user-defined dynamic models.

Source: `VeraGridEngine/Devices/Dynamic/dynamic_model_host.py`, `VeraGridEngine/Utils/Symbolic/`

## Sources

1. VeraGridEngine 5.6.28 source code installed at `/workspace/evaluations/gridcal/.venv/lib/python3.12/site-packages/VeraGridEngine/`
2. [VeraGrid GitHub Repository](https://github.com/SanPen/VeraGrid)
3. [VeraGrid Documentation — Structure](https://veragrid.readthedocs.io/en/latest/md_source/structure.html)
4. [VeraGrid Documentation — Plugins](https://veragrid.readthedocs.io/en/latest/md_source/plugins.html)
5. [VeraGrid Documentation — User Interface](https://veragrid.readthedocs.io/en/stable/md_source/user_interface.html)
6. [VeraGrid Documentation — Main Page](https://veragrid.readthedocs.io/en/latest/)
7. [VeraGrid README.md](https://github.com/SanPen/VeraGrid/blob/master/README.md)
8. [GridCal API Demo](https://gridcal.readthedocs.io/en/latest/rst_source/getting_started/api_demo.html)

## Gaps and Uncertainties

- **Plugin system details in the GUI package are not inspectable** from the engine-only install (`VeraGridEngine`). The full plugin loader, registry, and lifecycle management presumably reside in the `VeraGrid` GUI package, which is not installed in this evaluation environment.
- **Custom constraint injection for OPF** appears unsupported without source modification. This should be verified during testing by attempting to subclass or wrap the OPF formulation.
- **No Graphs.jl interoperability** — GridCal is Python-only; there is no Julia interface or bridge. NetworkX is the graph library.
- **The multi-engine backends (Bentayga, NewtonPA, PGM, GSLV)** are optional commercial or third-party packages. Their availability and integration depth should be tested, but the compilers exist in source.
- **DataFrame export from the data model** (as opposed to results) is limited. There is no `MultiCircuit.buses_to_df()` or similar. Users would need to iterate device lists manually or use the `registered_properties` metadata to construct DataFrames. The `export_profiles()` method provides DataFrame-based profile export but not full model export.
- **The symbolic/block-diagram dynamic simulation framework** appears to be a newer addition. Its maturity and completeness relative to the static analysis features is unclear from code inspection alone.
- **Version context:** This analysis is based on VeraGridEngine 5.6.28. The project was renamed from GridCal/GridCalEngine to VeraGrid/VeraGridEngine. Some documentation URLs still reference "gridcal" in their paths.

---

## Limitations & Ecosystem

### Key Findings

- **Project renamed from GridCal to VeraGrid in early 2026.** The PyPI package `GridCalEngine` (200k+ total downloads) is frozen at v5.4.1 with a deprecation notice. The new package is `veragridengine` (~23k total downloads as of March 2026). No compatibility shim exists; all import paths changed. ([install-findings.md](../notes/install-findings.md))
- **Extreme contributor concentration (bus factor = 1).** Santiago Penate Vera (SanPen) accounts for 9,522 of 13,551 total commits (70.3%). The next two contributors combined have ~1,700 commits. Only 30 contributors lifetime. ([GitHub contributors API](https://github.com/SanPen/GridCal))
- **OPF has open correctness issues.** Issue [#397](https://github.com/SanPen/GridCal/issues/397): "Optimal power flow not fulfilling the constraints" (ramp rate and min up/down time constraints ignored). Issue [#430](https://github.com/SanPen/GridCal/issues/430): "ACOPF does not handle well non-dispatchable generation results" (solver crashes). Both open as of March 2026.
- **SCOPF is under development, not production-ready.** Issue [#364](https://github.com/SanPen/GridCal/issues/364) describes a workflow for running SCOPF with numerical circuits, posted by the maintainer as a roadmap item (April 2025, still open).
- **No native SCUC/unit commitment formulation.** The tool has an OPF with "unit commitment" option but ramp constraints do not compile with it (per issue #397). No standalone SCUC solver exists.
- **Heavy dependency tree (30+ runtime dependencies)** including opencv-python, windpowerlib, pvlib, geopy, rdflib, websockets -- many unrelated to core power flow. Dependency version conflicts produce runtime warnings (urllib3/chardet).
- **License changed from LGPL to MPL-2.0** in v5.2.0 (November 2024). MPL-2.0 is permissive with file-level copyleft -- generally government-friendly.
- **Documentation is broad but shallow.** ReadTheDocs covers many topics conceptually but API reference is auto-generated with minimal method-level documentation. Many code examples reference the old `GridCalEngine` import paths.
- **Active development with rapid release cadence.** 2,434 commits in the last 12 months. 10 tagged releases in the last 24 months. CI runs on GitHub Actions (scheduled + push).
- **Commercial backing via eRoots Analytics** (Barcelona), which sells GSLV (C++ accelerated version) and consulting services. The primary developer is CTO of eRoots.

## Detailed Notes

### Repository Statistics

| Metric | Value | Source |
|--------|-------|--------|
| GitHub stars | 516 | [GitHub API](https://github.com/SanPen/GridCal) |
| GitHub forks | 123 | [GitHub API](https://github.com/SanPen/GridCal) |
| Open issues | 29 | [GitHub API](https://github.com/SanPen/GridCal) |
| Total contributors | 30 | [GitHub API](https://github.com/SanPen/GridCal) |
| License | MPL-2.0 | [GitHub API](https://github.com/SanPen/GridCal) |
| Created | 2016-01-13 | [GitHub API](https://github.com/SanPen/GridCal) |
| Last push | 2026-02-24 | [GitHub API](https://github.com/SanPen/GridCal) |
| Commits (last 12 months) | ~2,434 | [GitHub API](https://github.com/SanPen/GridCal) |
| PyPI downloads (GridCalEngine, total) | ~200,570 | [pepy.tech](https://pepy.tech/projects/gridcalengine) |
| PyPI downloads (VeraGridEngine, total) | ~22,736 | [pepy.tech](https://pepy.tech/projects/veragridengine) |
| Installed version (this eval) | 5.6.28 | [pyproject.toml](../pyproject.toml) |
| Latest PyPI version | 5.6.30 | [PyPI](https://pypi.org/project/VeraGridEngine/) |

### Contributor Concentration

| Contributor | Commits | Percentage |
|-------------|---------|------------|
| SanPen (Santiago Penate) | 9,522 | 70.3% |
| JosepFanals | 1,223 | 9.0% |
| Carlos-Alegre | 478 | 3.5% |
| benceszirbik | 466 | 3.4% |
| alexblancoeroots | 286 | 2.1% |
| All others (25 contributors) | ~1,576 | 11.6% |

Top 3 contributors account for 82.8% of all commits. Several of the top contributors have "eroots" or appear to be eRoots employees. The bus factor is effectively 1.

Source: [GitHub contributors API](https://github.com/SanPen/GridCal)

### Package Rename: GridCal to VeraGrid

The project was renamed in early 2026. Key details:

- **v5.4.0** (tagged 2026-02-02) is labeled "Last GridCal" on GitHub releases.
- **v5.6.20** (tagged 2026-02-02) is the first VeraGrid-branded release.
- The PyPI package `GridCalEngine` is frozen at 5.4.1 and prints a deprecation warning on every import.
- The deprecation message contains a typo: "witch" instead of "which".
- The new package is `veragridengine` (import as `VeraGridEngine`).
- No backward-compatibility shim or migration tool exists.
- All documentation URLs shifted from `gridcal.readthedocs.io` to `veragrid.readthedocs.io`.
- The GitHub repository URL remains `SanPen/GridCal` (not renamed, but README now says "VeraGrid").

Source: [install-findings.md](../notes/install-findings.md), [GitHub releases](https://github.com/SanPen/GridCal/releases)

### Release History (Last 24 Months)

| Version | Date | Key Changes |
|---------|------|-------------|
| 5.6.20 | 2026-02-02 | First VeraGrid-branded release |
| v5.4.0 | 2026-02-02 | "Last GridCal" -- final release under old name |
| v5.3.0 | 2025-01-08 | Better topology and ACDC power flow |
| v5.2.0 | 2024-11-11 | Relicensed to MPL-2.0 |
| v5.1.20 | 2024-07-23 | "End of Siroco" |
| v5.1.10 | 2024-05-31 | Bug fixes |
| v5.1.7 | 2024-04-16 | Bug fixes |
| 5.1.0 | 2024-04-01 | ACOPF and sparse profiles |
| 5.0.11 | 2024-01-05 | Added fluid transport problem |
| 5.0.2 | 2023-11-18 | "The great split" -- GridCal (GUI) / GridCalEngine (engine) |

The project releases frequently but versioning does not strictly follow semver (multiple 5.x.y releases with significant changes).

Source: [GitHub releases](https://github.com/SanPen/GridCal/releases)

### Open Issues Related to Evaluation Tests

**OPF correctness (A-3, A-5, A-6, A-9 relevant):**
- [#397](https://github.com/SanPen/GridCal/issues/397) — "Optimal power flow not fulfilling the constraints": Ramp up/down constraints and min up/down time constraints are not enforced. UC mode disables ramp constraints entirely. Load shedding cannot be disabled. (Open, created 2025-06-04)
- [#430](https://github.com/SanPen/GridCal/issues/430) — "ACOPF does not handle well non-dispatchable generation results": Solver crashes when generators are set to `enabled_dispatch = False`. (Open, created 2025-09-17, zero comments)
- [#413](https://github.com/SanPen/GridCal/issues/413) — "Function add_linear_branches_contingencies_formulation should be reviewed" (Open)

**SCOPF (A-9 relevant):**
- [#364](https://github.com/SanPen/GridCal/issues/364) — "Run SCOPF with numerical circuit": Maintainer-authored roadmap issue describing the intended SCOPF workflow. Not yet implemented. (Open, created 2025-04-14)

**Other evaluation-relevant issues:**
- [#328](https://github.com/SanPen/GridCal/issues/328) — "Add AC-PTDF to Linear Analysis" (Open, feature request)
- [#386](https://github.com/SanPen/GridCal/issues/386) — "Load shedding": Unable to disable automatic load shedding in OPF (Open)
- [#414](https://github.com/SanPen/GridCal/issues/414) — "PSSE Exporting is not working" (Open)
- [#425](https://github.com/SanPen/GridCal/issues/425) — "Three-phase transformers - Combining star and delta connections" (Open)

### Dependency Tree

VeraGridEngine v5.6.28 has 29 direct runtime dependencies:

**Core numerical:** numpy, scipy, pandas, numba, scikit-learn, autograd
**Optimization:** highspy (HiGHS), pulp (CBC/GLPK interface), pymoo (multi-objective)
**File I/O:** xlwt, xlrd, openpyxl, pyarrow, h5py, chardet, rdflib
**Visualization:** matplotlib, opencv-python
**Domain-specific:** windpowerlib, pvlib, geopy, pyproj
**Networking:** websockets, brotli
**Build system (in runtime deps):** setuptools, wheel

Notable concerns:
- **opencv-python** is a large compiled dependency (>50MB) unusual for a power systems engine. Its presence in runtime deps rather than optional is questionable.
- **windpowerlib and pvlib** are domain-specific renewable energy libraries -- useful for some workflows but heavy for core power flow use cases.
- **setuptools and wheel in runtime deps** is non-standard.
- **urllib3/chardet version conflict** produces warnings on every import.

Source: `importlib.metadata.distribution('veragridengine').requires` inside devcontainer

### Features Claimed (from README)

- AC/DC multi-grid power flow
- 3-phase unbalanced power flow and short circuit
- AC/DC multi-grid linear optimal power flow
- AC linear analysis (PTDF & LODF)
- AC linear net transfer capacity calculation
- AC+HVDC optimal net transfer capacity calculation
- AC/DC Stochastic power flow
- AC Short circuit
- AC Continuation power flow
- Contingency analysis (Power flow and LODF variants)
- Sigma analysis (one-shot stability analysis)
- Investments analysis
- Time series and snapshot for most simulations
- Import: PSSe .raw/.rawx, epc, dgs, matpower, pypsa, json, cim, cgmes
- Export: veragrid .xlsx/.veragrid/.json, cgmes, psse .raw/.rawx

**Not claimed:** SCUC, unit commitment as a standalone formulation, stochastic OPF (stochastic power flow exists but is Monte Carlo simulation, not stochastic programming), LMP decomposition, distributed slack OPF, lossy DC OPF.

Source: [GitHub README](https://github.com/SanPen/VeraGrid/blob/master/README.md)

### Documentation Quality

**Strengths:**
- ReadTheDocs site exists at [veragrid.readthedocs.io](https://veragrid.readthedocs.io)
- Grid modeling tutorial covers bus creation, line definitions, transformer connections
- Changelog is maintained in documentation
- README has inline code examples for common tasks (load file, power flow, save)
- FOSDEM 2026 talk provides architectural context

**Weaknesses:**
- API reference is auto-generated from docstrings with minimal method-level documentation
- Many tutorials still reference `GridCalEngine` import paths (pre-rename)
- No dedicated OPF tutorial or optimization example in official docs
- No example for contingency analysis via the API
- Documentation version on ReadTheDocs (5.6.20) may lag PyPI (5.6.30)
- The "old" docs at `gridcal-wip.readthedocs.io` still exist with v3.5.3 content, creating confusion

Source: [veragrid.readthedocs.io](https://veragrid.readthedocs.io), [gridcal.readthedocs.io](https://gridcal.readthedocs.io)

### Commercial Context and Institutional Backing

- **eRoots Analytics** (Barcelona, Spain) is the commercial entity behind GridCal/VeraGrid.
- Santiago Penate Vera is CTO of eRoots and primary developer.
- eRoots sells **GSLV** (Grid SoLVer), a C++ accelerated commercial variant claiming "10x faster" performance.
- Santiago previously worked at DNV, Indra, and Red Electrica (Spain's TSO).
- The project has presented at **LF Energy Summit 2024** (Brussels) and **FOSDEM 2026**.
- GridCal received a **Solar Impulse Efficient Solution** label (certification for clean/profitable solutions).
- Academic testimonials from CIRCE (Spain), Rensselaer Polytechnic Institute (USA), and CITCEA-UPC (Spain).
- No evidence of utility/ISO operational deployment or government procurement.
- Listed on the **Open Energy Modelling Initiative** forum.
- Has a Zenodo DOI for academic citation.
- Discord server exists for community chat.

Source: [eroots.tech](https://eroots.tech/veragrid-gslv), [LF Energy](https://lfenergy.org/lf-energy-summit-recap-and-video-vision-for-power-systems-planning-the-gridcal-example/), [FOSDEM 2026](https://fosdem.org/2026/schedule/event/7ARG7Y-making_of_a_modern_power_systems_software/)

### CI and Testing

- GitHub Actions CI exists with scheduled runs and push-on-master triggers.
- Most recent scheduled run: 2026-03-02 (success).
- Most recent push run: 2026-02-24 (success).
- `pytest` is listed as a runtime dependency (unusual -- should be dev-only).
- Test suite exists in `src/tests/` in the repo.
- No visible test coverage metrics or badges.
- Codacy badge is present but its current grade is unknown.

Source: [GitHub Actions](https://github.com/SanPen/GridCal/actions)

### Accessibility Observations (from install-findings.md)

- DC power flow is invoked via `SolverType.Linear` -- the terms "DC" or "DCPF" do not appear in enum names.
- `EngineType` enum contains `Bentayga`, `GSLV`, `NewtonPA`, `PGM`, `VeraGrid` -- not self-explanatory.
- Native MATPOWER .m file reading works well: `vge.open_file("case39.m")`.
- No `__version__` attribute on the package (must use `importlib.metadata`).

Source: [install-findings.md](../notes/install-findings.md)

## Sources

1. [GitHub: SanPen/GridCal](https://github.com/SanPen/GridCal) -- repository, issues, releases, contributors
2. [PyPI: VeraGridEngine](https://pypi.org/project/VeraGridEngine/) -- package metadata
3. [pepy.tech: VeraGridEngine downloads](https://pepy.tech/projects/veragridengine)
4. [pepy.tech: GridCalEngine downloads](https://pepy.tech/projects/gridcalengine)
5. [VeraGrid ReadTheDocs](https://veragrid.readthedocs.io) -- official documentation
6. [eRoots: VeraGrid & GSLV](https://eroots.tech/veragrid-gslv) -- commercial context
7. [LF Energy Summit: GridCal presentation](https://lfenergy.org/lf-energy-summit-recap-and-video-vision-for-power-systems-planning-the-gridcal-example/)
8. [FOSDEM 2026: Making of a modern power systems software](https://fosdem.org/2026/schedule/event/7ARG7Y-making_of_a_modern_power_systems_software/)
9. [GitHub Issue #397: OPF not fulfilling constraints](https://github.com/SanPen/GridCal/issues/397)
10. [GitHub Issue #430: ACOPF crashes with non-dispatchable gen](https://github.com/SanPen/GridCal/issues/430)
11. [GitHub Issue #364: Run SCOPF with numerical circuit](https://github.com/SanPen/GridCal/issues/364)
12. [evaluations/gridcal/notes/install-findings.md](../notes/install-findings.md) -- local install findings
13. [Open Energy Modelling Initiative: GridCal](https://forum.openmod.org/t/gridcal-project/2420)

## Gaps and Uncertainties

- **SCUC capability unclear.** The tool claims OPF with unit commitment option, but issue #397 reports constraints are not enforced. Needs hands-on testing to determine if a working SCUC formulation exists.
- **Stochastic OPF vs stochastic power flow.** The README claims "stochastic power flow" which is Monte Carlo simulation, not stochastic programming. Whether scenario-tree-based stochastic OPF is possible needs testing.
- **LMP extraction.** No documentation or issues mention LMP decomposition. Needs source code inspection to determine if shadow prices are accessible from OPF results.
- **Distributed slack.** The changelog mentions "distributed slack" was added in v3.5.8, but no documentation explains API usage. Needs testing.
- **PTDF extraction.** PTDF analysis is a listed feature and has its own driver. Quality and API accessibility need testing.
- **Contingency analysis API.** Feature is listed and has a driver, but no API example exists in docs. Need to verify if N-1 can be run programmatically without the GUI.
- **Discord community size unknown.** The Discord server exists but member count is not publicly visible.
- **GSLV relationship to VeraGrid unclear.** Whether GSLV uses proprietary code that could affect VeraGrid's open-source completeness is not documented.
- **Test coverage metrics unavailable.** No coverage badges or reports are published.
- **Lossy DC OPF.** Not mentioned anywhere in docs, changelog, or issues. Likely unsupported.
- **Custom constraint API.** No documentation on adding user-defined constraints to OPF. Needs source code investigation.

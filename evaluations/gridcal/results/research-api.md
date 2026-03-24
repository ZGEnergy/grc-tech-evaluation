# gridcal — Research: API & Formulations

## Key Findings

- **GridCal has been rebranded to VeraGrid.** The PyPI package is `veragridengine` (v5.6.28 installed), and the Python module is `VeraGridEngine`. The API module at `VeraGridEngine.api` re-exports all public symbols.
- **Convenience functions in `api.py`** provide one-liner access to power flow, linear OPF, nonlinear (AC) OPF, short circuit, continuation power flow, contingency analysis, and clustering — each returning a typed results object.
- **DC/Linear OPF** uses PTDF-based formulation solved via PuLP or OR-Tools with configurable MIP solver backend (HiGHS default; also SCIP, CPLEX, Gurobi, Xpress, CBC, PDLP). Formulation includes unit commitment, generation expansion planning, inter-area redispatch, and nodal capacity modes.
- **AC (Nonlinear) OPF** uses a custom interior-point solver (IPS) operating on a `NonLinearOptimalPfProblem` class with analytical Jacobians and Hessians — not an external NLP solver.
- **Power flow supports ~14 solver algorithms** including Newton-Raphson, Gauss-Seidel, HELM, Fast Decoupled, Levenberg-Marquardt, Iwamoto-NR, Continuation-NR, BFS, Linear (DC), and Linear AC (LACPF).
- **Data model** is object-oriented: `MultiCircuit` contains lists of `Bus`, `Line`, `Transformer2W`, `Generator`, `Load`, `Battery`, `Shunt`, `HvdcLine`, `VSC`, etc. Buses are containers; branches connect buses.
- **Extensive I/O support:** reads MATPOWER `.m`, PSS/e `.raw`/`.rawx`, CGMES, CIM, DGS, EPC (PowerWorld), PyPSA, pandapower, UCTE, IIDM, DPX, IPA. Saves to `.veragrid`, `.xlsx`, `.json`, CGMES, PSS/e `.raw`/`.rawx`.
- **No SCUC/SCED as named abstractions.** Unit commitment is available as `OpfDispatchMode.UnitCommitment` within the linear OPF formulation (includes ramp constraints, min up/down time, startup/shutdown costs). There is no explicit SCED formulation separate from OPF.
- **Results access** is via typed result objects with numpy arrays: `PowerFlowResults.voltage`, `.Sf`, `.loading`, `.losses`; `OptimalPowerFlowResults.bus_shadow_prices`, `.generator_power`, `.overloads`, etc.
- **Time series is a first-class concept.** Most analyses have both snapshot and time-series variants. The grid stores time profiles via `Profile` objects attached to each device.

## Detailed Notes

### API Entry Points

The `VeraGridEngine.api` module (source: `VeraGridEngine/api.py`) provides these top-level convenience functions:

| Function | Description | Returns |
|---|---|---|
| `open_file(filename)` | Load grid from file | `MultiCircuit` |
| `save_file(grid, filename)` | Save grid to file | — |
| `power_flow(grid, options)` | Snapshot AC/DC power flow | `PowerFlowResults` |
| `power_flow3ph(grid, options)` | 3-phase unbalanced power flow | `PowerFlowResults3Ph` |
| `power_flow_ts(grid, options, time_indices)` | Time-series power flow | `PowerFlowResults` |
| `linear_power_flow(grid, options)` | Linear (PTDF-based) analysis | `LinearAnalysisResults` |
| `linear_power_flow_ts(grid, options)` | Linear analysis time series | `LinearAnalysisTimeSeriesResults` |
| `linear_opf(grid, options)` | DC/Linear OPF (LP/MIP) | `OptimalPowerFlowResults` |
| `nonlinear_opf(grid, opf_options)` | AC OPF (interior point) | `NonlinearOPFResults` |
| `simple_opf(grid, options)` | Greedy dispatch OPF | `OptimalPowerFlowResults` |
| `balanced_pf(grid, options, opf_options)` | OPF then PF validation | `OptimalPowerFlowResults` |
| `short_circuit(grid, fault_index, fault_type)` | Short circuit analysis | `ShortCircuitResults` |
| `continuation_power_flow(grid, ...)` | Voltage stability (CPF) | `ContinuationPowerFlowResults` |
| `contingencies_ts(circuit, ...)` | Time-series contingency analysis | `ContingencyAnalysisTimeSeriesResults` |
| `clustering(circuit, n_points)` | Time-series clustering | `ClusteringResults` |
| `save_cgmes_file(grid, filename, ...)` | Export to CGMES format | `Logger` |

Source: `VeraGridEngine/api.py` in installed package at `.venv/lib/python3.12/site-packages/VeraGridEngine/api.py`

### Driver Pattern

All simulations follow a consistent driver pattern (source: [VeraGrid README](https://github.com/SanPen/VeraGrid/blob/master/README.md)):

```python
driver = SomeDriver(grid=multi_circuit, options=some_options)
driver.run()
results = driver.results
```

The convenience functions in `api.py` wrap this pattern. For more control, use the drivers directly:
- `PowerFlowDriver` / `PowerFlowTimeSeriesDriver`
- `OptimalPowerFlowDriver` / `OptimalPowerFlowTimeSeriesDriver`
- `LinearAnalysisDriver` / `LinearAnalysisTimeSeriesDriver`
- `ContingencyAnalysisDriver` / `ContingencyAnalysisTimeSeriesDriver`
- `ShortCircuitDriver`
- `ContinuationPowerFlowDriver`
- `PowerFlowDriver3Ph`

Source: `VeraGridEngine/Simulations/` directory structure.

### Supported Problem Formulations

#### Power Flow Algorithms (`SolverType` enum)

| Enum Value | Algorithm |
|---|---|
| `SolverType.NR` | Newton-Raphson (default) |
| `SolverType.GAUSS` | Gauss-Seidel |
| `SolverType.Decoupled_LU` | Decoupled LU decomposition |
| `SolverType.GN` | Gauss-Newton |
| `SolverType.Linear` | DC power flow (linear approximation) |
| `SolverType.HELM` | Holomorphic Embedding Load Flow |
| `SolverType.PowellDogLeg` | Powell's Dog Leg |
| `SolverType.IWAMOTO` | Iwamoto-Newton-Raphson |
| `SolverType.CONTINUATION_NR` | Continuation Newton-Raphson |
| `SolverType.LM` | Levenberg-Marquardt |
| `SolverType.FASTDECOUPLED` | Fast Decoupled |
| `SolverType.LACPF` | Linear AC power flow |
| `SolverType.BFS` | Backward-Forward Substitution |
| `SolverType.BFS_linear` | BFS (linear) |
| `SolverType.Constant_Impedance_linear` | Constant impedance linear |

Source: `VeraGridEngine/enumerations.py`, `SolverType` enum.

#### OPF Formulations

**Linear OPF** (`SolverType.LINEAR_OPF`):
- PTDF-based DC OPF formulation in `Formulations/linear_opf_ts.py`
- Dispatch modes via `OpfDispatchMode` enum:
  - `Normal` — standard economic dispatch with network constraints
  - `UnitCommitment` — includes binary on/off variables, min up/down time, startup/shutdown costs, ramp constraints
  - `InterAreaRedispatch` — inter-area power exchange optimization
  - `NodalCapacity` — nodal injection capacity analysis
  - `GenerationExpansionPlanning` — investment-aware dispatch
- Supports contingency constraints (LODF-based security-constrained OPF)
- Zonal grouping: `NoGrouping`, `Area`, `All` (copper plate)
- Battery storage with SoC tracking, charge/discharge efficiency
- Hydro (fluid node) formulation with turbines, pumps, P2X, spillage
- Shadow prices (LMPs) extracted from dual variables of Kirchhoff constraints

**Nonlinear OPF** (`SolverType.NONLINEAR_OPF`):
- Full AC OPF via custom interior-point solver
- `AcOpfMode` options: `ACOPFstd`, `ACOPFslacks`, `ACOPFMaxInjections`
- Problem class: `NonLinearOptimalPfProblem` with analytical Jacobians and Hessians
- Handles multi-island systems (splits into sub-problems per island)
- Returns: voltage, power flows, LMPs (`lam_p`), generator dispatch, tap positions, loading
- Can be initialized from a prior power flow solution (`ips_init_with_pf`)

**Greedy Dispatch** (`SolverType.GREEDY_DISPATCH_OPF`):
- Heuristic merit-order dispatch without network constraints
- Handles batteries with SoC tracking
- Fast but no network feasibility guarantee

**Proportional OPF** (`SolverType.Proportional_OPF`):
- Listed in enumerations but dispatch logic not found in `opf_driver.py` — may be unsupported in snapshot mode.

Source: `VeraGridEngine/Simulations/OPF/opf_driver.py`, `VeraGridEngine/Simulations/OPF/Formulations/linear_opf_ts.py`, `VeraGridEngine/Simulations/OPF/ac_opf_worker.py`

#### Other Analysis Types

From `SimulationTypes` enum and `Simulations/` directory:
- **State Estimation** — WLS-based, with observability analysis and pseudo-measurement augmentation
- **Contingency Analysis** — methods: PowerFlow, OPF, HELM, Linear (LODF), PTDF Scan
- **Continuation Power Flow** — voltage stability analysis (nose curves)
- **Short Circuit** — sequence-based (LG, LL, LLG, 3ph); requires prior power flow
- **Stochastic Power Flow** — Monte Carlo and Latin Hypercube sampling
- **Small Signal Stability** — eigenvalue analysis
- **Investment Evaluation** — methods: Independent, Hyperopt, MVRSM, NSGA3, Random, Mixed Variable GA
- **Sigma Analysis** — one-shot stability assessment
- **NTC/ATC** — net/available transfer capacity computation
- **Reliability** — Monte Carlo reliability assessment
- **Clustering** — time series reduction for faster analysis

Source: `VeraGridEngine/enumerations.py` (`SimulationTypes`), `VeraGridEngine/Simulations/` directory listing.

### Solver Interfaces

#### MIP Solvers (for Linear OPF)

Configured via `MIPSolvers` enum in `OptimalPowerFlowOptions`:

| Solver | Enum |
|---|---|
| HiGHS | `MIPSolvers.HIGHS` (default) |
| SCIP | `MIPSolvers.SCIP` |
| CPLEX | `MIPSolvers.CPLEX` |
| Gurobi | `MIPSolvers.GUROBI` |
| Xpress | `MIPSolvers.XPRESS` |
| CBC | `MIPSolvers.CBC` |
| PDLP | `MIPSolvers.PDLP` |

These are accessed through two MIP frameworks (`MIPFramework` enum):
- **PuLP** (default) — `VeraGridEngine/Utils/MIP/pulp_interface.py`
- **OR-Tools** (optional) — `VeraGridEngine/Utils/MIP/ortools_interface.py`

Both frameworks provide a unified `LpModel` / `LpVar` / `LpExp` abstraction.

Source: `VeraGridEngine/enumerations.py`, `VeraGridEngine/Utils/MIP/selected_interface.py`

#### Power Flow Engines

Configured via `EngineType` enum:
- `VeraGrid` (default) — native Python/NumPy/SciPy solvers
- `Bentayga` — external engine (commercial, by same author)
- `NewtonPA` — Newton Power Analytics (commercial)
- `PGM` — Power Grid Model (open source, C++ backend)
- `GSLV` — gslv engine

Source: `VeraGridEngine/enumerations.py`, `VeraGridEngine/Compilers/circuit_to_bentayga.py`, `circuit_to_newton_pa.py`, `circuit_to_gslv.py`

#### NLP Solver (for AC OPF)

The nonlinear OPF uses a **custom interior-point solver** implemented in:
- `VeraGridEngine/Utils/NumericalMethods/ips.py`
- `VeraGridEngine/Simulations/OPF/NumericalMethods/newton_raphson_ips_fx.py`

This is not a call to an external NLP solver (e.g., Ipopt). It is a purpose-built IPS with configurable tolerance, max iterations, and trust radius. The problem formulation (`NonLinearOptimalPfProblem`) computes analytical derivatives in `ac_opf_derivatives.py`.

Source: `VeraGridEngine/Simulations/OPF/ac_opf_worker.py`, `VeraGridEngine/Simulations/OPF/Formulations/ac_opf_problem.py`

### Data Model

#### Central Object: `MultiCircuit`

`MultiCircuit` (inherits from `Assets`) is the primary data container. Key attributes (from `Assets.__slots__`):

**Buses & Topology:**
- `_buses` — list of `Bus` objects
- `_bus_bars` — `BusBar` (physical busbar representation)
- `_voltage_levels` — `VoltageLevel`
- `_substations` — `Substation`
- `_switch_devices` — `Switch`

**Branches:**
- `_lines` — `Line` (R, X, B per unit; positive/negative/zero sequence; temperature correction)
- `_transformers2w` — `Transformer2W` (tap module/phase control, winding connection types)
- `_transformers3w` — `Transformer3W`
- `_dc_lines` — `DCLine`
- `_hvdc_lines` — `HvdcLine`
- `_vsc_devices` — `VSC` (voltage source converter)
- `_upfc_devices` — `UPFC`
- `_series_reactances` — `SeriesReactance`

**Injections:**
- `_generators` — `Generator` (P, Pmin, Pmax, Qmin, Qmax, cost, Cost2, Cost0, startup/shutdown costs, ramp up/down, min up/down time, must-run flag)
- `_loads` — `Load`
- `_batteries` — `Battery`
- `_shunts` — `Shunt`
- `_static_generators` — `StaticGenerator` (non-dispatchable)
- `_external_grids` — `ExternalGrid` (PQ/PV/VD modes)
- `_current_injections` — `CurrentInjection`
- `_controllable_shunts` — `ControllableShunt`

**Aggregation:**
- `_areas`, `_zones`, `_countries`, `_communities`, `_regions`, `_municipalities`
- `_contingencies`, `_contingency_groups`
- `_investments`, `_investments_groups`

**System-wide:**
- `Sbase` — base power in MVA (default 100)
- `fBase` — base frequency in Hz (default 50)
- `_time_profile` — datetime array for time series

Source: `VeraGridEngine/Devices/assets.py`, `VeraGridEngine/Devices/multi_circuit.py`

#### Bus Model

`Bus` (in `Devices/Substation/bus.py`):
- `Vnom` — nominal voltage (kV)
- `Vmin`, `Vmax` — voltage limits (p.u.)
- `Vm0`, `Va0` — initial voltage guess
- `is_slack` — slack bus flag
- `is_dc` — DC bus flag
- `area`, `zone`, `country`, `substation`, `voltage_level` — hierarchy references
- Phase flags: `ph_a`, `ph_b`, `ph_c`, `ph_n`
- Fault parameters: `r_fault`, `x_fault`

#### Generator Model

`Generator` (in `Devices/Injections/generator.py`):
- `P` — active power (MW)
- `Pmin`, `Pmax` — active power limits (MW)
- `Qmin`, `Qmax` — reactive power limits (MVAr)
- `Snom` — nominal apparent power (MVA)
- `Vset` — voltage setpoint (p.u.)
- `Cost`, `Cost2`, `Cost0` — generation cost coefficients (linear, quadratic, constant)
- `StartupCost`, `ShutdownCost` — UC parameters
- `MinTimeUp`, `MinTimeDown` — minimum up/down time
- `RampUp`, `RampDown` — ramp rate limits
- `must_run` — must-run constraint flag
- `enabled_dispatch` — dispatchable flag
- `is_controlled` — voltage control flag
- Sequence impedances: `R1`, `X1`, `R0`, `X0`, `R2`, `X2`
- Dynamic parameters: `M` (inertia), `D` (damping), `Kp`, `Ki`, `Kw`

#### Branch Models

`Line` (in `Devices/Branches/line.py`):
- `R`, `X`, `B` — positive-sequence impedance (p.u.)
- `R0`, `X0`, `B0` — zero-sequence
- `R2`, `X2`, `B2` — negative-sequence
- `length` — line length
- `rate` — thermal rating (MVA)
- `temp_base`, `temp_oper`, `alpha` — temperature correction parameters
- `template` — can reference `OverheadLineType`, `UndergroundLineType`, or `SequenceLineType`

`Transformer2W` (in `Devices/Branches/transformer.py`):
- `HV`, `LV` — high/low voltage side (kV)
- `nominal_power` — rated power (MVA)
- `tap_module`, `tap_module_min`, `tap_module_max` — tap ratio control
- `tap_phase`, `tap_phase_min`, `tap_phase_max` — phase shifter control
- `tap_module_control_mode` — `TapModuleControl` (fixed, Vm, Qf, Qt)
- `tap_phase_control_mode` — `TapPhaseControl` (fixed, Pf, Pt)
- Winding connection: `WindingsConnection` (GG, GD, DG, DD, etc.)
- Zero/negative sequence parameters
- Tap changer settings: total positions, neutral position, dV

#### Compiled Data Model: `NumericalCircuit`

For simulation, the object model is compiled into a `NumericalCircuit` via `compile_numerical_circuit_at()`. This produces flat numpy arrays organized into typed data structures:
- `BusData`, `GeneratorData`, `BatteryData`, `LoadData`, `ShuntData`
- `PassiveBranchData`, `ActiveBranchData`, `HvdcData`, `VscData`
- `FluidNodeData`, `FluidTurbineData`, `FluidPumpData`, `FluidP2XData`, `FluidPathData`

The `NumericalCircuit` handles island detection and splits into sub-circuits for parallel solve. Uses numba JIT (`@nb.njit`) for performance-critical operations.

Source: `VeraGridEngine/DataStructures/numerical_circuit.py`, `VeraGridEngine/Compilers/circuit_to_data.py`

### Input/Output Formats

#### Import Formats

| Format | Extension(s) | Parser |
|---|---|---|
| MATPOWER | `.m`, `.matpower` | `IO/matpower/` |
| PSS/e RAW | `.raw` | `IO/raw/raw_parser_writer.py` |
| PSS/e RAWX | `.rawx` | `IO/raw/rawx_parser_writer.py` |
| CGMES | `.xml`, `.zip` | `IO/cim/cgmes/` (v2.4.15, v3.0.0) |
| CIM 16 | `.xml` | `IO/cim/cim16/` |
| DGS (PowerFactory) | `.dgs` | `IO/dgs/` |
| EPC (PowerWorld) | `.epc` | `IO/epc/` |
| PyPSA | `.nc` (NetCDF), `.hdf5` | `IO/others/pypsa_parser.py` |
| pandapower | `.json` | `IO/others/pandapower_parser.py` |
| UCTE-DEF | `.ucte` | `IO/ucte/` |
| IIDM (PowSyBl) | — | `IO/iidm/` |
| DPX | `.dpx` | `IO/others/dpx_parser.py` |
| IPA | — | `IO/others/ipa_parser.py` |
| RTE XML | — | `IO/others/rte_parser.py` |
| ANAREDE (PWF) | `.pwf` | `IO/others/anarede.py` |
| VeraGrid native | `.veragrid`, `.gridcal` | `IO/veragrid/` |
| VeraGrid Excel | `.xlsx`, `.xls` | `IO/veragrid/excel_interface.py` |
| VeraGrid JSON | `.json`, `.ejson` | `IO/veragrid/json_parser.py` |
| VeraGrid SQLite | `.sqlite` | `IO/veragrid/sqlite_interface.py` |
| VeraGrid H5 | `.h5` | `IO/veragrid/h5_interface.py` |

#### Export Formats

| Format | Method |
|---|---|
| VeraGrid native | `save_file(grid, "file.veragrid")` |
| VeraGrid Excel | `save_file(grid, "file.xlsx")` |
| VeraGrid JSON | `save_file(grid, "file.ejson")` |
| CGMES | `save_cgmes_file(grid, "file.zip", boundary_set_path)` |

Note: PSS/e `.raw` export is referenced in code (`raw_parser_writer.py`) but the [VeraGrid README](https://github.com/SanPen/VeraGrid/blob/master/README.md) notes `.raw` export has not been fully implemented.

Source: `VeraGridEngine/IO/file_open.py`, `VeraGridEngine/IO/file_save.py`, `VeraGridEngine/enumerations.py` (`FileType`)

### Result Access Patterns

#### Power Flow Results (`PowerFlowResults`)

```python
results = vge.power_flow(grid, options)
results.voltage        # CxVec — complex bus voltages
results.Sf             # CxVec — branch power flow (from end)
results.St             # CxVec — branch power flow (to end)
results.loading        # CxVec — branch loading (fraction of rate)
results.losses         # CxVec — branch losses
results.converged      # bool
results.iterations     # int
results.elapsed        # float (seconds)
```

Also includes VSC and HVDC-specific results: `Sf_hvdc`, `St_hvdc`, `losses_hvdc`, `loading_hvdc`, etc.

Source: `VeraGridEngine/Simulations/PowerFlow/power_flow_results.py`

#### OPF Results (`OptimalPowerFlowResults`)

```python
results = vge.linear_opf(grid, options)
results.voltage              # CxVec — bus voltages
results.bus_shadow_prices    # Vec — nodal LMPs
results.generator_power      # Vec — generator active power dispatch
results.generator_shedding   # Vec — curtailment
results.battery_power        # Vec — battery dispatch
results.load_shedding        # Vec — load shed
results.Sf                   # Vec — branch flows (from)
results.loading              # Vec — branch loading
results.overloads            # Vec — branch overloads
results.tap_angle            # Vec — phase shifter angles
results.hvdc_Pf              # Vec — HVDC power flows
results.converged            # bool
```

Available result categories: `BusResults`, `GeneratorResults`, `BatteryResults`, `LoadResults`, `BranchResults`, `HvdcResults`, `VscResults`, `AreaResults` (inter-area exchange, losses per area).

Source: `VeraGridEngine/Simulations/OPF/opf_results.py`

#### Nonlinear OPF Results (`NonlinearOPFResults`)

```python
results = vge.nonlinear_opf(grid, options)
results.V          # CxVec — complex voltages
results.S          # CxVec — power injections
results.Sf         # CxVec — branch flows
results.Pg         # Vec — generator active power
results.Qg         # Vec — generator reactive power
results.lam_p      # Vec — active power shadow prices (LMPs)
results.tap_phase  # Vec — phase shifter tap angles
results.tap_module # Vec — tap module ratios
results.converged  # bool
results.error      # float
results.iterations # int
```

Source: `VeraGridEngine/Simulations/OPF/Formulations/ac_opf_problem.py`

### Naming: GridCal vs VeraGrid

GridCal was renamed to VeraGrid. The old `GridCal` / `GridCalEngine` PyPI packages map to `VeraGrid` / `VeraGridEngine`. All internal references use the VeraGrid naming. The [old documentation](https://gridcal-wip.readthedocs.io/en/latest/) still uses GridCal naming but the API patterns are the same. The [current GitHub repo](https://github.com/SanPen/VeraGrid) uses VeraGrid naming.

Source: [GitHub SanPen/VeraGrid](https://github.com/SanPen/VeraGrid), [PyPI GridCalEngine](https://pypi.org/project/GridCalEngine/), [PyPI VeraGridEngine](https://pypi.org/project/veragridengine/)

### Programmatic Grid Construction (Verified)

Grids can be built entirely from code without loading files. The constructor parameter names differ from the old GridCal docs (e.g., `vset` not `Vset` for generators, `voltage_module` was old API). Verified working pattern (v5.6.28):

```python
import VeraGridEngine as vge

grid = vge.MultiCircuit()

b1 = vge.Bus(name="Bus1", Vnom=20)
b2 = vge.Bus(name="Bus2", Vnom=20)
grid.add_bus(b1)
grid.add_bus(b2)
b1.is_slack = True

gen = vge.Generator(name="Gen1", P=100, vset=1.0, Pmin=0, Pmax=200,
                    Cost=1.0, Cost2=0.01, Cost0=0.2)
grid.add_generator(b1, gen)

load = vge.Load(name="Load1", P=40, Q=20)
grid.add_load(b2, load)

line = vge.Line(bus_from=b1, bus_to=b2, name="L1-2", r=0.05, x=0.11, b=0.02, rate=100)
grid.add_line(line)

battery = vge.Battery(name="Batt1", P=0, Pmin=-50, Pmax=50, Enom=200,
                      charge_efficiency=0.9, discharge_efficiency=0.9,
                      min_soc=0.3, max_soc=0.99, soc=0.8)
grid.add_battery(b2, battery)
```

Source: Verified by execution in devcontainer against VeraGridEngine v5.6.28.

### Time Series / Profile API (Verified)

Time-varying data is attached to devices via `Profile` objects. Each device attribute `X` has a corresponding `X_prof` attribute:

```python
import pandas as pd
import numpy as np

# Set time axis on grid
dates = pd.date_range("2024-01-01", periods=24, freq="h")
grid.set_time_profile(dates)

# Set load profile (creates array matching time axis length)
load.P_prof.set(np.full(24, load.P) * np.random.uniform(0.8, 1.2, 24))
load.Q_prof.set(np.full(24, load.Q) * np.random.uniform(0.8, 1.2, 24))

# Run time-series power flow
ts_results = vge.power_flow_ts(grid, options=opts)
ts_results.voltage   # shape: (24, n_buses)
ts_results.Sf        # shape: (24, n_branches)
ts_results.loading   # shape: (24, n_branches)
```

Source: Verified by execution in devcontainer against VeraGridEngine v5.6.28.

### Result DataFrame Export (Verified)

Results objects provide `get_bus_df()`, `get_branch_df()`, `get_voltage_df()`, `get_current_df()` methods returning pandas DataFrames. Also `get_report_dataframe()`, `export_all()`, `to_json()`, and `get_dict()`. Example verified output:

```
Bus DataFrame columns: Vm, Va, P, Q
Branch DataFrame columns: Pf, Qf, Pt, Qt, loading, Ploss, Qloss
```

Source: Verified by execution in devcontainer against VeraGridEngine v5.6.28.

### Full Driver List (Verified)

All 25 driver classes verified in v5.6.28:

| Driver | Time-series variant | Purpose |
|---|---|---|
| `PowerFlowDriver` | `PowerFlowTimeSeriesDriver` | AC/DC power flow |
| `PowerFlowDriver3Ph` | — | 3-phase unbalanced power flow |
| `OptimalPowerFlowDriver` | `OptimalPowerFlowTimeSeriesDriver` | DC/AC OPF |
| `LinearAnalysisDriver` | `LinearAnalysisTimeSeriesDriver` | PTDF/LODF computation |
| `ContingencyAnalysisDriver` | `ContingencyAnalysisTimeSeriesDriver` | N-1 contingency analysis |
| `ContinuationPowerFlowDriver` | — | Voltage stability (CPF) |
| `ShortCircuitDriver` | — | Short circuit analysis |
| `StateEstimationDriver` | — | WLS state estimation |
| `StochasticPowerFlowDriver` | — | Monte Carlo / LHS power flow |
| `SmallSignalStabilityDriver` | — | Eigenvalue analysis |
| `SigmaAnalysisDriver` | — | One-shot stability |
| `ReliabilityStudyDriver` | — | Monte Carlo reliability |
| `AvailableTransferCapacityDriver` | `AvailableTransferCapacityTimeSeriesDriver` | ATC computation |
| `OptimalNetTransferCapacityDriver` | `OptimalNetTransferCapacityTimeSeriesDriver` | NTC optimization |
| `NodalCapacityTimeSeriesDriver` | — | Nodal capacity analysis |
| `InvestmentsEvaluationDriver` | — | Investment optimization |
| `ClusteringDriver` | — | Time series reduction |
| `InputsAnalysisDriver` | — | Input data validation |
| `NodeGroupsDriver` | — | Bus grouping analysis |
| `RmsSimulationDriver` | — | RMS transient simulation |

Source: `dir(VeraGridEngine)` filtered for `*Driver` classes, verified v5.6.28.

### Nonlinear OPF Convergence (Verified)

The custom IPS solver was tested on IEEE 39-bus. Converged in 16 iterations with error 5.57e-08. Produces LMPs (`lam_p`) ranging 0.13-0.14 $/MWh on the test case. This confirms the AC OPF is functional, though large-case robustness still needs testing.

Source: Verified by execution in devcontainer against VeraGridEngine v5.6.28.

### `run_linear_opf_ts` Detailed Signature (Verified)

The time-series linear OPF function `run_linear_opf_ts()` exposes the full set of UC/SCUC features:

```python
run_linear_opf_ts(
    grid: MultiCircuit,
    time_indices: IntVec | None,
    dispatch_mode: OpfDispatchMode = Normal,      # Normal, UnitCommitment, InterAreaRedispatch, etc.
    solver_type: MIPSolvers = HIGHS,              # HiGHS, SCIP, CPLEX, Gurobi, etc.
    zonal_grouping: ZonalGrouping = NoGrouping,    # NoGrouping, Area, All (copper plate)
    skip_generation_limits: bool = False,
    consider_contingencies: bool = False,          # LODF-based security constraints
    contingency_groups_used: list[ContingencyGroup] | None = None,
    ramp_constraints: bool = False,                # inter-temporal ramp limits
    consider_time_up_down: bool = False,           # min up/down time constraints
    area_spinning_reserve: bool = False,           # spinning reserve per area
    lodf_threshold: float = 0.001,
    energy_0: Vec | None = None,                   # initial battery SoC
    fluid_level_0: Vec | None = None,              # initial hydro reservoir level
    add_losses_approximation: bool = False,        # linear loss approximation
    mip_framework: MIPFramework = PuLP,            # PuLP or OR-Tools
    ...
) -> Tuple[OpfVars, LpModel]
```

This confirms that SCUC functionality (binary commitment variables, ramp constraints, min up/down, startup/shutdown costs, spinning reserves) is available within the linear OPF framework, not as a separate named SCUC abstraction.

Source: `VeraGridEngine/api.py` function `run_linear_opf_ts`, verified v5.6.28.

## Sources

1. Installed package source: `.venv/lib/python3.12/site-packages/VeraGridEngine/` (v5.6.28)
2. [VeraGrid README](https://github.com/SanPen/VeraGrid/blob/master/README.md) — GitHub
3. [GridCal documentation](https://gridcal-wip.readthedocs.io/en/latest/) — ReadTheDocs (old naming, v3.5.3)
4. [GridCal code tutorials](https://gridcal-wip.readthedocs.io/en/latest/getting_started/code_tutorials.html) — old API examples
5. [GridCal simulation theory](https://gridcal-wip.readthedocs.io/en/latest/theory/simulations.html) — power flow and OPF theory
6. [SanPen/GridCal GitHub](https://github.com/sanpen/gridcal) — original repo (now archived)
7. [SanPen/VeraGrid GitHub](https://github.com/SanPen/VeraGrid) — current repo
8. [GridCal Wiki](https://github.com/SanPen/GridCal/wiki) — algorithm descriptions (HELM, etc.)
9. `evaluations/gridcal/verify_install.py` — working usage example in this repo
10. `VeraGridEngine/enumerations.py` — all enum definitions (SolverType, MIPSolvers, EngineType, etc.)
11. `VeraGridEngine/Simulations/OPF/Formulations/linear_opf_ts.py` — DC OPF formulation source
12. `VeraGridEngine/Simulations/OPF/Formulations/ac_opf_problem.py` — AC OPF formulation source
13. Runtime introspection of v5.6.28 in devcontainer — constructor signatures, enum values, result attributes, DataFrame export methods
14. Execution verification: ACPF (NR, 39-bus), DCPF (Linear, 39-bus), Linear OPF (39-bus), Nonlinear OPF (39-bus, IPS), programmatic grid construction, save/load round-trip, time-series profiles and TS power flow

## Gaps and Uncertainties

- **No Ipopt/external NLP integration observed.** The AC OPF uses a custom interior-point solver. Converges on IEEE 39-bus (verified), but large-case robustness and numerical accuracy vs. MATPOWER reference values still need testing.
- **SCUC/SCED terminology:** Unit commitment exists as a dispatch mode within `linear_opf`, but it is unclear how mature the binary variable (on/off) formulation is for large systems. Needs testing with explicit UC parameters (startup costs, min up/down times).
- **Proportional OPF** is listed in `SolverType` but not dispatched in `opf_driver.py` snapshot mode -- may be time-series-only or deprecated.
- **PSS/e export completeness** is uncertain. The [VeraGrid README](https://github.com/SanPen/VeraGrid/blob/master/README.md) lists `.raw` and `.rawx` as export formats; code exists in `raw_parser_writer.py` but quality/completeness is unknown.
- **Engine backends** (Bentayga, NewtonPA, PGM, GSLV) are compiled-to but not installed. The default `VeraGrid` engine covers all documented formulations; external engines are performance/commercial options.
- **Documentation is sparse and partially outdated.** The ReadTheDocs site references the old `GridCal.Engine` API (v3.5.3), while the installed version is 5.6.28. Source code and runtime introspection are the authoritative references.
- **3-phase power flow** exists (`PowerFlowDriver3Ph`, `power_flow3ph()`) but scope and limitations are not documented. Returns `PowerFlowResults3Ph` with per-phase voltages.
- **Constructor parameter names changed** between old GridCal docs and current VeraGrid API (e.g., `voltage_module` -> `vset`, `Sbranch` -> `Sf`). Old tutorial code from ReadTheDocs will not work without adaptation.
- **RMS transient simulation** (`RmsSimulationDriver`) exists but dynamic model support scope is unclear -- `RmsModelTemplate`, `RmsEvent`, `RmsEventsGroup` classes exist but documentation is absent.

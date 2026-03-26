# GridCal — Research Context (Merged)

# Section 1: API & Formulations

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
---

# Section 2: Extensions & Architecture

# gridcal -- Research: Extensions & Architecture

## Key Findings

- **No formal plugin/extension API exists.** GridCal (now "VeraGrid" / `VeraGridEngine` v5.6.28) has no documented plugin system, hook registry, or callback framework for third-party extensions. The single exception is a `plugin_fcn_ptr` callback in the investment evaluation solver, which accepts a plain callable.
- **Architecture follows a clear three-layer separation:** Object-oriented device model (`MultiCircuit` / `Assets`) -> array-oriented numerical compilation (`NumericalCircuit`) -> simulation drivers (`DriverTemplate` subclasses) -> results (`ResultsTemplate`). This is well-structured but tightly coupled.
- **NetworkX is a direct dependency** and `MultiCircuit.build_graph()` returns a `nx.MultiDiGraph`. NetworkX is also used internally for topology reduction, node grouping, and synthetic network generation.
- **Pandas DataFrame export is built-in:** `PowerFlowResults.get_bus_df()` and `get_branch_df()` return DataFrames; `ResultsTable.to_df()` converts any result type to a DataFrame. The `export_all()` method returns bus and branch DataFrames.
- **Scipy sparse matrices are the primary internal representation** for admittance matrices, connectivity, and adjacency. The `NumericalCircuit` exposes `get_connectivity_matrices()`, `get_admittance_matrices()`, and `compute_adjacency_matrix()`.
- **Multi-engine compilation** via `Compilers/` translates `MultiCircuit` to external formats (Bentayga, Newton Power Analytics, Power Grid Model, GSLV, Gurobi Optimods). The `EngineType` enum selects the backend at runtime.
- **No constraint injection API.** OPF formulations are monolithic functions (e.g., `add_linear_branches_formulation`, `add_linear_node_balance`) that build the LP problem procedurally. Users cannot add custom constraints without modifying the source.
- **IO parsers support import/export from pandapower, PyPSA, MATPOWER, PSS/e, CGMES, DGS, UCTE, and IIDM formats.** Conversion is format-level, not live interop.
- **Signal system is a stub.** `DummySignal` replaces Qt signals in the engine, providing `emit()`/`connect()` methods. When used headless, signals are no-ops. The GUI package presumably replaces these with real Qt signals.
- **The `~/.VeraGrid/plugins/` directory exists** in the filesystem API, suggesting planned plugin support in the GUI layer, but no plugin loading mechanism was found in the engine code.

## Detailed Notes

### Architecture: Three-Layer Design

The codebase has a clear separation between three representations of a power system:

1. **Object-Oriented Layer (`Devices/`):** `MultiCircuit` extends `Assets`, which holds typed lists of device objects (buses, lines, generators, loads, etc.). Each device inherits from `EditableDevice`, which provides a property introspection system via `GCProp` descriptors. Devices are organized under `Devices/Branches/`, `Devices/Injections/`, `Devices/Substation/`, `Devices/Aggregation/`, `Devices/Fluid/`, `Devices/Dynamic/`.
   - Source: `VeraGridEngine/Devices/assets.py`, `VeraGridEngine/Devices/multi_circuit.py`

2. **Numerical Layer (`DataStructures/`):** `NumericalCircuit` stores array-oriented data (NumPy arrays, SciPy sparse matrices) compiled from the object model. Contains `BusData`, `PassiveBranchData`, `GeneratorData`, `LoadData`, etc. Compilation is performed by `compile_numerical_circuit_at()` in `Compilers/circuit_to_data.py`.
   - Source: `VeraGridEngine/DataStructures/numerical_circuit.py`, `VeraGridEngine/Compilers/circuit_to_data.py`

3. **Simulation Layer (`Simulations/`):** `DriverTemplate` is the base class for all simulation drivers. Each driver takes a `MultiCircuit`, compiles it, runs the algorithm, and populates a `ResultsTemplate` subclass. Drivers include: PowerFlow, OPF, LinearAnalysis, ContingencyAnalysis, ShortCircuit, ContinuationPowerFlow, StateEstimation, Stochastic, Clustering, InvestmentsEvaluation, NodalCapacity, NTC/ATC, Reliability, Rms (dynamics), and more.
   - Source: `VeraGridEngine/Simulations/driver_template.py`, `VeraGridEngine/Simulations/driver_handler.py`

The `api.py` module exposes high-level convenience functions (`power_flow()`, `linear_opf()`, `open_file()`, etc.) that wrap driver creation and execution.
   - Source: `VeraGridEngine/api.py`

### Plugin / Extension Mechanisms

**Investment Evaluation Plugin Callback:**
The `InvestmentsEvaluationOptions` class accepts a `plugin_fcn_ptr: Callable` parameter. When `solver=InvestmentEvaluationMethod.FromPlugin`, the driver calls `self.options.plugin_fcn_ptr(self)`, passing the entire driver as context. This is the only formal extension point found in the engine.
   - Source: `VeraGridEngine/Simulations/InvestmentsEvaluation/investments_evaluation_options.py` (line 24), `investments_evaluation_driver.py` (lines 318-319)
   - Enum: `InvestmentEvaluationMethod.FromPlugin` in `enumerations.py` (line 166)

**Plugins Directory:**
`file_system.py` defines `plugins_path()` returning `~/.VeraGrid/plugins/`. No loader code was found in the engine; this is likely used by the GUI layer.
   - Source: `VeraGridEngine/IO/file_system.py` (line 36)

**No General Hook/Event System:**
There is no observer pattern, event bus, or hook registry. The `DummySignal` class provides `emit()`/`connect()` stubs that are no-ops in headless mode. These are designed for Qt signal replacement, not for user-extensible callbacks.
   - Source: `VeraGridEngine/Simulations/driver_template.py` (lines 20-35)

### Network Graph Access

**NetworkX Integration:**
`MultiCircuit.build_graph()` returns a `nx.MultiDiGraph` with bus indices as nodes and weighted edges (weight = branch reactance X). A second method `build_graph_real_power_flow(current_flow)` builds a `nx.DiGraph` with edge direction based on actual power flow.
   - Source: `VeraGridEngine/Devices/multi_circuit.py` (lines 368-428)

NetworkX is also used in:
- `Simulations/Topology/node_groups_driver.py` -- Dijkstra shortest paths for node grouping
- `Simulations/Topology/topology_reduction_driver.py` -- Simple paths for topology reduction
- `Topology/GridReduction/` -- Di Shi and PTDF-based grid reduction
- `Utils/ThirdParty/SyntheticNetworks/rpgm_algo.py` -- Random power grid model generation
- `Devices/Diagrams/base_diagram.py` -- Diagram layout

**Adjacency and Connectivity Matrices:**
`MultiCircuit.get_adjacent_matrix()` returns a `scipy.sparse.csc_matrix`. `get_bus_branch_connectivity_matrix()` returns `(Cf, Ct, C)` sparse matrices. `NumericalCircuit.compute_adjacency_matrix()` provides the same from the numerical layer.
   - Source: `VeraGridEngine/Devices/multi_circuit.py` (lines 878-920), `DataStructures/numerical_circuit.py` (line 858)

**Island Detection:**
`Topology/topology.py` contains `find_islands()` using a Numba-JIT'd DFS on sparse CSC adjacency matrices. This is the core topology processing routine.
   - Source: `VeraGridEngine/Topology/topology.py`

### DataFrame Interoperability

**Results to DataFrame:**
- `PowerFlowResults.get_bus_df()` -> `pd.DataFrame` with columns `Vm, Va, P, Q`
- `PowerFlowResults.get_branch_df()` -> `pd.DataFrame` with columns `Pf, Qf, Pt, Qt, loading, Ploss, Qloss`
- `PowerFlowResults.export_all()` -> tuple of `(df_bus, df_branch)` DataFrames
- `ResultsTable.to_df()` converts any results model to a DataFrame
- `ResultsTable.save_to_excel(file_name)` and `save_to_csv(file_name)` for disk export
   - Source: `VeraGridEngine/Simulations/PowerFlow/power_flow_results.py` (lines 447-475, 951-991), `VeraGridEngine/Simulations/results_table.py` (to_df at ~line 356)

**Device Data:**
Device properties use a `GCProp` descriptor system for introspection. The `EditableDevice` base class supports `get_dict()` for serialization. However, there is no built-in `to_dataframe()` on the device model itself -- users must iterate device lists manually.

### Constraint Addition (OPF)

The linear OPF formulation is implemented as a series of procedural functions in `Simulations/OPF/Formulations/linear_opf_ts.py`:
- `add_linear_simple_generation_formulation()`
- `add_linear_battery_formulation()`
- `add_linear_branches_formulation()`
- `add_linear_branches_contingencies_formulation()`
- `add_linear_hvdc_formulation()`
- `add_linear_node_balance()`
- `add_linear_load_formulation()`
- `add_hydro_formulation()`
- etc.

These functions operate on an `LpModel` object and add variables/constraints procedurally. The AC OPF uses `NonLinearOptimalPfProblem` class with `update()` and `get_jacobians_and_hessians()` methods.

**There is no API to inject custom constraints.** Users would need to either:
1. Fork the formulation functions and add constraints directly
2. Extract the `NumericalCircuit` data and build their own optimization problem

   - Source: `VeraGridEngine/Simulations/OPF/Formulations/linear_opf_ts.py`, `ac_opf_problem.py`

### Multi-Engine Compilation (Compilers/)

The `Compilers/` module provides translation from `MultiCircuit` to external solver formats:
- `circuit_to_bentayga.py` -- Bentayga (commercial, license-gated)
- `circuit_to_newton_pa.py` -- Newton Power Analytics
- `circuit_to_pgm.py` -- Power Grid Model (open-source)
- `circuit_to_gslv.py` -- GSLV solver
- `circuit_to_optimods.py` -- Gurobi Optimods (for AC OPF via Gurobi)

The `EngineType` enum (`VeraGrid`, `Bentayga`, `NewtonPA`, `PGM`, `GSLV`) selects the backend at driver construction. The internal `circuit_to_data.py` compiles to the native `NumericalCircuit`.
   - Source: `VeraGridEngine/Compilers/__init__.py`, `VeraGridEngine/enumerations.py` (line 294)

### Format Interoperability (IO/)

Import parsers:
- MATPOWER `.m` files (`IO/matpower/`)
- PSS/e `.raw`/`.rawx` files (`IO/raw/`)
- CGMES/CIM XML (`IO/cim/`)
- DigiSilent DGS (`IO/dgs/`)
- PSLF `.epc` (`IO/epc/`)
- UCTE (`IO/ucte/`)
- IIDM (`IO/iidm/`)
- pandapower pickle/JSON/SQLite/Excel (`IO/others/pandapower_parser.py`)
- PyPSA Network (`IO/others/pypsa_parser.py`)
- ANAREDE, IPA, PLX, DPX, RTE formats (`IO/others/`)

Export:
- `to_matpower()` function for MATPOWER dict format
- CGMES export via `save_cgmes_file()`
- PSS/e `.raw` export (`IO/raw/veragrid_to_raw.py`)
- Native formats: `.veragrid` (zip/HDF5/SQLite), `.ejson`, Excel
   - Source: `VeraGridEngine/IO/` directory, `VeraGridEngine/IO/matpower/__init__.py`

### Code Organization Metrics

- `multi_circuit.py`: 3,199 lines (the central god-class, inherits from `Assets`)
- `assets.py`: 7,000+ lines (device list management)
- `linear_opf_ts.py`: 2,600+ lines (linear OPF formulation)
- `ac_opf_problem.py`: 1,700+ lines (nonlinear OPF)
- `circuit_to_data.py`: 2,200+ lines (numerical compilation)
- `topology.py`: 700+ lines (island detection, connectivity)

The `MultiCircuit`/`Assets` class is a large monolith with 100+ methods. While the subpackage organization is clean (Devices, DataStructures, Simulations, Compilers, IO, Topology, Utils), the central classes are not decomposed.

## Sources

1. `VeraGridEngine/__version__.py` -- Version 5.6.28, MPL-2.0 license
2. `VeraGridEngine/api.py` -- Public API convenience functions
3. `VeraGridEngine/__init__.py` -- Package initialization and contributor list
4. `VeraGridEngine/Devices/multi_circuit.py` -- Core MultiCircuit class with `build_graph()`, `get_adjacent_matrix()`
5. `VeraGridEngine/Devices/assets.py` -- Assets base class with device list management
6. `VeraGridEngine/Simulations/driver_template.py` -- DriverTemplate, DummySignal, TimeSeriesDriverTemplate
7. `VeraGridEngine/Simulations/results_template.py` -- ResultsTemplate with data serialization
8. `VeraGridEngine/Simulations/results_table.py` -- ResultsTable with `to_df()`, `save_to_excel()`, `save_to_csv()`
9. `VeraGridEngine/Simulations/PowerFlow/power_flow_results.py` -- `get_bus_df()`, `get_branch_df()`, `export_all()`
10. `VeraGridEngine/Simulations/InvestmentsEvaluation/investments_evaluation_options.py` -- `plugin_fcn_ptr` callback
11. `VeraGridEngine/Simulations/InvestmentsEvaluation/investments_evaluation_driver.py` -- `FromPlugin` dispatch
12. `VeraGridEngine/Simulations/OPF/Formulations/linear_opf_ts.py` -- Linear OPF constraint functions
13. `VeraGridEngine/Simulations/OPF/Formulations/ac_opf_problem.py` -- Nonlinear OPF problem class
14. `VeraGridEngine/DataStructures/numerical_circuit.py` -- NumericalCircuit with sparse matrices
15. `VeraGridEngine/Topology/topology.py` -- Island detection, adjacency, connectivity
16. `VeraGridEngine/Compilers/__init__.py` -- Compiler module exports
17. `VeraGridEngine/Compilers/circuit_to_pgm.py` -- Power Grid Model translation
18. `VeraGridEngine/Compilers/circuit_to_bentayga.py` -- Bentayga translation
19. `VeraGridEngine/Compilers/circuit_to_optimods.py` -- Gurobi Optimods translation
20. `VeraGridEngine/IO/file_system.py` -- `plugins_path()`, `scripts_path()`
21. `VeraGridEngine/IO/others/pypsa_parser.py` -- PyPSA import parser
22. `VeraGridEngine/IO/others/pandapower_parser.py` -- pandapower import parser
23. `VeraGridEngine/IO/matpower/__init__.py` -- MATPOWER import/export
24. `VeraGridEngine/Devices/Parents/editable_device.py` -- GCProp, EditableDevice
25. `VeraGridEngine/enumerations.py` -- EngineType, InvestmentEvaluationMethod, SimulationTypes
26. GitHub repository metadata: https://github.com/SanPen/VeraGrid (516 stars, 29 open issues, MPL-2.0)

## Gaps and Uncertainties

- **No developer documentation for extensions.** The GitHub wiki pages mostly fail to load; readthedocs returns 404. Extension patterns must be inferred entirely from source code.
- **Plugin loading mechanism unclear.** The `plugins_path()` exists but no loader was found in the engine. This likely lives in the GUI package (`VeraGrid` as opposed to `VeraGridEngine`), which is not installed here.
- **Custom constraint injection untested.** While the LP/NLP problem objects are accessible in theory, there is no documented or supported way to add custom constraints. Needs verification whether one can subclass `NonLinearOptimalPfProblem` or inject into the `LpModel`.
- **Graphs.jl interop does not exist.** GridCal is Python-only; no Julia interop is available.
- **The rename from GridCal to VeraGrid is recent** (the PyPI package is `veragridengine`, GitHub repo is `SanPen/VeraGrid` but still referenced as GridCal in many places). Documentation may lag behind.
- **Signal/callback system untested with real Qt.** The `DummySignal.connect()` method exists but its behavior when connected to real callbacks in headless mode needs verification.
- **No event hooks for pre/post simulation.** There is no documented way to register callbacks that fire before or after a simulation run.
- **Device-level DataFrame export not built-in.** While results have `to_df()`, the device model (buses, generators, etc.) does not provide a direct DataFrame export method -- users must iterate and construct manually.
---

# Section 3: Limitations & Ecosystem

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
---

# Section 4: Version & Capabilities

```yaml
tool: gridcal
installed_version: 5.6.28
release_date: 2026-02-25
latest_version: 5.6.38
latest_release_date: 2026-03-18
research_date: 2026-03-24
```

# gridcal — Version & Capability Report

## Version Summary

The installed version of GridCal (rebranded as VeraGrid/VeraGridEngine since v5.4.0) is **5.6.28**, released on 2026-02-25. The latest available version on PyPI is **5.6.38**, released 2026-03-18 — 10 patch releases and 21 days behind. The 5.6.x series has seen extremely rapid iteration: between the installed version and the latest, there have been releases on 2026-03-03 (5.6.29), 03-06 (5.6.30), 03-09 (5.6.31), 03-11 (5.6.32, 5.6.33), 03-12 (5.6.34), 03-16 (5.6.35), 03-17 (5.6.36), and 03-18 (5.6.37, 5.6.38). None of these releases have tagged GitHub release notes; the GitHub commit history shows only generic "latest changes from eroots repo" merge messages, indicating development occurs in a private eRoots repository. Based on the patch-level versioning and absence of documented breaking changes, the risk of API incompatibility between 5.6.28 and 5.6.38 is low.

The project underwent a significant rebrand from "GridCal" to "VeraGrid" at version 5.4.0 (February 2025) due to trademark conflicts. The Python package was renamed from `GridCalEngine` to `VeraGridEngine`, and the import namespace changed from `GridCalEngine` to `VeraGridEngine`. The core API surface, class names, and function signatures were preserved through the rename. The evaluation uses the `veragridengine` PyPI package with `import VeraGridEngine as vge`.

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes | ~1.0 | `SolverType.Linear` provides DC approximation. Tested against all MATPOWER 8 benchmark grids. ([README](https://github.com/SanPen/VeraGrid/blob/master/README.md)) |
| AC Power Flow (ACPF) | yes | ~1.0 | Multiple solvers: Newton-Raphson, Gauss-Seidel, HELM, Fast Decoupled, Iwamoto-NR, Continuation NR, LACPF. Three-phase unbalanced power flow added in 5.x series. ([README](https://github.com/SanPen/VeraGrid/blob/master/README.md)) |
| DC Optimal Power Flow (DC OPF) | yes | ~3.0 | `SolverType.LINEAR_OPF`. MIP support via HiGHS (built-in since 4.5.0), plus SCIP/CPLEX/Gurobi/CBC through PuLP or OR-Tools frameworks. MIP auto-healing added in 5.0.2 ensures OPF simulations are always feasible. ([Changelog](https://veragrid.readthedocs.io/en/stable/rst_source/change_log.html), [OPF docs](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html)) |
| AC Optimal Power Flow (AC OPF) | yes | 5.1.0 | `SolverType.NONLINEAR_OPF` with Interior Point Solver. Three modes: standard, slacks, max injections. Enhanced in 5.1.0 with HVDC dispatch. Also offers "AC Linear OPF" mode between DC and full NL. ([GitHub release 5.1.0](https://github.com/SanPen/VeraGrid/releases/tag/5.1.0), [OPF docs](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html)) |
| Security-Constrained Unit Commitment (SCUC) | partial | ~5.0 | `OpfDispatchMode.UnitCommitment` exists with `consider_time_up_down` and `consider_ramps` options. Documentation shows multi-period 24-hour commitment examples using MIP via HiGHS. However, this is a simplified UC formulation within the OPF framework — not a full ISO-grade SCUC with all standard constraints (startup cost profiles, detailed min up/down time curves, reserve products). ([OPF docs](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html)) |
| Security-Constrained Economic Dispatch (SCED) | partial | ~5.0 | Linear OPF with `consider_contingencies` option approximates SCED functionality. No dedicated SCED solver or API. Dispatch is handled via `OpfDispatchMode.Normal` with security constraints. Quadratic cost curves with fixed/linear/quadratic coefficients supported. ([OPF docs](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html)) |
| PTDF / Shift Factor Extraction | yes | 3.6.1 (empirical), 4.0.0 (analytical) | `LinearAnalysis` driver computes PTDF and LODF matrices. Version 4.0.0 replaced empirical method with analytical PTDF/LODF (orders of magnitude faster). Time-series variant available via `LinearAnalysisTimeSeriesDriver`. Also supports VTDF (3.6.4+) and net transfer capacity calculation. ([Changelog 4.0.0](https://veragrid.readthedocs.io/en/stable/rst_source/change_log.html), [README](https://github.com/SanPen/VeraGrid/blob/master/README.md)) |
| Contingency Analysis (N-1) | yes | 3.6.1 | `ContingencyAnalysisDriver` with both power-flow and LODF-based methods. Supports contingency groups and filtering. Time-series contingency analysis also available. Contingency reports added to all OPF modes in 4.2.4. Branch contingency multiplier in 4.1.2. ([Changelog](https://veragrid.readthedocs.io/en/stable/rst_source/change_log.html), [README](https://github.com/SanPen/VeraGrid/blob/master/README.md)) |
| Custom Constraint Injection | no | — | No public API for injecting arbitrary user-defined constraints into the OPF formulation. The OPF is formulated internally using PuLP/OR-Tools but the model construction is not exposed for user modification. Flexible slack variables (load/generation shedding with cost weights) provide limited soft-constraint capability but not arbitrary linear constraints. ([OPF docs](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html)) |
| Network Graph Access | yes | ~3.0 | `MultiCircuit.build_graph()` and `MultiCircuit.plot_graph()` provide network topology as a graph. `get_topology_data()` returns topology information. Island detection via `find_islands`. Kron's reduction for network simplification. ([Modelling docs](https://veragrid.readthedocs.io/en/latest/md_source/modelling.html)) |
| CSV Data Import | no | — | No native CSV import for network data. Supports Excel import (`interpret_excel_v3`), JSON, native `.veragrid` format, and equipment catalog databases. Profile data can be loaded from Excel. ([Modelling docs](https://veragrid.readthedocs.io/en/latest/md_source/modelling.html)) |
| MATPOWER Case Import | yes | ~2.0 | `vge.open_file("case.m")` natively parses MATPOWER `.m` files. Tested against all MATPOWER 8 benchmark cases; README claims the continental USA case solves in ~1 second. Also supports PSS/e `.raw`/`.rawx` (v29-35), CGMES/CIM (2.4.15, 3.0), UCTE, DigSilent `.dgs` (partial), PSLF `.epc` (partial), and PyPSA formats. ([README](https://github.com/SanPen/VeraGrid/blob/master/README.md)) |
| Multi-Period / Time Series | yes | ~3.0 | `PowerFlowTimeSeriesDriver` and `OptimalPowerFlowTimeSeriesDriver` support temporal simulation. Time grouping (monthly, weekly, daily, hourly) for OPF time series. Battery state-of-charge tracking across periods. Clustering driver for representative period selection (4.1.0+). Results can be saved to files (4.2.0+). ([Changelog](https://veragrid.readthedocs.io/en/stable/rst_source/change_log.html), [OPF docs](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html)) |
| Warm Start / Solution Reuse | yes | ~4.0 | `PowerFlowOptions.use_stored_guess` and `initialize_with_existing_solution` flags enable warm starting from previous solutions. OPF options include `ips_init_with_pf` to initialize AC OPF from power flow solution. OPF verification workflow dispatches via linear optimization then validates with exact power flow. ([OPF docs](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html)) |
| Parallel Computation | partial | ~4.0 | Time series simulations support parallel execution via the `engine` parameter (VeraGrid, Bentayga, NewtonPA, PGM, GSLV engines). Parallel operation limited to UNIX systems due to Python multiprocessing constraints on Windows. Bentayga and NewtonPA are proprietary/commercial add-ons from eRoots. No GPU acceleration. ([README](https://github.com/SanPen/VeraGrid/blob/master/README.md)) |

### Support Semantics

- **yes** — Feature is fully supported in the installed version.
- **no** — Feature is not available.
- **partial** — Feature exists but with significant limitations. Notes column explains.

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|----------------------|
| 5.4.0 | Rebrand from GridCal to VeraGrid. Package renamed from `GridCalEngine` to `VeraGridEngine`. Import namespace changed accordingly. ([GitHub release v5.4.0](https://github.com/SanPen/VeraGrid/releases/tag/v5.4.0)) | Evaluation already uses `VeraGridEngine` — no impact. Any documentation or examples referencing `GridCalEngine` need import path updates. |
| 5.3.0 | Topology processing overhaul: consolidated ConnectivityNodes, BusBars, and Buses into unified framework. FUBM converter approach integrated. ([GitHub release v5.3.0](https://github.com/SanPen/VeraGrid/releases/tag/v5.3.0)) | May affect how bus/branch topology is accessed programmatically. Improved AC/DC convergence properties are beneficial for evaluation. |
| 5.2.0 | License changed from LGPL to MPLv2. ([GitHub release v5.2.0](https://github.com/SanPen/VeraGrid/releases/tag/v5.2.0)) | No API impact. License change relevant for supply chain evaluation dimension. |
| 5.1.0 | JSON-based file format replaced CSV for native `.gridcal` files. Sparse profile implementation changed memory layout. First production-grade ACOPF. ([GitHub release 5.1.0](https://github.com/SanPen/VeraGrid/releases/tag/5.1.0)) | No impact on MATPOWER import. ACOPF capability is a significant addition for expressiveness tests. |
| 5.0.2 | "The great split" — GridCal split into GUI package (GridCal/VeraGrid) and engine package (GridCalEngine/VeraGridEngine). API naming unified. MIP auto-healing for OPF feasibility. ([GitHub release 5.0.2](https://github.com/SanPen/VeraGrid/releases/tag/5.0.2)) | Evaluation correctly depends only on `veragridengine` (engine-only package without Qt). |
| 4.0.0 | Multi-terminal AC/DC grids. Replaced empirical PTDF with analytical PTDF/LODF (orders of magnitude faster). Outer loop controls replaced with direct integration into numerical methods. ([GitHub release v4.0](https://github.com/SanPen/VeraGrid/releases/tag/v4.0)) | Analytical PTDF is the current implementation used in evaluation. |

## Changelog Analysis

### Installed Version (5.6.28) to Latest (5.6.38)

No tagged GitHub releases exist between 5.6.20 and 5.6.38. The 10 releases from 5.6.29 to 5.6.38 span 2026-03-03 to 2026-03-18 (15 days). GitHub commit messages for this period are generic merges from the private eRoots development repository ("latest changes from eroots repo", version number bumps). Without detailed release notes, the specific changes cannot be enumerated. The rapid release cadence (10 releases in 15 days) and patch-level versioning suggest bug fixes and incremental improvements rather than feature additions.

### Key milestones in the 5.x series

**5.6.20 (2026-02-02, tagged release):** "Countless bug fixes," proper grid reduction, file format export reorganization, substation creation from electrical patterns (breaker-and-a-half, double bar). Short circuits no longer treated as variations.

**5.4.0 (2025-02-02):** Rebrand from GridCal to VeraGrid. Package rename. No functional changes.

**5.3.0 (2025-01-08):** Topology processing overhaul. FUBM integration for improved AC/DC convergence.

**5.2.0 (2024-11-11):** License change from LGPL to MPLv2.

**5.1.0 (2024-04-01):** First production-grade ACOPF with interior point solver. HVDC dispatch in OPF. Sparse profiles for memory-efficient time series.

**5.0.2 (2023-11-18):** Engine/GUI split enabling headless operation. MIP auto-healing for OPF feasibility.

### Features relevant to the 15 canonical capabilities

The 5.x series brought two major capability additions: (1) AC OPF via interior point solver (5.1.0), and (2) improved topology handling for AC/DC grids (5.3.0). All other canonical features (DCPF, ACPF, DC OPF, PTDF, contingency analysis, MATPOWER import, time series, warm start) were already present in the 4.x series and have been incrementally improved. SCUC/SCED remain partial implementations within the OPF framework. Custom constraint injection and CSV import remain unsupported as of 5.6.38.

## Sources

1. [VeraGridEngine on PyPI](https://pypi.org/project/VeraGridEngine/) — version history and release dates (confirmed 5.6.38 as latest, 2026-03-18)
2. [VeraGrid GitHub Repository](https://github.com/SanPen/VeraGrid) — source code, releases, commit history
3. [VeraGrid GitHub Releases](https://github.com/SanPen/VeraGrid/releases) — release notes for tagged versions (5.6.20 and earlier only)
4. [VeraGrid Documentation — Changelog](https://veragrid.readthedocs.io/en/stable/rst_source/change_log.html) — historical changelog (covers up to 5.0.2 only)
5. [VeraGrid Documentation — OPF](https://veragrid.readthedocs.io/en/latest/md_source/optimal_power_flow.html) — OPF capabilities, dispatch modes, solver support (v5.6.31 docs)
6. [VeraGrid Documentation — Modelling](https://veragrid.readthedocs.io/en/latest/md_source/modelling.html) — element types, file formats, topology (v5.6.31 docs)
7. [VeraGrid README](https://github.com/SanPen/VeraGrid/blob/master/README.md) — feature list, file format support, MATPOWER compatibility
8. Runtime introspection of `VeraGridEngine` 5.6.28 API via devcontainer (`importlib.metadata.version('veragridengine')`)

## Gaps and Uncertainties

- **Changelog gap for 5.6.21–5.6.38:** No tagged GitHub releases exist after 5.6.20. Versions 5.6.21 through 5.6.38 have no public release notes. Development occurs in a private eRoots repository with periodic merges to the public GitHub repo, making it impossible to track individual changes between 5.6.28 and 5.6.38.
- **SCUC/SCED depth unclear:** The `OpfDispatchMode.UnitCommitment` mode exists and the documentation shows 24-hour commitment examples, but its exact constraint set (startup cost profiles, min up/down time enforcement, reserve products, ramp rate modeling fidelity) could not be fully determined from the public API and documentation alone. Testing is needed to verify the scope of the UC formulation.
- **Custom constraint injection:** No public API was found. It may be possible to modify the PuLP/OR-Tools model objects if they are accessible through internal attributes, but this would be undocumented and fragile. The flexible slack variables (load/generation shedding with costs) provide limited soft-constraint capability but not arbitrary linear constraint injection.
- **Parallel computation scope:** The `engine` parameter suggests pluggable compute backends, but actual parallelization behavior (thread vs. process, degree of parallelism) is not documented. Bentayga and NewtonPA engines are proprietary/commercial add-ons from eRoots — their availability and capabilities are unclear for evaluation purposes.
- **"Since Version" estimates:** Many "since version" entries are approximate, based on changelog analysis and feature availability in historical documentation. Exact version provenance could not be determined for features that predate the 3.6.1 changelog entries.
- **Documentation version lag:** The latest ReadTheDocs documentation is for version 5.6.31, while the latest PyPI release is 5.6.38. The changelog on ReadTheDocs only covers up to 5.0.2. There may be undocumented capability additions in recent versions.
- **5.6.28 to 5.6.38 delta risk assessment:** The 10-release gap with no documented changes presents low but non-zero risk. All are patch-level bumps within 15 days, suggesting bug fixes. No evidence of breaking API changes, but this cannot be confirmed without source-level comparison.

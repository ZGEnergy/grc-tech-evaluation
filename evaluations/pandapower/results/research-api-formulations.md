# pandapower -- Research: API & Formulations

**Version evaluated:** 3.4.0 (installed via uv in devcontainer)
**Date:** 2026-03-06

## Key Findings

- pandapower represents networks as a `pandapowerNet` object (subclass of dict) containing ~30+ pandas DataFrames -- one per element type (bus, line, gen, load, trafo, etc.) plus corresponding `res_*` result tables.
- Supports AC power flow (`pp.runpp`) with 6 solver algorithms: Newton-Raphson, Iwamoto NR, backward/forward sweep, Gauss-Seidel, and two fast-decoupled variants. DC power flow via `pp.rundcpp`.
- AC OPF (`pp.runopp`) and DC OPF (`pp.rundcopp`) use PYPOWER's interior point method internally. OPF results include **LMPs** directly in `net.res_bus.lam_p` and `net.res_bus.lam_q`.
- Extensive PowerModels.jl interface (`pp.runpm*`) supports 13+ functions including AC/DC OPF, optimal transmission switching (OTS), transmission network expansion planning (TNEP), storage OPF, and various relaxations (SDP, SOC, QC formulations).
- **No native SCUC or SCED.** pandapower has no unit commitment formulation -- it is a steady-state power flow and OPF tool, not a production cost model.
- Contingency analysis via `pandapower.contingency.run_contingency()` supports N-1 analysis with optional lightsim2grid acceleration, but no built-in SCOPF optimizer.
- Distributed slack is supported via `slack_weight` parameters on `ext_grid` and `gen` elements, enabled with `distributed_slack=True` in `runpp`.
- Cost functions support both polynomial (`create_poly_cost` with up to quadratic terms) and piecewise-linear (`create_pwl_cost`) formulations for active and reactive power.
- I/O formats: JSON (native), Excel, pickle, SQLite, PostgreSQL, MATPOWER `.m`/`.mat` import/export, and dict-of-DataFrames.
- Three-phase unbalanced power flow (`pp.runpp_3ph`) and lightsim2grid/PowerGridModel solver backends provide performance alternatives.

## Detailed Notes

### Data Model: The pandapowerNet Object

The core data structure is `pandapowerNet`, a dict-like object where each key maps to a pandas DataFrame representing one element type. Created via `pp.create_empty_network()`.

**Input element DataFrames (primary):**

| DataFrame | Key columns | Purpose |
|-----------|-------------|---------|
| `net.bus` | `name`, `vn_kv`, `type`, `zone`, `in_service`, `geo` | Bus definitions |
| `net.line` | `from_bus`, `to_bus`, `length_km`, `r_ohm_per_km`, `x_ohm_per_km`, `c_nf_per_km`, `max_i_ka` | AC transmission/distribution lines |
| `net.trafo` | `hv_bus`, `lv_bus`, `sn_mva`, `vn_hv_kv`, `vn_lv_kv`, `vk_percent`, `vkr_percent`, tap params | 2-winding transformers |
| `net.trafo3w` | `hv_bus`, `mv_bus`, `lv_bus`, + per-winding parameters | 3-winding transformers |
| `net.gen` | `bus`, `p_mw`, `vm_pu`, `min_p_mw`, `max_p_mw`, `min_q_mvar`, `max_q_mvar`, `slack`, `slack_weight`, `controllable` | PV generators |
| `net.sgen` | `bus`, `p_mw`, `q_mvar`, `controllable` | Static generators (PQ injection) |
| `net.ext_grid` | `bus`, `vm_pu`, `va_degree`, `slack_weight`, `controllable` | External grid / slack bus |
| `net.load` | `bus`, `p_mw`, `q_mvar`, `const_z_p_percent`, `const_i_p_percent`, `scaling` | Loads (ZIP model supported) |
| `net.storage` | `bus`, `p_mw`, `q_mvar`, `soc_percent`, `min_e_mwh`, `max_e_mwh` | Energy storage |
| `net.shunt` | `bus`, `q_mvar`, `p_mw`, `vn_kv`, `step`, `max_step` | Shunt compensators |
| `net.switch` | `bus`, `element`, `et`, `closed`, `z_ohm` | Switching devices |
| `net.dcline` | `from_bus`, `to_bus`, `p_mw`, `loss_percent`, `loss_mw` | DC lines |
| `net.impedance` | `from_bus`, `to_bus`, `rft_pu`, `xft_pu` (asymmetric R/X) | General impedance elements |
| `net.ward` / `net.xward` | `bus`, `ps_mw`, `qs_mvar`, `pz_mw`, `qz_mvar` | Ward / extended Ward equivalents |
| `net.svc` | `bus`, `x_l_ohm`, `x_cvar_ohm`, `set_vm_pu` | Static VAR compensators |
| `net.tcsc` | `from_bus`, `to_bus`, `x_l_ohm`, `x_cvar_ohm` | Thyristor-controlled series compensators |
| `net.ssc` | `bus`, `r_ohm`, `x_ohm`, `set_vm_pu` | Static series compensators |
| `net.vsc` / `net.vsc_bipolar` / `net.vsc_stacked` | AC/DC bus connections, control modes | Voltage source converters (HVDC) |
| `net.bus_dc` / `net.line_dc` / `net.load_dc` / `net.source_dc` | DC network elements | DC grid modeling |
| `net.motor` | `bus`, `pn_mech_mw`, `cos_phi`, `lrc_pu` | Induction motors |
| `net.measurement` | `measurement_type`, `element_type`, `element`, `value`, `std_dev` | Measurements for state estimation |

**Cost DataFrames (for OPF):**

| DataFrame | Key columns |
|-----------|-------------|
| `net.poly_cost` | `element`, `et`, `cp0_eur`, `cp1_eur_per_mw`, `cp2_eur_per_mw2`, `cq0_eur`, `cq1_eur_per_mvar`, `cq2_eur_per_mvar2` |
| `net.pwl_cost` | `power_type`, `element`, `et`, `points` (list of [p, cost] breakpoints) |

Source: Verified from `pp.create_empty_network()` introspection, pandapower 3.4.0.

**Result DataFrames (populated after solving):**

| DataFrame | Key columns |
|-----------|-------------|
| `net.res_bus` | `vm_pu`, `va_degree`, `p_mw`, `q_mvar` (+ `lam_p`, `lam_q` after OPF) |
| `net.res_line` | `p_from_mw`, `q_from_mvar`, `p_to_mw`, `q_to_mvar`, `pl_mw` (losses), `ql_mvar`, `i_ka`, `loading_percent` |
| `net.res_trafo` | `p_hv_mw`, `p_lv_mw`, `pl_mw`, `ql_mvar`, `loading_percent` |
| `net.res_gen` | `p_mw`, `q_mvar`, `va_degree`, `vm_pu` |
| `net.res_ext_grid` | `p_mw`, `q_mvar` |
| `net.res_load` | `p_mw`, `q_mvar` |

Every input element type has a corresponding `res_*` table. Three-phase results use `_3ph` suffix with per-phase columns (e.g., `p_a_mw`, `p_b_mw`, `p_c_mw`).

### Element Creation API

Elements are added to the network via `pp.create_*()` functions that return the integer index of the created element:

```python
net = pp.create_empty_network(f_hz=60)
b0 = pp.create_bus(net, vn_kv=345, name="Bus 0")
b1 = pp.create_bus(net, vn_kv=345, name="Bus 1")
pp.create_line_from_parameters(net, from_bus=b0, to_bus=b1, length_km=100,
                                r_ohm_per_km=0.01, x_ohm_per_km=0.1,
                                c_nf_per_km=10, max_i_ka=1.0)
pp.create_gen(net, bus=b1, p_mw=100, vm_pu=1.0, controllable=True,
              min_p_mw=0, max_p_mw=200)
pp.create_ext_grid(net, bus=b0, vm_pu=1.0)
pp.create_load(net, bus=b1, p_mw=80, q_mvar=20)
```

Batch creation functions exist for multiple elements: `pp.create_buses()`, `pp.create_lines()`, `pp.create_gens()`, `pp.create_loads()`, etc. -- these accept arrays and return arrays of indices.

Standard types (predefined line/trafo parameters) via `pp.create_line(net, from_bus, to_bus, length_km, std_type="NAYY 4x50 SE")` and `pp.available_std_types(net, "line")`.

Source: Introspection of `pp.create_*` function signatures, pandapower 3.4.0.

### Power Flow Solvers

#### AC Power Flow: `pp.runpp()`

```python
pp.runpp(net, algorithm='nr', calculate_voltage_angles=True, init='auto',
         max_iteration='auto', tolerance_mva=1e-08, trafo_model='t',
         enforce_q_lims=False, distributed_slack=False, tdpf=False)
```

**Available algorithms (`algorithm` parameter):**

| Algorithm | Value | Notes |
|-----------|-------|-------|
| Newton-Raphson | `"nr"` | Default. PYPOWER implementation with numba acceleration. Max iter default: 10 |
| Iwamoto NR | `"iwamoto_nr"` | More robust but potentially slower |
| Backward/Forward Sweep | `"bfsw"` | Suited for radial/weakly-meshed networks. Max iter default: 100 |
| Gauss-Seidel | `"gs"` | PYPOWER implementation. Max iter default: 1000 |
| Fast-Decoupled BX | `"fdbx"` | PYPOWER implementation. Max iter default: 30 |
| Fast-Decoupled XB | `"fdxb"` | PYPOWER implementation. Max iter default: 30 |

**External solver backends:**

| Backend | Entry point | Notes |
|---------|------------|-------|
| lightsim2grid | `pp.runpp(net)` with lightsim2grid installed | C++ NR solver, auto-detected. Significantly faster. Available in this install. |
| PowerGridModel | `pp.runpp_pgm(net, algorithm='nr')` | C++ solver, separate entry point. NOT available in this install (`PGM_IMPORTED=False`). |

**Key features:**
- `distributed_slack=True`: Distributes slack power among multiple generators/ext_grids weighted by `slack_weight` column
- `tdpf=True`: Temperature-dependent power flow (conductor temperature affects impedance)
- `voltage_depend_loads=True`: ZIP load model using `const_z_p_percent`, `const_i_p_percent` columns
- `enforce_q_lims=True`: Enforces reactive power limits on generators (PV->PQ switching)
- `trafo_model='t'` or `'pi'`: T-equivalent or pi-equivalent transformer model
- Initialization: `"flat"`, `"dc"` (DC loadflow first), `"results"` (reuse previous solution), `"auto"`

Source: `inspect.getdoc(pp.runpp)`, pandapower 3.4.0. [runpp docs](https://pandapower.readthedocs.io/en/latest/)

#### DC Power Flow: `pp.rundcpp()`

```python
pp.rundcpp(net, trafo_model='t', trafo_loading='current',
           check_connectivity=True, switch_rx_ratio=2)
```

DC power flow assumes flat voltage (1.0 pu everywhere), no reactive power, and lossless lines. Results in `net.res_bus` show `vm_pu=1.0` for all buses; `net.res_line.pl_mw=0.0` for all lines (no losses in DCPF). Active power flows and angles are computed.

Source: Verified by running `pp.rundcpp()` on case9, pandapower 3.4.0.

#### Three-Phase Unbalanced: `pp.runpp_3ph()`

```python
pp.runpp_3ph(net, calculate_voltage_angles=True, init='auto',
             max_iteration='auto', tolerance_mva=1e-08)
```

Uses `asymmetric_load` and `asymmetric_sgen` element tables for unbalanced loads/generators. Results in `res_*_3ph` tables with per-phase columns (`p_a_mw`, `p_b_mw`, `p_c_mw`, etc.).

Source: Function signature introspection, pandapower 3.4.0.

### Optimal Power Flow

#### AC OPF: `pp.runopp()`

```python
pp.runopp(net, verbose=False, calculate_voltage_angles=True,
          init='flat', delta=1e-10, consider_line_temperature=False)
```

Uses PYPOWER's interior point solver. Requires:
1. **Cost functions** on controllable elements via `pp.create_poly_cost()` or `pp.create_pwl_cost()`
2. **Controllable flag** set to `True` on elements that should be dispatched
3. **Constraints** via element columns: `net.bus.min_vm_pu/max_vm_pu`, `net.line.max_loading_percent`, `net.trafo.max_loading_percent`
4. **Flexibility bounds**: `net.gen.min_p_mw/max_p_mw`, `net.gen.min_q_mvar/max_q_mvar`, etc.

**OPF result access:**
- `net.res_bus.lam_p` -- Active power LMP (dual variable), units: EUR/MW
- `net.res_bus.lam_q` -- Reactive power marginal price (dual variable), units: EUR/Mvar
- `net.res_gen.p_mw` -- Optimal dispatch
- `net.OPF_converged` -- Boolean convergence flag

Verified: On case9, `pp.runopp()` converges and populates `lam_p` with distinct nodal prices (e.g., 24.06-25.15 EUR/MW range), confirming LMP extraction works.

Source: `inspect.getdoc(pp.runopp)` and live test on case9, pandapower 3.4.0.

#### DC OPF: `pp.rundcopp()`

```python
pp.rundcopp(net, verbose=False, delta=1e-10, switch_rx_ratio=0.5)
```

DC approximation of OPF (linearized, lossless). Same cost/constraint setup as AC OPF.

Source: Function signature introspection, pandapower 3.4.0.

### PowerModels.jl Interface

pandapower interfaces with [PowerModels.jl](https://lanl-ansi.github.io/PowerModels.jl/stable/) via JSON data exchange, enabling advanced OPF formulations. Requires Julia + PowerModels.jl installation.

**Available `runpm*` functions:**

| Function | Purpose | Default `pm_model` | Default `pm_solver` |
|----------|---------|-------------------|-------------------|
| `pp.runpm()` | General PowerModels interface | `ACPPowerModel` | `ipopt` |
| `pp.runpm_ac_opf()` | AC OPF via PowerModels | `ACPPowerModel` | `ipopt` |
| `pp.runpm_dc_opf()` | DC OPF via PowerModels | `DCPPowerModel` | `ipopt` |
| `pp.runpm_ots()` | Optimal Transmission Switching | `DCPPowerModel` | `juniper` (MINLP) |
| `pp.runpm_tnep()` | Transmission Network Expansion Planning | `ACPPowerModel` | `juniper` |
| `pp.runpm_storage_opf()` | Multi-period storage OPF | `ACPPowerModel` | `juniper` |
| `pp.runpm_pf()` | Power flow via PowerModels | varies | `ipopt` |
| `pp.runpm_ploss()` | Minimize active power losses | varies | varies |
| `pp.runpm_qflex()` | Reactive power flexibility | varies | varies |
| `pp.runpm_vstab()` | Voltage stability optimization | varies | varies |
| `pp.runpm_loading()` | Minimize branch loading | varies | varies |
| `pp.runpm_multi_qflex()` | Multi-objective Q flexibility | varies | varies |
| `pp.runpm_multi_vstab()` | Multi-objective V stability | varies | varies |

**Configurable PowerModels formulations (`pm_model` parameter):**
- `ACPPowerModel` -- AC polar (nonconvex NLP)
- `ACRPowerModel` -- AC rectangular (nonconvex NLP)
- `DCPPowerModel` -- DC linearization (LP)
- `SOCWRPowerModel` -- Second-order cone relaxation
- `SOCBFPowerModel` -- SOC branch flow
- `QCRMPowerModel` -- Quadratic convex relaxation
- `SDPWRMPowerModel` -- Semidefinite programming relaxation

**Solver options:**
- `pm_solver`: Main solver (default `ipopt` for NLP, `juniper` for MINLP)
- `pm_mip_solver`: MIP sub-solver (default `highs`)
- `pm_nl_solver`: NL sub-solver (default `ipopt`)
- `pm_time_limits`, `pm_log_level`, `pm_tol`: Runtime controls

Source: Function signature introspection, pandapower 3.4.0. [PowerModels.jl docs](https://lanl-ansi.github.io/PowerModels.jl/stable/)

### Contingency Analysis

```python
from pandapower.contingency import run_contingency, run_contingency_ls2g

run_contingency(net, nminus1_cases, pf_options=None,
                pf_options_nminus1=None, write_to_net=True,
                contingency_evaluation_function=pp.runpp)
```

- `nminus1_cases`: dict specifying which lines/trafos to trip
- Runs base case + all N-1 contingencies
- `run_contingency_ls2g()`: Uses lightsim2grid C++ backend for faster N-1 screening
- `report_contingency_results()` and `check_elements_within_limits()` for post-analysis
- **No built-in SCOPF optimizer** -- contingency analysis is a screening/reporting tool, not a security-constrained optimization

Source: `pandapower.contingency` module introspection, pandapower 3.4.0. [Contingency analysis docs](https://pandapower.readthedocs.io/en/latest/contingency.html)

### State Estimation

```python
from pandapower.estimation import estimate
estimate(net, algorithm='wls', init='flat')
```

Algorithms: `WLSAlgorithm`, `IRWLSAlgorithm` (iteratively reweighted), `LPAlgorithm`, `AFWLSAlgorithm` (augmented), `WLSZeroInjectionConstraintsAlgorithm`.

Measurements are added via `pp.create_measurement(net, meas_type, element_type, value, std_dev, element, side)`. Results in `res_bus_est`, `res_line_est`, etc.

Source: `pandapower.estimation` module introspection, pandapower 3.4.0.

### Short-Circuit Calculation

```python
from pandapower.shortcircuit import calc_sc
calc_sc(net, ...)
```

IEC 60909 short-circuit calculations. Results in `res_bus_sc`, `res_line_sc`, etc. Also `calc_sc_on_line()` for fault location along a line.

Source: `pandapower.shortcircuit` module introspection, pandapower 3.4.0.

### Loss Modeling

- **ACPF**: Full loss modeling. `net.res_line.pl_mw` and `net.res_line.ql_mvar` contain per-line active/reactive losses. Transformer losses in `net.res_trafo.pl_mw` / `ql_mvar`. Verified: case9 shows non-zero line losses (0.09-2.46 MW range).
- **DCPF**: Lossless by definition. All `pl_mw = 0.0`.
- **AC OPF**: Full losses included in optimization (via PYPOWER interior point).
- **DC OPF**: Lossless approximation.
- **PowerModels.jl**: Loss handling depends on formulation (ACP includes losses, DCP does not).

Source: Verified by running `pp.runpp()` and `pp.rundcpp()` on case9, pandapower 3.4.0.

### Input/Output Formats

| Format | Read | Write | Function |
|--------|------|-------|----------|
| JSON (native) | Yes | Yes | `pp.from_json()` / `pp.to_json()` |
| Excel | Yes | Yes | `pp.from_excel()` / `pp.to_excel()` |
| Pickle | Yes | Yes | `pp.from_pickle()` / `pp.to_pickle()` |
| SQLite | Yes | Yes | `pp.from_sqlite()` / `pp.to_sqlite()` |
| PostgreSQL | Yes | Yes | `pp.from_postgresql()` / `pp.to_postgresql()` |
| MATPOWER `.m` | Yes | Yes | `from_mpc()` / `to_mpc()` from `pandapower.converter.matpower` |
| MATPOWER `.mat` | Yes | Yes | `from_mpc()` (via scipy.io) |
| Dict of DataFrames | Yes | Yes | `pp.from_dict_of_dfs()` / `pp.to_dict_of_dfs()` |
| JSON string | Yes | -- | `pp.from_json_string()` |
| JSON dict | Yes | -- | `pp.from_json_dict()` |

MATPOWER import: `from_mpc(mpc_file, f_hz=50, casename_mpc_file='mpc', validate_conversion=False)` -- supports `.m` (via matpowercaseframes) and `.mat` (via scipy.io).

Source: I/O function introspection, pandapower 3.4.0. [MATPOWER converter docs](https://pandapower.readthedocs.io/en/latest/converter/matpower.html)

### Built-in Test Networks

pandapower includes ~50+ built-in networks accessible via `pandapower.networks`:
- **IEEE/MATPOWER cases**: `case5`, `case9`, `case14`, `case24_ieee_rts`, `case30`, `case39`, `case57`, `case118`, `case300`, `case_ieee30`, `case_illinois200`
- **PEGASE cases**: `case89pegase`, `case1354pegase`, `case2869pegase`, `case9241pegase`
- **RTE cases**: `case1888rte`, `case2848rte`, `case6470rte`, `case6495rte`, `case6515rte`
- **CIGRE networks**: `create_cigre_network_hv()`, `create_cigre_network_mv()`, `create_cigre_network_lv()`
- **Distribution networks**: Kerber feeders, Dickert LV networks, Schutterwald LV
- **Simple examples**: `example_simple()`, `example_multivoltage()`, `simple_four_bus_system()`

Source: `pandapower.networks` module introspection, pandapower 3.4.0.

### Timeseries Simulation

```python
from pandapower.timeseries import run_timeseries, DFData, OutputWriter

ds = DFData(time_series_dataframe)
ow = OutputWriter(net, output_path="results/")
run_timeseries(net, time_steps=range(96))
```

Runs sequential power flows over time steps with data sources driving element parameter changes. Uses `ConstControl` objects to map data source columns to net element values at each step.

Source: `pandapower.timeseries` module introspection, pandapower 3.4.0.

### Control Framework

pandapower includes a controller framework for iterative control loops within power flow:

- `ConstControl` -- Maps data source values to element parameters
- `ContinuousTapControl` / `DiscreteTapControl` -- Transformer tap changers
- `TrafoController` -- General transformer control
- `DroopControl` / `VDroopControl_local` -- Droop-based voltage/frequency control
- `BinarySearchControl` -- Binary search convergence controller
- `DERController` -- Distributed energy resource control
- `PQController` -- Active/reactive power control

Controllers are stored in `net.controller` DataFrame and executed iteratively during `runpp(net, run_control=True)`.

Source: `pandapower.control` module introspection, pandapower 3.4.0.

### Topology Analysis

Graph-based network analysis via NetworkX:

```python
from pandapower.topology import create_nxgraph, connected_components
graph = create_nxgraph(net)
components = connected_components(graph)
```

Functions include: `calc_distance_to_bus`, `determine_stubs`, `unsupplied_buses`, `elements_on_path`, `lines_on_path`, `find_graph_characteristics`.

Source: `pandapower.topology` module introspection, pandapower 3.4.0.

## Formulation Coverage Summary

| Problem | Supported | Entry Point | Solver |
|---------|-----------|-------------|--------|
| AC Power Flow (balanced) | Yes | `pp.runpp()` | NR/Iwamoto/BFSW/GS/FD (PYPOWER+numba), lightsim2grid, PGM |
| DC Power Flow | Yes | `pp.rundcpp()` | Linear solve (PYPOWER) |
| AC Power Flow (3-phase unbalanced) | Yes | `pp.runpp_3ph()` | Newton-Raphson |
| AC OPF | Yes | `pp.runopp()` or `pp.runpm_ac_opf()` | Interior point (PYPOWER) or Ipopt (PowerModels.jl) |
| DC OPF | Yes | `pp.rundcopp()` or `pp.runpm_dc_opf()` | Interior point (PYPOWER) or Ipopt (PowerModels.jl) |
| OPF with relaxations (SOC, SDP, QC) | Yes (via PowerModels.jl) | `pp.runpm(pm_model=...)` | Ipopt, MOSEK, SCS |
| Optimal Transmission Switching | Yes (via PowerModels.jl) | `pp.runpm_ots()` | Juniper (MINLP) |
| Transmission Expansion Planning | Yes (via PowerModels.jl) | `pp.runpm_tnep()` | Juniper (MINLP) |
| Multi-period Storage OPF | Yes (via PowerModels.jl) | `pp.runpm_storage_opf()` | Juniper (MINLP) |
| Contingency Analysis (N-1) | Yes | `contingency.run_contingency()` | Sequential PF |
| Security-Constrained OPF (SCOPF) | **No** | -- | -- |
| Unit Commitment (SCUC) | **No** | -- | -- |
| Economic Dispatch (SCED) | **No** | -- | -- |
| State Estimation | Yes | `estimation.estimate()` | WLS variants, LP |
| Short-Circuit (IEC 60909) | Yes | `shortcircuit.calc_sc()` | Analytical |
| Loss Minimization | Yes (via PowerModels.jl) | `pp.runpm_ploss()` | Ipopt |

## Sources

1. [pandapower official website](https://www.pandapower.org/)
2. [pandapower documentation v3.4.0](https://pandapower.readthedocs.io/en/latest/)
3. [pandapower GitHub repository](https://github.com/e2nIEE/pandapower)
4. [pandapower OPF formulation docs](https://pandapower.readthedocs.io/en/v2.4.0/opf/formulation.html)
5. [MATPOWER converter docs](https://pandapower.readthedocs.io/en/latest/converter/matpower.html)
6. [Contingency analysis docs](https://pandapower.readthedocs.io/en/latest/contingency.html)
7. [pandapower IEEE paper (Thurner et al., 2018)](https://ieeexplore.ieee.org/document/8344496/)
8. [PowerModels.jl documentation](https://lanl-ansi.github.io/PowerModels.jl/stable/)
9. Source code introspection: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/`, pandapower 3.4.0
10. [pandapower distributed slack issue #771](https://github.com/e2nIEE/pandapower/issues/771)
11. [Pp OPF three-phase OPF paper](https://arxiv.org/pdf/2211.11032)

## Gaps and Uncertainties

- **No SCUC/SCED**: pandapower has no unit commitment or security-constrained economic dispatch. It is a steady-state tool, not a production cost model. For UC, a separate tool (e.g., PowerSimulations.jl, PLEXOS) would be needed.
- **No native SCOPF**: Contingency analysis is available for screening, but there is no built-in security-constrained OPF optimizer that jointly optimizes base case + contingencies. The PowerModels.jl interface could potentially be extended for this via custom Julia files (`julia_file` parameter in `runpm`).
- **LMP extraction from DC OPF**: Verified for AC OPF (`res_bus.lam_p`). Not tested for `rundcopp()` -- needs verification that dual variables are populated for the DC case as well.
- **PowerModels.jl availability**: The PowerModels.jl interface requires a Julia installation with PowerModels.jl. Not tested in this devcontainer environment.
- **PowerGridModel backend**: `PGM_IMPORTED=False` in this install. The `runpp_pgm()` function exists but the `power-grid-model` package is not installed.
- **Three-phase OPF**: `pp.runpp_3ph()` supports 3-phase power flow, but 3-phase OPF is a separate research effort (pp OPF paper, arxiv 2211.11032) and its integration status into mainline pandapower 3.4.0 is unclear.
- **Distributed slack in OPF**: The `distributed_slack` parameter exists in `runpp()` but not in `runopp()`. It is unclear whether OPF supports distributed slack or only single-slack formulation.
- **Custom OPF constraints**: The extent to which users can add arbitrary constraints beyond bus voltage and branch loading limits (e.g., interface flow limits, reserve requirements) to the native PYPOWER OPF is not documented. PowerModels.jl allows custom Julia extensions via the `julia_file` and `pp_to_pm_callback` parameters.

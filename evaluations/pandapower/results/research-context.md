# pandapower — Research: API & Formulations

**Version studied:** 3.4.0 (installed via `uv sync` in devcontainer)
**Repository:** [e2nIEE/pandapower](https://github.com/e2nIEE/pandapower) (1,118 stars, 556 forks, BSD-like license)
**Documentation:** [pandapower.readthedocs.io](https://pandapower.readthedocs.io/en/latest/)

## Key Findings

- **DataFrame-centric data model**: The network (`pandapowerNet`) is a dict-like object containing one pandas DataFrame per element type (bus, line, gen, load, trafo, etc.) and one `res_*` DataFrame per element for results. Over 25 element types supported.
- **Four core analysis functions**: `runpp()` (AC power flow), `rundcpp()` (DC power flow), `runopp()` (AC OPF), `rundcopp()` (DC OPF), plus `runpp_3ph()` for unbalanced 3-phase and `runpp_pgm()` via power-grid-model backend.
- **Six PF algorithms**: Newton-Raphson (`nr`), Iwamoto-NR (`iwamoto_nr`), backward/forward sweep (`bfsw`), Gauss-Seidel (`gs`), and two fast-decoupled variants (`fdbx`, `fdxb`).
- **OPF uses PYPOWER interior-point method** natively; alternatively routes to Julia PowerModels.jl via PandaModels.jl for AC/DC OPF, TNEP, OTS, storage OPF, and custom formulations.
- **No native SCUC or SCED** formulation — only continuous OPF. Unit commitment requires external modeling or the PandaModels.jl Julia bridge.
- **Rich converter ecosystem**: Import from MATPOWER (.m/.mat), PYPOWER (ppc dict), PowerFactory, CIM CGMES, UCTE-DEF, JAO Static Grid Model. Export to MATPOWER and PYPOWER formats.
- **Comprehensive I/O**: JSON (primary), pickle, Excel, SQLite, PostgreSQL serialization of full network state.
- **Performance backends**: numba JIT acceleration (default), lightsim2grid C++ backend for Newton-Raphson, power-grid-model C++ backend.
- **Beyond PF/OPF**: Short-circuit analysis (IEC 60909), weighted-least-squares state estimation, time-series simulation, topology analysis, and controller framework (tap changers, DER, droop).
- **Costs defined per-element** via `create_poly_cost()` (polynomial up to quadratic) or `create_pwl_cost()` (piecewise-linear), stored in `net.poly_cost` / `net.pwl_cost` DataFrames.

## Detailed Notes

### Data Model

The pandapower network object (`pandapowerNet`, subclass of `ADict`) is a dictionary of pandas DataFrames. Each element type gets its own DataFrame table, with columns for parameters and one row per element instance.

**Node elements:**
- `net.bus` — AC buses: columns `name, vn_kv, type, zone, in_service, geo`. OPF adds `min_vm_pu, max_vm_pu`.
- `net.bus_dc` — DC buses (same structure).

**Branch elements:**
- `net.line` — AC lines: `from_bus, to_bus, length_km, r_ohm_per_km, x_ohm_per_km, c_nf_per_km, g_us_per_km, max_i_ka, df, parallel, std_type, type, in_service`.
- `net.trafo` — 2-winding transformers: `hv_bus, lv_bus, sn_mva, vn_hv_kv, vn_lv_kv, vk_percent, vkr_percent, pfe_kw, i0_percent, shift_degree, tap_side/neutral/min/max/step_percent/pos, parallel, df`.
- `net.trafo3w` — 3-winding transformers with HV/MV/LV buses.
- `net.impedance` — General series impedance: `rft_pu, xft_pu, rtf_pu, xtf_pu, sn_mva`.
- `net.dcline` — DC line (point-to-point HVDC link).
- `net.line_dc` — DC line on DC bus system.
- `net.switch` — Switches connecting bus-bus, bus-line, or bus-trafo: `bus, element, et, type, closed, z_ohm`.
- `net.tcsc` — Thyristor-controlled series capacitor.

**Generation elements:**
- `net.ext_grid` — Slack/reference bus: `bus, vm_pu, va_degree, slack_weight`. Also `s_sc_max_mva` for short-circuit. The slack bus in pandapower.
- `net.gen` — PV generator (voltage-controlled): `bus, p_mw, vm_pu, sn_mva, min/max_q_mvar, min/max_p_mw, scaling, slack, controllable, slack_weight`.
- `net.sgen` — Static generator (PQ injection): `bus, p_mw, q_mvar, scaling, controllable, current_source`.
- `net.source_dc` — DC voltage source.

**Load elements:**
- `net.load` — AC load: `bus, p_mw, q_mvar, const_z/i_p/q_percent` (ZIP load model), `scaling, controllable, type` (wye/delta).
- `net.load_dc` — DC load.
- `net.motor` — Induction motor model.
- `net.asymmetric_load` / `net.asymmetric_sgen` — Per-phase (A/B/C) power for unbalanced analysis.

**Shunt/compensation elements:**
- `net.shunt` — Shunt: `bus, q_mvar, p_mw, vn_kv, step, max_step`.
- `net.svc` — Static VAR compensator.
- `net.ssc` — Static synchronous compensator (STATCOM).

**Equivalent elements:**
- `net.ward` — Ward equivalent: `ps_mw, qs_mvar, qz_mvar, pz_mw`.
- `net.xward` — Extended Ward: adds `r_ohm, x_ohm, vm_pu`.

**HVDC/VSC elements:**
- `net.vsc` — Voltage source converter: `bus, bus_dc, r_ohm, x_ohm, r_dc_ohm, pl_dc_mw, control_mode_ac/dc, control_value_ac/dc`.
- `net.vsc_bipolar`, `net.vsc_stacked` — Bipolar and stacked VSC configurations.

**Other:**
- `net.storage` — Energy storage: `p_mw, q_mvar, sn_mva, soc_percent, min/max_e_mwh`.
- `net.measurement` — Measurement data for state estimation.
- `net.group` — Element grouping.
- `net.controller` — Controller objects for quasi-static simulation.
- `net.poly_cost` / `net.pwl_cost` — Cost function tables for OPF.

**Standard types:** Lines and transformers can reference standard types (`std_type` column) from `net.std_types`, which provides libraries of manufacturer data (e.g., `"NAYY 4x50 SE"`). Parameters are auto-populated from the standard type catalog.

Source: `pp.create_empty_network()` table inspection; [pandapower elements docs](https://pandapower.readthedocs.io/en/latest/elements.html)

### Results Access Pattern

After running a power flow or OPF, results are stored in `res_*` DataFrames indexed identically to the input tables:

| Result table | Key columns |
|---|---|
| `net.res_bus` | `vm_pu, va_degree, p_mw, q_mvar` |
| `net.res_line` | `p_from_mw, q_from_mvar, p_to_mw, q_to_mvar, pl_mw, ql_mvar, i_from_ka, i_to_ka, i_ka, loading_percent` |
| `net.res_trafo` | `p_hv_mw, q_hv_mvar, p_lv_mw, q_lv_mvar, pl_mw, ql_mvar, i_hv_ka, i_lv_ka, loading_percent` |
| `net.res_gen` | `p_mw, q_mvar, va_degree, vm_pu` |
| `net.res_ext_grid` | `p_mw, q_mvar` |
| `net.res_load` | `p_mw, q_mvar` |
| `net.res_sgen` | `p_mw, q_mvar` |
| `net.res_storage` | `p_mw, q_mvar` |
| `net.res_dcline` | `p_from_mw, q_from_mvar, p_to_mw, q_to_mvar, pl_mw` |

The convergence status is stored in `net.converged` (bool) and `net.OPF_converged` (bool).

Bus power values use consumer sign convention: positive = consumption.

Source: `_empty_res_*` table inspection; [bus results docs](https://pandapower.readthedocs.io/en/latest/elements/bus.html)

### Power Flow (ACPF / DCPF)

**AC Power Flow — `pp.runpp()`**

```python
pp.runpp(net, algorithm='nr', calculate_voltage_angles=True, init='auto',
         max_iteration='auto', tolerance_mva=1e-08, trafo_model='t',
         trafo_loading='current', enforce_p_lims=False, enforce_q_lims=False,
         check_connectivity=True, voltage_depend_loads=True,
         consider_line_temperature=False, run_control=False,
         distributed_slack=False, tdpf=False, **kwargs)
```

Algorithm options:

| Algorithm | Description | Default max_iteration |
|---|---|---|
| `"nr"` | Newton-Raphson with numba | 10 |
| `"iwamoto_nr"` | NR with Iwamoto damping (more robust) | 10 |
| `"bfsw"` | Backward/forward sweep (radial networks) | 100 |
| `"gs"` | Gauss-Seidel (PYPOWER) | 1000 |
| `"fdbx"` | Fast-decoupled BX (PYPOWER) | 30 |
| `"fdxb"` | Fast-decoupled XB (PYPOWER) | 30 |

Initialization options: `"auto"` (DC if voltage angles, else flat), `"flat"` (1.0 pu, 0 deg), `"dc"` (DC presolve), `"results"` (reuse prior solution).

Special features:
- **ZIP load model**: `const_z_p/q_percent, const_i_p/q_percent` on loads
- **Distributed slack**: `distributed_slack=True` with `slack_weight` on gen/ext_grid
- **Temperature-dependent power flow (TDPF)**: `tdpf=True`
- **Reactive power limit enforcement**: `enforce_q_lims=True`
- **Controller loop**: `run_control=True` runs outer-loop controllers (tap changers, etc.)

Performance backends:
- **numba** (default): JIT-compiled sparse matrix assembly
- **lightsim2grid**: C++ Newton-Raphson backend, enabled via `lightsim2grid=True` kwarg

Source: `inspect.signature(pp.runpp)`; [AC PF docs](https://pandapower.readthedocs.io/en/latest/powerflow/ac.html)

**DC Power Flow — `pp.rundcpp()`**

```python
pp.rundcpp(net, trafo_model='t', trafo_loading='current', recycle=None,
           check_connectivity=True, switch_rx_ratio=2, trafo3w_losses='hv', **kwargs)
```

Simpler interface — no algorithm choice (direct linear solve). Uses PYPOWER DC power flow internally.

Source: `inspect.signature(pp.rundcpp)`; [DC PF docs](https://pandapower.readthedocs.io/en/latest/powerflow/dc.html)

**3-Phase Unbalanced Power Flow — `pp.runpp_3ph()`**

```python
pp.runpp_3ph(net, calculate_voltage_angles=True, init='auto', max_iteration='auto',
             tolerance_mva=1e-08, trafo_model='t', trafo_loading='current',
             enforce_q_lims=False, numba=True, **kwargs)
```

Uses `asymmetric_load` / `asymmetric_sgen` elements. Results go to `res_*_3ph` tables with per-phase columns (`p_a_mw, p_b_mw, p_c_mw`, etc.).

**Power Grid Model Backend — `pp.runpp_pgm()`**

```python
pp.runpp_pgm(net, algorithm='nr', max_iterations=20, error_tolerance_vm_pu=1e-08,
             symmetric=True, validate_input=False)
```

Uses the [power-grid-model](https://github.com/PowerGridModel/power-grid-model) C++ library. Supports `"nr"`, `"bfsw"`, `"lc"` (linear current), `"lin"` (linear approximation). Can run symmetric or asymmetric 3-phase.

Source: `inspect.signature(pp.runpp_pgm)`

### Optimal Power Flow (AC OPF / DC OPF)

**AC OPF — `pp.runopp()`**

```python
pp.runopp(net, verbose=False, calculate_voltage_angles=True,
          check_connectivity=True, suppress_warnings=True, switch_rx_ratio=2,
          delta=1e-10, init='flat', numba=True, trafo3w_losses='hv',
          consider_line_temperature=False, **kwargs)
```

Uses PYPOWER's interior-point method. Init options: `"flat"` (midpoint of bounds) or `"pf"` (run power flow first).

**DC OPF — `pp.rundcopp()`**

```python
pp.rundcopp(net, verbose=False, check_connectivity=True,
            suppress_warnings=True, switch_rx_ratio=0.5, delta=1e-10,
            trafo3w_losses='hv', **kwargs)
```

**OPF constraints** are defined directly in element DataFrames:
- Generator/sgen/load/storage/ext_grid: `min_p_mw, max_p_mw, min_q_mvar, max_q_mvar` + `controllable=True`
- Bus: `min_vm_pu, max_vm_pu`
- Line: `max_loading_percent`
- Transformer: `max_loading_percent`

**Cost functions** stored in separate tables:
- `pp.create_poly_cost(net, element, et, cp1_eur_per_mw, cp0_eur=0, cp2_eur_per_mw2=0, ...)` — polynomial: `f(p) = cp2*p^2 + cp1*p + cp0`
- `pp.create_pwl_cost(net, element, et, points, power_type='p')` — piecewise-linear with breakpoints

The OPF **will not start** without cost functions defined. Constraints must also be specified; missing constraints cause errors.

Source: `inspect.getdoc(pp.runopp)`; [OPF formulation docs](https://pandapower.readthedocs.io/en/latest/opf/formulation.html)

### PandaModels.jl / PowerModels.jl Interface

pandapower provides a bridge to Julia's PowerModels.jl ecosystem via PandaModels.jl. This enables advanced optimization formulations not available in the native PYPOWER solver:

| Function | Formulation | Default solver |
|---|---|---|
| `pp.runpm_ac_opf()` | Non-linear AC OPF (ACPPowerModel) | ipopt |
| `pp.runpm_dc_opf()` | Linearized DC OPF (DCPPowerModel) | ipopt |
| `pp.runpm()` | Custom OPF with `pm_model` param | ipopt |
| `pp.runpm_tnep()` | Transmission network expansion planning | juniper (MINLP) |
| `pp.runpm_ots()` | Optimal transmission switching | juniper (MINLP) |
| `pp.runpm_storage_opf()` | Multi-timestep storage OPF | juniper |
| `pp.runpm_pf()` | Power flow via PowerModels | ipopt |
| `pp.runpm_loading()` | Minimize branch loading | ipopt |
| `pp.runpm_ploss()` | Minimize power losses | ipopt |
| `pp.runpm_vstab()` | Voltage stability optimization | ipopt |
| `pp.runpm_qflex()` | Reactive power flexibility | ipopt |

Solver options via parameters: `pm_solver` (NLP), `pm_mip_solver` (MIP, default `"highs"`), `pm_nl_solver` (NL sub-problem, default `"ipopt"`).

PowerModels model types can be specified via `pm_model`: `"ACPPowerModel"`, `"DCPPowerModel"`, `"SOCWRPowerModel"`, etc.

**Requirement**: Julia must be installed with PandaModels.jl and PowerModels.jl packages. The interface uses pyjulia to call Julia from Python.

Source: `inspect.signature(pp.runpm*)`; [PandaModels docs](https://pandapower.readthedocs.io/en/latest/opf/pandamodels.html)

### Solver Interfaces Summary

| Analysis | Solver | Backend | Notes |
|---|---|---|---|
| AC PF (NR) | Newton-Raphson | pandapower (numba) | Default, fastest |
| AC PF (NR) | Newton-Raphson | lightsim2grid (C++) | Optional acceleration |
| AC PF (NR/bfsw) | NR or BFS | power-grid-model (C++) | Via `runpp_pgm()` |
| AC PF (Iwamoto) | Iwamoto-NR | pandapower | More robust convergence |
| AC PF (GS/FD) | Gauss-Seidel, Fast-decoupled | PYPOWER | Legacy algorithms |
| DC PF | Linear solve | PYPOWER | Direct solve |
| AC/DC OPF | Interior point | PYPOWER | Native solver |
| AC/DC OPF | Ipopt, Gurobi, HiGHS | PowerModels.jl (Julia) | Via PandaModels bridge |
| TNEP/OTS | Juniper (MINLP) | PowerModels.jl (Julia) | Mixed-integer problems |

### Input/Output Formats

**Native serialization:**

| Function | Format | Notes |
|---|---|---|
| `pp.to_json()` / `pp.from_json()` | JSON | Primary format, supports encryption |
| `pp.to_pickle()` / `pp.from_pickle()` | Python pickle | Fast but not portable |
| `pp.to_excel()` / `pp.from_excel()` | Excel (.xlsx) | Human-readable |
| `pp.to_sqlite()` / `pp.from_sqlite()` | SQLite | Single-file database |
| `pp.to_postgresql()` / `pp.from_postgresql()` | PostgreSQL | Server-based storage |
| `pp.to_dict_of_dfs()` / `pp.from_dict_of_dfs()` | Dict of DataFrames | Programmatic interchange |

**External format converters (import):**

| Function | Source format |
|---|---|
| `pp.converter.matpower.from_mpc(file)` | MATPOWER .m or .mat (case v2) |
| `pp.converter.pypower.from_ppc(ppc_dict)` | PYPOWER case dict |
| `pp.converter.ucte.from_ucte(file)` | UCTE-DEF format |
| `pp.converter.cim` (module) | CIM CGMES (requires lxml) |
| `pp.converter.powerfactory` (module) | DIgSILENT PowerFactory |
| JAO Static Grid Model converter | JAO format |

**External format converters (export):**

| Function | Target format |
|---|---|
| `pp.converter.matpower.to_mpc(net, filename)` | MATPOWER .mat |
| `pp.converter.pypower.to_ppc(net)` | PYPOWER case dict |
| `pp.converter.pandamodels.to_pm(net)` | PowerModels.jl JSON |

Source: `inspect.signature(pp.from_*)` / `pp.to_*()`; [Converter docs](https://pandapower.readthedocs.io/en/latest/converter.html)

### Additional Analysis Capabilities

**Short-circuit analysis (`pp.shortcircuit`):**
- `pp.shortcircuit.calc_sc(net, fault='3ph', case='max')` — IEC 60909 compliant
- Supports 3-phase, 2-phase, and single-phase faults
- Parameters: `ip` (peak current), `ith` (thermal current), `tk_s` (fault duration)

**State estimation (`pp.estimation`):**
- `pp.estimation.estimate(net, algorithm='wls')` — weighted least squares
- Algorithms: WLS, IRWLS (iteratively reweighted), LP, optimization-based
- Bad data detection via chi-squared test and normalized residuals
- Measurements defined in `net.measurement` table

**Time series (`pp.timeseries`):**
- `pp.timeseries.run_timeseries(net, time_steps)` — loops power flow over time steps
- Data injection via `DFData` (DataFrame-based profiles) + `ConstControl` controllers
- Output capture via `OutputWriter` with configurable logging

**Topology analysis (`pp.topology`):**
- NetworkX graph creation: `pp.topology.create_nxgraph(net)`
- Connected components, shortest paths, stub detection
- Impedance-weighted graph for distance calculations

**Controller framework (`pp.control`):**
- `DiscreteTapControl` / `ContinuousTapControl` — transformer tap changers
- `DERController` — distributed energy resource Q control
- `DroopControl` — voltage droop characteristic
- `ConstControl` — time-series data injection
- `BinarySearchControl` — generic setpoint control
- Controllers run in outer loop around power flow

**Built-in test networks (`pp.networks`):**
- IEEE cases: 9, 14, 24 RTS, 30, 39, 57, 118, 145, 300
- PEGASE cases: 89, 1354, 2869, 9241
- RTE cases: 1888, 2848, 6470, 6495, 6515
- European distribution: CIGRE HV/MV/LV, Kerber variants, Dickert LV
- Synthetic: `example_simple()`, `example_multivoltage()`

Source: function inspection in devcontainer; [pandapower.org/about](https://www.pandapower.org/about/)

### Network Creation Pattern

```python
import pandapower as pp

net = pp.create_empty_network(name='', f_hz=50.0, sn_mva=1)

# Add buses
b1 = pp.create_bus(net, vn_kv=110, name="HV Bus")
b2 = pp.create_bus(net, vn_kv=20, name="MV Bus")

# Add external grid (slack)
pp.create_ext_grid(net, bus=b1, vm_pu=1.02, va_degree=0)

# Add transformer
pp.create_transformer(net, hv_bus=b1, lv_bus=b2, std_type="25 MVA 110/20 kV")

# Add line
b3 = pp.create_bus(net, vn_kv=20)
pp.create_line(net, from_bus=b2, to_bus=b3, length_km=10, std_type="NAYY 4x50 SE")

# Add load
pp.create_load(net, bus=b3, p_mw=2, q_mvar=0.5)

# Add generator
pp.create_gen(net, bus=b3, p_mw=1, vm_pu=1.0)

# Run power flow
pp.runpp(net)

# Access results
print(net.res_bus)    # voltages
print(net.res_line)   # line flows and loading
```

### Internal Data Flow (PF execution)

1. Element DataFrames → `pd2ppc()` converts to PYPOWER/MATPOWER-style bus-branch arrays (`net._ppc`)
2. Bus-branch model solved by selected algorithm
3. Results mapped back via `net._pd2ppc_lookups` → `res_*` DataFrames populated
4. `net.converged` set to True/False

Source: [internal datastructure tutorial](https://github.com/e2nIEE/pandapower/blob/develop/tutorials/internal_datastructure.ipynb)

## Sources

1. [pandapower GitHub repository](https://github.com/e2nIEE/pandapower) — v3.4.0
2. [AC Power Flow documentation](https://pandapower.readthedocs.io/en/latest/powerflow/ac.html)
3. [DC Power Flow documentation](https://pandapower.readthedocs.io/en/latest/powerflow/dc.html)
4. [OPF documentation](https://pandapower.readthedocs.io/en/latest/opf.html)
5. [OPF formulation](https://pandapower.readthedocs.io/en/latest/opf/formulation.html)
6. [PYPOWER OPF solver](https://pandapower.readthedocs.io/en/latest/opf/pypower_run.html)
7. [PandaModels.jl interface](https://pandapower.readthedocs.io/en/latest/opf/pandamodels.html)
8. [Elements documentation](https://pandapower.readthedocs.io/en/latest/elements.html)
9. [Bus element docs](https://pandapower.readthedocs.io/en/latest/elements/bus.html)
10. [Converter documentation](https://pandapower.readthedocs.io/en/latest/converter.html)
11. [MATPOWER converter](https://pandapower.readthedocs.io/en/latest/converter/matpower.html)
12. [State estimation docs](https://pandapower.readthedocs.io/en/latest/estimation.html)
13. [About pandapower](https://www.pandapower.org/about/)
14. [pandapower paper (arXiv:1709.06743)](https://arxiv.org/abs/1709.06743)
15. Source code inspection: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/`

## Gaps and Uncertainties

- **No native SCUC/SCED**: pandapower does not have built-in security-constrained unit commitment or economic dispatch. The closest is DC OPF with generator constraints. Whether PandaModels.jl bridge supports SCUC-like formulations via custom Julia files needs verification.
- **LMP extraction**: The native PYPOWER OPF does not appear to directly expose locational marginal prices (bus shadow prices / dual variables). Need to verify whether `runopp()` populates any dual/shadow price results, or whether only PandaModels.jl provides this.
- **Contingency analysis**: No dedicated N-1 contingency analysis function found. Would need to be implemented manually by looping over contingencies and re-running power flow.
- **lightsim2grid integration depth**: Documentation mentions it but specifics on activation, limitations, and which analyses it supports (PF only? OPF?) need testing.
- **PandaModels.jl actual availability**: The Julia bridge requires separate Julia installation and package setup. Whether this works reliably in the devcontainer environment is untested.
- **CIM CGMES converter**: Requires `lxml` package which is not installed in the current environment. Functionality untested.
- **PowerFactory converter**: Requires PowerFactory installation. Cannot be tested in this environment.
- **OPF convergence robustness**: The PYPOWER interior-point solver may struggle with large networks. Practical scalability limits for `runopp()` vs `runpm_ac_opf()` are unknown.
- **Cost function limitations**: The native PYPOWER OPF supports polynomial (up to quadratic) and piecewise-linear costs. Whether higher-order polynomials work needs verification.
- **DC OPF bus dual variables**: Whether `rundcopp()` returns bus marginal prices (shadow prices on power balance constraints) is not documented and needs testing.

---

# pandapower — Research: Extensions & Architecture

## Key Findings

- **pandapowerNet is a dict-of-DataFrames**: The core data structure (`pandapowerNet`) inherits from `ADict` (attribute-accessible dict). Every element type (bus, line, load, gen, trafo, etc.) is a pandas DataFrame, making the entire network natively interoperable with the pandas ecosystem. Users can freely add columns to existing tables or add entirely new keys to the dict without breaking power flow.
- **Controller framework provides the primary extension point**: Custom controllers inherit from `Controller` (or `BasicCtrl`) and override lifecycle methods (`time_step`, `initialize_control`, `control_step`, `is_converged`, `finalize_step`, etc.). Controllers are stored in `net.controller` DataFrame and auto-participate in time-series simulations and the control loop.
- **No formal plugin/registration API for new element types**: There is no `register_element()` or plugin system. Adding a new element type that participates in power flow requires modifying the internal `pd2ppc` conversion pipeline and result extraction — effectively forking the core code.
- **PYPOWER userfcn callback system for OPF constraints**: The inherited PYPOWER `add_userfcn`/`run_userfcn` mechanism supports callbacks at 5 stages (`ext2int`, `formulation`, `int2ext`, `printpf`, `savecase`). The `formulation` stage allows adding custom linear constraints and variables to the OPF model via `om.add_constraints()` and `om.add_vars()`.
- **NetworkX graph is a first-class output**: `pandapower.topology.create_nxgraph()` converts any network to a NetworkX `MultiGraph` with buses as nodes and branches as edges. Edge attributes include impedance data. An alternative `graph-tool` backend is also supported via `GraphToolInterface`.
- **Multiple solver backends**: Power flow supports NumPy/SciPy (default), Numba JIT acceleration, lightsim2grid (C++ backend, ~20x speedup), and power-grid-model (C++ steady-state solver). These are selected via `runpp()` kwargs, not a formal backend abstraction.
- **Rich serialization**: Networks can be saved/loaded as JSON, pickle, Excel, SQLite, PostgreSQL, and MATPOWER `.mat` files. JSON serialization handles custom controllers via `JSONSerializableClass`.
- **Converter ecosystem**: Bidirectional converters exist for PYPOWER/MATPOWER format, CIM (IEC 61970), PowerFactory (DIgSILENT), UCTE-DEF, and PowerModels.jl (via PandaModels.jl). pandapipes provides multi-energy coupling.
- **Architecture is modular but tightly coupled**: The codebase is organized into clear subpackages (control, topology, timeseries, opf, estimation, protection, etc.), but the power flow pipeline (`runpp` → `_powerflow` → `_pd2ppc` → `_run_pf_algorithm` → `_extract_results`) has hardcoded element-type handling throughout, limiting extensibility for new element types.
- **No Graphs.jl interop**: pandapower is pure Python. There is no Julia graph library interop beyond the PowerModels.jl OPF integration (which serializes to JSON, not graph objects).

## Detailed Notes

### Data Structure: pandapowerNet

The `pandapowerNet` class (defined in `auxiliary.py`, line 342) inherits from `ADict`, which itself is a dict subclass allowing attribute-style access (`net.bus` == `net["bus"]`). Every element type is a pandas DataFrame with typed columns defined in `network_structure.py`.

An empty network contains ~120+ keys including element tables, result tables (`res_*`), empty result templates (`_empty_res_*`), internal state (`_ppc`, `_pd2ppc_lookups`), and metadata (`version`, `f_hz`, `sn_mva`).

Users can add arbitrary keys: `net["my_custom_data"] = pd.DataFrame(...)` — this is preserved through serialization (JSON/pickle) and does not interfere with power flow. Existing element tables can also receive additional columns freely.

**Source:** `pandapower/auxiliary.py` lines 342-422; `pandapower/network_structure.py`

### Controller Framework (Primary Extension API)

The controller system has a two-level class hierarchy:

1. **`BasicCtrl`** (`control/basic_controller.py`): Base class with lifecycle hooks:
   - `time_step(container, time)` — called at start of each time step (time-series only)
   - `initialize_control(container)` — called after initial power flow, before control
   - `control_step(container)` — called when `is_converged()` returns False
   - `is_converged(container)` — check if controller has converged
   - `repair_control(container)` — recover from power flow divergence
   - `restore_init_state(container)` — restore pre-control state
   - `finalize_control(container)` — cleanup after control loop
   - `finalize_step(container, time)` — cleanup after each time step (time-series only)

2. **`Controller`** (subclass of `BasicCtrl`): Adds pandapower-specific registration — automatically adds itself to `net.controller` DataFrame with columns: `object`, `in_service`, `order`, `level`, `initial_run`, `recycle`.

**Predefined controllers** include:
- `ConstControl` — applies constant values from data sources to network elements
- `ContinuousTapControl`, `DiscreteTapControl` — transformer tap changers
- `DERController` — distributed energy resource voltage/var control
- `TrafoControl`, `ShuntControl`, `PQControl`, `StationControl`
- `CharacteristicControl` — piecewise-linear characteristic curves

The control loop (`run_control.py`) supports multi-level execution ordering via the `level` and `order` columns. Controllers at the same level run in a convergence loop; levels execute sequentially.

**Source:** `pandapower/control/basic_controller.py`; `pandapower/control/run_control.py`; [Building a Controller tutorial](https://github.com/e2nIEE/pandapower/blob/develop/tutorials/building_a_controller.ipynb)

### PYPOWER User Function Callbacks (OPF Extension)

pandapower inherits PYPOWER's `userfcn` callback mechanism for extending the OPF:

```python
from pandapower.pypower.add_userfcn import add_userfcn
ppci = add_userfcn(ppci, 'formulation', my_callback, args=my_data)
```

Five callback stages:
1. **`ext2int`** — after external-to-internal index conversion
2. **`formulation`** — after OPF model setup, before solving (add constraints/vars/costs here)
3. **`int2ext`** — before converting results back to external indexing
4. **`printpf`** — after result pretty-printing
5. **`savecase`** — when saving case to file

The `formulation` callback receives the OPF model object (`om`) which exposes:
- `om.add_constraints(name, A, l, u, varsets)` — add linear constraints `l <= A*x <= u`
- `om.add_vars(name, N, v0, vl, vu)` — add optimization variables
- `om.get_ppc()` — access the PYPOWER case dict

pandapower uses this internally for DC line constraints (see `_add_dcline_constraints` in `optimal_powerflow.py`).

**Limitation:** Only linear constraints can be added by users. Nonlinear constraint support exists in the data structure but has no public user-facing API.

**Source:** `pandapower/pypower/add_userfcn.py`; `pandapower/pypower/run_userfcn.py`; `pandapower/pypower/opf_model.py` lines 176-255; `pandapower/optimal_powerflow.py`

### PowerModels.jl Integration (Advanced OPF Extension)

The `runpm()` function provides a bridge to PowerModels.jl via PandaModels.jl:
- Supports custom Julia optimization files (`julia_file` parameter)
- Accepts a `pp_to_pm_callback` function to inject additional data into the PowerModels JSON data structure before solving
- Configurable model type (`pm_model="ACPPowerModel"`, `"DCPPowerModel"`, etc.)
- Configurable solver (`pm_solver="ipopt"`, `"juniper"` for MINLP, etc.)

This is the most flexible OPF extension path, as PowerModels.jl supports arbitrary nonlinear formulations, but requires Julia runtime.

**Source:** `pandapower/runpm.py`; `pandapower/opf/run_pandamodels.py`

### Network Graph Access (NetworkX)

`pandapower.topology.create_nxgraph()` provides comprehensive graph conversion:

```python
import pandapower.topology as top
mg = top.create_nxgraph(net, respect_switches=True)
```

Parameters control which elements become edges:
- `include_lines`, `include_trafos`, `include_trafo3ws`, `include_impedances`
- `include_dclines`, `include_tcsc`, `include_vsc`, `include_line_dc`
- `calc_branch_impedances=True` adds `r_ohm`, `x_ohm`, `z_ohm` edge attributes
- `branch_impedance_unit="ohm"` or `"pu"`
- `multi=True` returns `MultiGraph` (allows parallel edges), `False` returns `Graph`
- `library="networkx"` (default) or `"graph_tool"` (if graph-tool installed)

Graph analysis functions in `topology/graph_searches.py`:
- `connected_component(mg, bus)` / `connected_components(mg)`
- `calc_distance_to_bus(mg, bus)`
- `unsupplied_buses(net)`
- `determine_stubs(net)`
- `lines_on_path(mg, path)` / `elements_on_path(mg, path, element)`
- `find_basic_graph_characteristics(g, roots, characteristics)`
- `get_2connected_buses(g, roots)`

The `graph-tool` backend (`GraphToolInterface`) wraps `graph_tool.Graph` with a NetworkX-compatible API for performance on large networks.

**Source:** `pandapower/topology/create_graph.py`; `pandapower/topology/graph_searches.py`; `pandapower/topology/graph_tool_interface.py`

### Power Flow Pipeline Architecture

The power flow execution chain:

1. `runpp(net, ...)` — public API, validates options, delegates
2. `_powerflow(net, ...)` — creates auxiliary elements, initializes results
3. `_pd2ppc(net, ...)` — converts pandapower DataFrames → PYPOWER case dict (ppc)
   - `_build_bus_ppc()` — bus table
   - `_build_gen_ppc()` — generator table
   - `_build_branch_ppc()` — line/trafo/impedance → branch table
   - `_calc_pq_elements_and_add_on_ppc()` — loads/sgens → bus injections
   - `_build_svc_ppc()`, `_build_tcsc_ppc()`, `_build_vsc_ppc()` — FACTS devices
4. `_ppc2ppci(ppc, net)` — remove out-of-service elements
5. `_run_pf_algorithm(ppci, options)` — dispatch to solver:
   - `_run_newton_raphson_pf()` (default "nr")
   - `_run_bfswpf()` (backward/forward sweep)
   - `_run_dc_pf()` (DC approximation)
   - `_runpf_pypower()` (Gauss-Seidel, fast-decoupled)
6. `_extract_results(net, result)` — writes results back to `net.res_*` DataFrames

Each step has hardcoded handling for known element types. Adding a new element type requires changes in `pd2ppc.py`, `build_bus.py`/`build_branch.py`/`build_gen.py`, `results.py`/`results_bus.py`/`results_branch.py`, and `network_structure.py`.

**Source:** `pandapower/run.py`; `pandapower/powerflow.py`; `pandapower/pd2ppc.py`

### Solver Backend Options

pandapower v3.4.0 supports these solver backends via `runpp()` parameters:

| Backend | Activation | Notes |
|---------|-----------|-------|
| NumPy/SciPy (PYPOWER) | Default | Pure Python, Numba-optional |
| Numba JIT | `numba=True` (default if available) | JIT-compiles matrix construction |
| lightsim2grid | `lightsim2grid=True` | C++ backend, ~20x speedup |
| power-grid-model | Via `PandaPowerConverter` | C++ steady-state solver |

These are not a pluggable backend abstraction — each requires specific code paths in the power flow function.

**Source:** `pandapower/run.py` lines 60-95; [pandapower AC power flow docs](https://pandapower.readthedocs.io/en/latest/powerflow/ac.html)

### Serialization and Interoperability

**File I/O formats** (`file_io.py`, `sql_io.py`):
- `to_json()` / `from_json()` — JSON with `PPJSONEncoder`/`PPJSONDecoder`, handles DataFrames, numpy arrays, custom objects. Supports encryption.
- `to_pickle()` / `from_pickle()` — Python pickle (protocol 2)
- `to_excel()` / `from_excel()` — one sheet per element table
- `to_sqlite()` / `from_sqlite()` — SQLite database
- `to_postgresql()` / `from_postgresql()` — PostgreSQL database

**Format converters** (`converter/` package):
- **MATPOWER**: `from_mpc()` / `to_mpc()` — reads `.mat` and `.m` files via `matpowercaseframes` or `scipy.io`
- **PYPOWER**: `from_ppc()` / `to_ppc()` — direct ppc dict conversion
- **CIM** (IEC 61970): `from_cim()` with full CGMES profile support (detailed converter classes per element type)
- **PowerFactory**: `export_pfd_to_pp()` — DIgSILENT PowerFactory export
- **UCTE-DEF**: `from_ucte()` — European transmission network format
- **PowerModels.jl**: `to_pm()` / `from_pm()` — JSON-based bridge to Julia

**Source:** `pandapower/file_io.py`; `pandapower/sql_io.py`; `pandapower/converter/` subpackages

### Multi-Energy Coupling (pandapipes)

pandapipes is a companion package that provides:
- Pipe flow simulation (gas, water, district heating)
- `MultiNet` container holding multiple pandapower/pandapipes networks
- Coupling controllers (e.g., `P2GControlMultiEnergy`) for power-to-gas, gas-to-power, heat pump scenarios
- Same controller framework as pandapower (`BasicCtrl` inheritance)

**Source:** [pandapipes Multi Energy Networks docs](https://pandapipes.readthedocs.io/en/latest/multi_energy_nets.html); [pandapipes GitHub](https://github.com/e2nIEE/pandapipes)

### Additional Analysis Modules

pandapower includes several domain-specific extension modules:
- **State estimation** (`estimation/`): WLS and LAV estimators
- **Short-circuit analysis** (`shortcircuit/`): IEC 60909 calculations
- **Protection** (`protection/`): Fuse and overcurrent relay modeling
- **Grid equivalents** (`grid_equivalents/`): Ward and REI network reduction
- **Contingency analysis** (`contingency/`): N-1/N-k security assessment
- **Diagnostics** (`diagnostic/`): Network validation and error detection

These are all internal modules, not third-party plugins — there is no plugin discovery mechanism.

### DataFrame Interoperability

Since all element data lives in pandas DataFrames, interoperability is seamless:
- Direct access: `net.bus`, `net.line`, `net.res_bus`, etc. are standard `pd.DataFrame` objects
- Standard pandas operations work: filtering, groupby, merge, vectorized math
- Results are immediately available as DataFrames after `runpp()`: `net.res_bus.vm_pu`, `net.res_line.loading_percent`, etc.
- Can export any table to CSV, Parquet, HDF5 via standard pandas methods
- Integration with NumPy/SciPy for custom analysis on result data

**Source:** `pandapower/auxiliary.py` (pandapowerNet class definition)

## Sources

1. `pandapower/auxiliary.py` — pandapowerNet class, ADict base class
2. `pandapower/network_structure.py` — element table schema definitions
3. `pandapower/control/basic_controller.py` — BasicCtrl and Controller classes
4. `pandapower/control/run_control.py` — control loop execution
5. `pandapower/topology/create_graph.py` — NetworkX graph creation
6. `pandapower/topology/graph_searches.py` — graph analysis functions
7. `pandapower/topology/graph_tool_interface.py` — graph-tool backend
8. `pandapower/powerflow.py` — power flow pipeline
9. `pandapower/pd2ppc.py` — DataFrame-to-PYPOWER conversion
10. `pandapower/run.py` — runpp public API, user_pf_options
11. `pandapower/optimal_powerflow.py` — OPF with userfcn callbacks
12. `pandapower/pypower/add_userfcn.py` — callback registration API
13. `pandapower/pypower/run_userfcn.py` — callback execution
14. `pandapower/pypower/opf_model.py` — OPF model (add_constraints, add_vars)
15. `pandapower/runpm.py` — PowerModels.jl integration
16. `pandapower/file_io.py` — JSON/pickle/Excel serialization
17. `pandapower/sql_io.py` — SQLite/PostgreSQL I/O
18. `pandapower/converter/` — MATPOWER, CIM, PYPOWER, PowerFactory, UCTE converters
19. [pandapower documentation](https://pandapower.readthedocs.io/en/latest/)
20. [pandapower GitHub](https://github.com/e2nIEE/pandapower)
21. [Building a Controller tutorial](https://github.com/e2nIEE/pandapower/blob/develop/tutorials/building_a_controller.ipynb)
22. [pandapipes Multi-Energy Networks](https://pandapipes.readthedocs.io/en/latest/multi_energy_nets.html)
23. [lightsim2grid benchmarks](https://lightsim2grid.readthedocs.io/en/latest/benchmarks.html)
24. [pandapower AC power flow docs](https://pandapower.readthedocs.io/en/latest/powerflow/ac.html)

## Gaps and Uncertainties

- **No documented API for adding new element types**: The process of adding a new element type (e.g., a custom FACTS device or novel storage model) that participates in power flow is not documented. It requires modifying multiple internal modules (`pd2ppc.py`, `build_*.py`, `results*.py`, `network_structure.py`). Whether this is intentionally left as "fork the code" or an accidental gap in documentation is unclear.
- **Controller framework vs power flow decoupling**: Controllers operate in an outer loop around power flow, not within it. A controller that needs to modify the admittance matrix or add custom equations to the Newton-Raphson system cannot do so through the controller API — it would need to modify internal PYPOWER structures.
- **graph-tool backend completeness**: The `GraphToolInterface` wraps graph-tool with a NetworkX-like API, but the wrapper appears incomplete (e.g., `add_edge_data` is a TODO stub). Unclear how well-tested this is in practice.
- **lightsim2grid and power-grid-model feature parity**: Not all pandapower features may be supported when using these alternative backends (e.g., 3-phase power flow, FACTS devices, distributed slack). The exact feature matrix needs testing.
- **User function callbacks are PYPOWER-inherited, not pandapower-native**: The `userfcn` system works at the ppc/ppci level, not the pandapower DataFrame level. Users must understand the internal PYPOWER data representation to use it effectively.
- **No event/signal system**: There is no publish/subscribe or event system. Extensions cannot hook into arbitrary points in the power flow pipeline without modifying source code.
- **Multi-energy coupling via pandapipes**: The coupling mechanism relies on the shared controller framework. Whether this extends to other energy carriers beyond gas/heat/water (e.g., hydrogen) needs verification.
- **Custom cost functions in OPF**: While polynomial and piecewise-linear costs are supported natively, adding a fully custom nonlinear objective function requires the PowerModels.jl pathway or modifying PYPOWER internals.

---

# pandapower — Research: Limitations & Ecosystem

## Key Findings

- **OPF solver is internal (PIPS/PYPOWER fork):** pandapower's native OPF uses a bundled interior-point solver from PYPOWER. It cannot natively interface with Ipopt, HiGHS, or other external solvers. External solver access requires the PandaModels.jl Julia bridge (`runpm_ac_opf`), which adds a Julia dependency.
- **No unit commitment / SCUC capability:** pandapower has no built-in unit commitment formulation. Binary on/off decisions for generators, min up/down times, and startup costs are not supported natively. PandaModels.jl does not add UC either.
- **No native stochastic optimization:** No built-in scenario-based or chance-constrained optimization. Stochastic analysis must be implemented manually by looping over scenarios.
- **Time series module is sequential PF, not multi-period OPF:** `run_timeseries()` runs independent power flows per timestep with controller callbacks. It does not formulate or solve inter-temporal optimization (e.g., storage dispatch across hours).
- **MATPOWER converter has known bugs:** Transformer round-trip conversion loses data (#2643), multiple generators on the same bus can fail (#2685), and files with non-standard voltage levels produce zero vn_kv (#2516). The shared `matpower_loader` mitigates some issues.
- **tolerance_mva is likely in per-unit, not MVA:** Confirmed bug (#2750) — the convergence tolerance parameter is documented as MVA but compared against per-unit mismatches internally. Unfixed as of v3.4.0.
- **Active development, frequent releases:** 10 releases in the past 12 months (v3.0.0 through v3.4.0). v3.0.0 was a major release adding VSC/HVDC, CGMES v3.0 support, and DER controllers.
- **Moderate community:** ~1,118 GitHub stars, 556 forks, 135 contributors, 157 open issues (47 labeled bug). ~2.2M total PyPI downloads. Development concentrated at University of Kassel / Fraunhofer IEE.
- **Contingency analysis requires lightsim2grid:** The `run_contingency` and `run_contingency_ls2g` functions live in a module that depends on lightsim2grid for performant execution. lightsim2grid is available (v0.12.2) in the eval environment.
- **BSD 3-Clause license.** All core dependencies (numpy, scipy, pandas, networkx) are permissively licensed.

## Detailed Notes

### OPF Solver Architecture

pandapower's OPF (`runopp` for AC, `rundcopp` for DC) uses a bundled fork of PYPOWER's PIPS (Primal-dual Interior Point Solver). The DC OPF uses `qps_pypower`, also from the PYPOWER fork. These are pure-Python/NumPy/SciPy solvers — no compiled solver binaries.

There is no mechanism to swap in external solvers (Ipopt, HiGHS, GLPK) for the native OPF. The only path to external solvers is `runpm_ac_opf()` / `runpm_dc_opf()`, which calls PowerModels.jl via PandaModels.jl through the `juliacall` Python package. This requires a full Julia installation and the PandaModels.jl package.

**Implications for evaluation:**
- Suite A OPF tests (A-3, A-4) can use the native PIPS solver for small cases
- Scalability of OPF (Suite C) will be limited by the pure-Python PIPS solver
- Custom constraint injection (A-9 flowgates, B-1) via PYPOWER's `add_userfcn` is possible but underdocumented

**Sources:**
- `pandapower/pypower/pipsopf_solver.py` (PIPS solver source)
- `pandapower/pypower/dcopf_solver.py` (DC OPF, uses `qps_pypower`)
- `pandapower/runpm.py` (PandaModels.jl bridge, line 1-40)

### Unit Commitment and Multi-Period Optimization

pandapower has **no unit commitment capability**. There is no binary commitment variable, no min up/down time constraint, no startup cost modeling. The `run_timeseries()` function performs sequential independent power flows (or OPFs if a custom `run` function is passed), but these are decoupled across timesteps — there is no inter-temporal linking.

The `create_storage` element exists for modeling batteries, but it is only used in sequential power flow with controller-based SoC tracking — not in an optimization formulation that dispatches storage optimally across time periods.

**Implications for evaluation:**
- Tests A-5 (SCUC) and A-6 (multi-period with storage) will likely fail or require external tooling
- Test A-12 (full multi-period DCOPF with BESS) cannot be expressed natively

**Sources:**
- `pandapower/timeseries/run_time_series.py` (sequential PF/OPF runner)
- No UC-related attributes found in `dir(pandapower)`

### MATPOWER File Loading and Conversion Bugs

The MATPOWER converter (`from_mpc`, `from_ppc`) has several known open bugs:

| Issue | Description | Status |
|-------|-------------|--------|
| [#2643](https://github.com/e2nIEE/pandapower/issues/2643) | `to_ppc()` sets transformer ratio to 1.0; round-trip via `from_ppc()` loses transformer data | Open |
| [#2685](https://github.com/e2nIEE/pandapower/issues/2685) | Multiple generators on the same bus from MATPOWER .m file parsed incorrectly | Open |
| [#2516](https://github.com/e2nIEE/pandapower/issues/2516) | MATPOWER files with various voltage levels produce zero `vn_kv` | Open |
| [#2614](https://github.com/e2nIEE/pandapower/issues/2614) | `from_ppc()` reduces line count during conversion | Open |
| [#2620](https://github.com/e2nIEE/pandapower/issues/2620) | `to_mpc()` converts transformers to impedances; `from_mpc()` cannot reverse | Open |
| [#2392](https://github.com/e2nIEE/pandapower/issues/2392) | Zero-resistance lines interpreted as transformers in IEEE14 | Open |

The shared `matpower_loader` in the evaluation repo (`evaluations/shared/matpower_loader.py`) uses `matpowercaseframes` to parse MATPOWER files and `from_ppc` to convert to pandapower format. This path is classified as LOSSLESS in the evaluation protocol.

**Sources:**
- GitHub issues linked above
- `evaluations/shared/LOADING_NOTES.md`

### Convergence and Numerical Issues

| Issue | Description |
|-------|-------------|
| [#2750](https://github.com/e2nIEE/pandapower/issues/2750) | `tolerance_mva` is compared in per-unit despite being documented as MVA. Confirmed by maintainer, unfixed. |
| [#2557](https://github.com/e2nIEE/pandapower/issues/2557) | Behavior mismatch between pp2 and pp3 on IEEE cases — transformer impedance splitting changed |
| [#114](https://github.com/e2nIEE/pandapower/issues/114) | Algorithms for ill-conditioned problems — open since 2017 |
| [#2609](https://github.com/e2nIEE/pandapower/issues/2609) | Simbench network AC OPF not converging with native or PandaModels solver |
| [#1101](https://github.com/e2nIEE/pandapower/issues/1101) | OPF non-convergence regression in versions > 2.2.0 |
| [#2692](https://github.com/e2nIEE/pandapower/issues/2692) | Ideal 3-winding transformers with tap at HV side malfunction |

### Short Circuit Analysis

pandapower implements IEC 60909 short circuit calculations via `pandapower.shortcircuit.calc_sc()`. Known open issues:

| Issue | Description |
|-------|-------------|
| [#2646](https://github.com/e2nIEE/pandapower/issues/2646) | NaN bus voltages during single-phase short circuit |
| [#2621](https://github.com/e2nIEE/pandapower/issues/2621) | Thermal current values don't vary with topology |
| [#2292](https://github.com/e2nIEE/pandapower/issues/2292) | Possibly incorrect Ik'' results |
| [#2484](https://github.com/e2nIEE/pandapower/issues/2484) | Missing kappa value for Type 4 wind generators |

### State Estimation

pandapower includes WLS, IRWLS, LP, and AF-WLS state estimation algorithms. Known issues:

| Issue | Description |
|-------|-------------|
| [#2700](https://github.com/e2nIEE/pandapower/issues/2700) | `zero-injection="no_inj_bus"` produces IndexError |
| [#1451](https://github.com/e2nIEE/pandapower/issues/1451) | `remove_bad_data` fails with linear algebra errors |

### Contingency Analysis

pandapower has a contingency analysis module (`pandapower.contingency`) with two implementations:
- `run_contingency()` — pure-Python sequential N-1
- `run_contingency_ls2g()` — accelerated via lightsim2grid (C++ backend)

Open issues:
- [#2715](https://github.com/e2nIEE/pandapower/issues/2715): Parallel contingency analysis not yet implemented
- [#2910](https://github.com/e2nIEE/pandapower/issues/2910): lightsim2grid issue with case14 (future compatibility)
- [#2438](https://github.com/e2nIEE/pandapower/issues/2438): `run_contingency_ls2g` fails with redundant buses
- [#2684](https://github.com/e2nIEE/pandapower/issues/2684): Ambiguity in `max_loading_percent` requirement

### DC Line / HVDC Modeling

v3.0.0 added VSC elements, DC buses, DC lines, and hybrid AC/DC power flow. Known issues:
- [#2716](https://github.com/e2nIEE/pandapower/issues/2716): Bidirectional DC lines bug
- [#2712](https://github.com/e2nIEE/pandapower/issues/2712): Distributed slack not supported for DC power flow
- [#2235](https://github.com/e2nIEE/pandapower/issues/2235): DC lines not correctly displayed in `res_bus.p_mw`

### Ecosystem Packages

| Package | Stars | Description | Relationship |
|---------|-------|-------------|--------------|
| [pandapipes](https://github.com/e2nIEE/pandapipes) | 210 | Pipeflow calculation (gas, heat, water) | Official companion (same team) |
| [simbench](https://github.com/e2nIEE/simbench) | 128 | Benchmark distribution grids | Official companion |
| [PandaModels.jl](https://github.com/e2nIEE/PandaModels.jl) | 13 | Julia bridge to PowerModels.jl | Official companion |
| [pandahub](https://github.com/e2nIEE/pandahub) | 15 | MongoDB data hub for networks | Official companion |
| [pandapower-qgis](https://github.com/e2nIEE/pandapower-qgis) | 2 | QGIS plugin | Official companion |
| [lightsim2grid](https://github.com/BDonnot/lightsim2grid) | ~100 | C++ power flow backend (RTE) | Third-party, officially supported |

**lightsim2grid** is particularly notable: it provides a compiled C++ Newton-Raphson solver that pandapower can use as a drop-in replacement for its pure-Python solver (`pp.runpp(net, algorithm='gs')` → lightsim2grid). It offers 10-100x speedup on power flow and is critical for performant contingency analysis.

### Performance / Scalability

The optional `performance` extras add:
- **lightsim2grid** (~0.12.2): C++ power flow backend, 10-100x faster than native Newton-Raphson
- **numba** (~0.61): JIT compilation for select numerical routines
- **ortools** (~9.14): Google OR-Tools (unclear integration point)

Scalability concerns:
- Native Newton-Raphson (pure Python/NumPy) is slow for large networks (>5k buses)
- Native OPF (PIPS) is a pure-Python interior point solver — likely impractical for 10k+ bus OPF
- [#851](https://github.com/e2nIEE/pandapower/issues/851): Feature request for GraphBLAS-accelerated graph algorithms (open since 2019)
- [#1635](https://github.com/e2nIEE/pandapower/issues/1635): Temperature-dependent power flow performance issues
- No parallel processing support for contingency analysis ([#2715](https://github.com/e2nIEE/pandapower/issues/2715))

### Release History

| Version | Date | Highlights |
|---------|------|------------|
| v3.4.0 | 2026-02-09 | DC elements in DC powerflow, Python 3.14 support, lightsim2grid 0.12.2 |
| v3.3.2 | 2026-01-15 | Bug fixes |
| v3.3.0 | 2025-12-16 | (details not retrieved) |
| v3.2.1 | 2025-10-27 | Bug fixes |
| v3.2.0 | 2025-10-08 | (details not retrieved) |
| v3.1.2 | 2025-06-16 | Bug fixes |
| v3.1.1 | 2025-05-26 | Bug fixes |
| v3.0.0 | 2025-03-06 | **Major:** VSC/HVDC, CGMES v3.0, DER controllers, station controllers, pandera schemas, JAO/UCTE converters |
| v2.14.11 | 2024-08-07 | Last v2 release |

Release cadence: approximately monthly during active development periods. Major version bumps (2→3) introduce breaking API changes (controller parameter renames, geodata format changes).

### Documentation Quality

- **Platform:** ReadTheDocs (Sphinx-based), covers v3.4.0
- **Coverage:** Comprehensive across core features (power flow, OPF, short circuit, state estimation, controllers, time series, plotting, converters)
- **Gaps identified:**
  - Protection module coverage is minimal (only overcurrent relay and fuse)
  - No dedicated troubleshooting/debugging guide
  - Limited scalability/performance guidance
  - Transformer documentation has known equation errors ([#2847](https://github.com/e2nIEE/pandapower/issues/2847))
  - Some tutorials have deprecation warnings ([#2734](https://github.com/e2nIEE/pandapower/issues/2734))
  - Missing plots in asymmetric tutorial ([#2733](https://github.com/e2nIEE/pandapower/issues/2733))
- **Tutorials:** Jupyter notebooks in the repo, tested via CI (nbmake)
- **API reference:** Auto-generated from docstrings (numpydoc style)

### Academic Citation

Primary paper: L. Thurner, A. Scheidler, F. Schäfer et al., "pandapower — An Open-Source Python Tool for Convenient Modeling, Analysis, and Optimization of Electric Power Systems," *IEEE Transactions on Power Systems*, vol. 33, no. 6, pp. 6510-6521, 2018. DOI: [10.1109/TPWRS.2018.2829021](https://doi.org/10.1109/TPWRS.2018.2829021)

### License and Dependencies

- **pandapower license:** BSD 3-Clause
- **Copyright:** University of Kassel and Fraunhofer IEE (2016-2026)
- **Core dependencies (all permissive):** pandas (~2.3), networkx (~3.4), scipy (<1.17), numpy (>=1.26), packaging, tqdm, deepdiff, geojson, typing_extensions, pandera (~0.26.1)
- **Performance extras:** lightsim2grid (MPL-2.0), numba (BSD-2), ortools (Apache-2.0)
- **Converter extras:** matpowercaseframes (MIT), lxml (BSD-3)
- **PandaModels bridge:** juliacall (MIT) → requires Julia runtime + PowerModels.jl (BSD-3)

No GPL or copyleft dependencies in the core or performance extras.

### Operational Deployment Evidence

No direct evidence of utility, ISO, or government operational deployments was found on the website, documentation, or GitHub. The project is developed by University of Kassel and Fraunhofer IEE (a German applied research institute). Fraunhofer IEE works with European TSOs/DSOs, which suggests indirect industrial use, but no specific deployments are publicly documented.

The simbench companion project provides standardized benchmark networks modeled after German distribution grid characteristics, suggesting primary use in European grid planning contexts.

## Sources

1. GitHub repository: https://github.com/e2nIEE/pandapower (1,118 stars, 556 forks, 135 contributors)
2. PyPI: https://pypi.org/project/pandapower/ (v3.4.0, 2026-02-09)
3. Documentation: https://pandapower.readthedocs.io/en/latest/
4. Download stats: https://pepy.tech/projects/pandapower (~2.2M total downloads)
5. Primary paper: IEEE TPWRS 2018, DOI 10.1109/TPWRS.2018.2829021
6. Official website: https://www.pandapower.org
7. PandaModels.jl: https://github.com/e2nIEE/PandaModels.jl
8. lightsim2grid: https://github.com/BDonnot/lightsim2grid
9. simbench: https://github.com/e2nIEE/simbench
10. Installed source code: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/`

## Gaps and Uncertainties

- **OPF scalability:** Not yet tested — unclear how PIPS performs on 2k and 10k bus networks. May need PandaModels.jl bridge for larger cases.
- **Custom constraint injection:** PYPOWER's `add_userfcn` exists but is underdocumented in pandapower context. Unclear if flowgate constraints (test B-1) can be expressed without PandaModels.jl.
- **lightsim2grid PF accuracy:** lightsim2grid is a separate C++ implementation — need to verify results match native pandapower on test networks.
- **MATPOWER loading fidelity:** Known bugs in converter may affect ACTIVSg 2k/10k loading. The shared `matpower_loader` may mitigate, but needs testing.
- **Pandas 3.0 compatibility:** Listed as a future goal (#2861) for pandapower v4.0. Current v3.4.0 pins pandas ~2.3.
- **Three-phase / unbalanced power flow:** pandapower has `runpp_3ph` but its maturity is unclear — asymmetric tutorial has missing plots (#2733).
- **PandaModels.jl integration reliability:** Issue #1740 reports discrepancies between OPF solutions via PandaModels vs direct PowerModels.jl usage.
- **No evidence of US utility/ISO deployment.** All known development is European (German). Unclear if pandapower handles US-specific conventions (US ISO market data, reliability standards) out of the box.

---

<!-- tool: pandapower, installed_version: 3.4.0, release_date: 2026-02-09 -->

# pandapower — Version & Capability Report

## Version Summary

The installed version of pandapower is **3.4.0**, released on 2026-02-09. This is the latest available version on PyPI, so no version gap exists. The installation includes the `[performance]` extra (numba 0.64.0, lightsim2grid 0.12.2), along with `matpowercaseframes` and `pyomo` as additional project dependencies.

pandapower 3.4.0 sits atop a major version 3 lineage that began with 3.0.0 on 2025-03-06. The 3.x series introduced hybrid AC/DC power flow, VSC elements, DC buses and lines, CGMES v3.0 support, and migrated from setup.py to pyproject.toml. It also dropped Python 3.8 support and removed legacy geodata tables in favor of GeoJSON-based `geo` columns.

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes | 1.x | `pp.rundcpp()` — linearized DC power flow |
| AC Power Flow (ACPF) | yes | 1.x | `pp.runpp()` — Newton-Raphson, with lightsim2grid and power-grid-model backends; also supports 3-phase unbalanced via `runpp_3ph()` |
| DC Optimal Power Flow (DC OPF) | yes | 1.x | `pp.rundcopp()` — uses PYPOWER backend |
| AC Optimal Power Flow (AC OPF) | yes | 1.x | `pp.runopp()` — uses PYPOWER backend; PandaModels.jl available as optional Julia-based solver |
| Security-Constrained Unit Commitment (SCUC) | no | — | No unit commitment formulation. pandapower is a steady-state network analysis tool, not a market/scheduling tool. |
| Security-Constrained Economic Dispatch (SCED) | no | — | No security-constrained economic dispatch. OPF does not model N-1 security constraints in the optimization. |
| PTDF / Shift Factor Extraction | yes | 1.x | `pandapower.pypower.makePTDF.makePTDF()` — computes Power Transfer Distribution Factors from the DC model |
| Contingency Analysis (N-1) | yes | 2.x | `pandapower.contingency.run_contingency()` for standard N-1; `run_contingency_ls2g()` for accelerated analysis via lightsim2grid |
| Custom Constraint Injection | partial | 1.x | OPF supports predefined constraint types (bus voltage limits, branch loading limits, generator P/Q limits) but does NOT support arbitrary user-defined constraints in the PYPOWER OPF. Users would need to build a custom Pyomo model or use PandaModels.jl for fully custom constraints. |
| Network Graph Access | yes | 1.x | `pandapower.topology.create_nxgraph()` — full NetworkX graph representation with specialized power-system search algorithms |
| CSV Data Import | no | — | No native CSV import. File I/O supports JSON, Excel, pickle, and SQL. Users must manually construct DataFrames from CSV and populate the pandapower network. |
| MATPOWER Case Import | yes | 1.x | `pandapower.converter.matpower.from_mpc.from_mpc()` reads .m files; `pandapower.converter.pypower.from_ppc.from_ppc()` converts PYPOWER case dicts; `matpowercaseframes` package also available |
| Multi-Period / Time Series | yes | 2.x | `pandapower.timeseries.run_timeseries()` — controller-based loop over time steps with DataSource and OutputWriter infrastructure |
| Warm Start / Solution Reuse | yes | 1.x | `init="results"` parameter in `runpp()` and `runopp()` reuses the previous solution as starting point |
| Parallel Computation | partial | 2.x | No built-in parallel power flow dispatcher. Acceleration via numba JIT compilation (makeYbus, etc.) and lightsim2grid C++ backend. Users can parallelize time-series runs externally (e.g., multiprocessing). |

### Canonical Feature-Suite Mapping

| Feature | Suites |
|---------|--------|
| DC Power Flow (DCPF) | A, G |
| AC Power Flow (ACPF) | A, G |
| DC Optimal Power Flow (DC OPF) | A |
| AC Optimal Power Flow (AC OPF) | A |
| Security-Constrained Unit Commitment (SCUC) | A |
| Security-Constrained Economic Dispatch (SCED) | A |
| PTDF / Shift Factor Extraction | B |
| Contingency Analysis (N-1) | B |
| Custom Constraint Injection | C |
| Network Graph Access | C |
| CSV Data Import | G |
| MATPOWER Case Import | A, G |
| Multi-Period / Time Series | B |
| Warm Start / Solution Reuse | D |
| Parallel Computation | D |

### Support Semantics

- **yes** — Feature is fully supported in the installed version.
- **no** — Feature is not available.
- **partial** — Feature exists but with significant limitations. When `partial` is used, the Notes column MUST explain what is limited.
- **Since Version** — The version that introduced the feature. Set to `unknown` if the changelog does not provide this information.

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|----------------------|
| 3.4.0 | Station Controller `voltage_ctrl` renamed to `control_modus` (bool to enum) | No impact on evaluation suites (controller internals). |
| 3.3.0 | Removed deprecated functions: `get_connected_lines`, `get_connected_switches`, `connected_bus_in_line`, `get_line_path` | Topology operations must use current API names. Suite C graph tests unaffected if using `create_nxgraph`. |
| 3.3.0 | Removed general imports; reorganized `create.py` into modular files | Import paths changed but backwards-compatible. No evaluation impact. |
| 3.3.0 | Renamed `q_capability_curve_characteristic` to `q_capability_characteristic` | No direct evaluation impact (reactive capability curve feature). |
| 3.0.0 | Removed Python 3.8 support | No impact; evaluation uses Python 3.12. |
| 3.0.0 | Removed `vk_percent_characteristic`, `vkr_percent_characteristic` from trafo; removed `tap_phase_shifter` from `net.trafo` | Transformer modeling changes. Could affect Suite A/G if tests used old characteristic parameters. |
| 3.0.0 | TrafoController parameter rename: `trafotable`/`trafotype` to `element`; `tid` to `element_index` | Controller API change. No evaluation impact unless controller tests use old names. |
| 3.0.0 | Removed `bus_geodata` and `line_geodata` tables; replaced with `geo` column (GeoJSON) | Plotting/geodata changes. No power flow or OPF impact. |
| 3.0.0 | Changed `from "inductive"/"ind"` to `"underexcited"` and `"capacitive"/"cap"` to `"overexcited"` | Reactive power terminology change. Could affect OPF constraint setup. |

## Changelog Analysis

### 3.0.0 (2025-03-06) — Major Release

The 3.0 release was the most significant in the evaluation-relevant period. Key themes:

- **Hybrid AC/DC Power Flow**: Added VSC elements, DC buses, DC lines, and a unified AC/DC power flow solver. This extends expressiveness for modern grid topologies.
- **New Controllers**: DERController, discrete shunt controller, station controller with voltage and reactive power control, DISCrete tap control with hunting detection.
- **Converter Expansion**: CGMES v3.0 reading, JAO European EHV grid converter, PowerFactory converter enhancements.
- **State Estimation**: AF-WLS estimator for non-observable grids, shunt estimation results.
- **Infrastructure**: Migration to pyproject.toml, removed setup.py.

### 3.1.x (2025-05-26 to 2025-06-16) — State Estimation Focus

- State estimation RAM and speed optimizations with sparse matrices.
- Iteration count output for convergence monitoring.
- Reactive capability curve support for generators and static generators.
- Multiple zero injection measurement creation options.

### 3.2.x (2025-10-08 to 2025-10-27) — DC Elements and Controllers

- Back2Back VSC converter with tests.
- Load_dc and Source_dc for DC loads and generators.
- DMR controller for metallic return line current.
- Station Controller with droop control.
- Python 3.13 support.
- Plotly switched from mapbox to maplibre.

### 3.3.x (2025-12-15 to 2026-01-14) — Modularization

- Julia implementation now using juliacall (relevant for PandaModels.jl integration).
- Static Var Compensator with Voltage Control.
- Separate per-phase MVA attributes for three-phase modeling.
- Removed deprecated topology functions.
- scipy version pinned to <1.16 for Python 3.10 compatibility.

### 3.4.0 (2026-02-09) — Current Release

- `enforce_p_lims` optional argument for considering generator/sgen active power limits in power flow.
- DC elements added to DC power flow.
- Python 3.14 support in test pipeline.
- Removed extra dependencies from "all" set; added "dev" set.

### Themes Relevant to Evaluation Suites

- **Suite A (Power Flow / OPF)**: Core ACPF and DCPF stable throughout. OPF via PYPOWER unchanged. No SCUC/SCED introduced.
- **Suite B (PTDF / Contingency / Time Series)**: PTDF via makePTDF unchanged. Contingency analysis stable with lightsim2grid acceleration. Time series stable.
- **Suite C (Custom Constraints / Graph)**: NetworkX graph access stable. Custom constraint injection remains limited to predefined OPF constraint types.
- **Suite D (Warm Start / Parallel)**: `init="results"` warm start unchanged. No new parallel computation features. numba and lightsim2grid provide single-run acceleration.
- **Suite G (Data Import)**: MATPOWER converter stable. No CSV import added. CGMES v3.0 and JAO converters added in 3.0.

## Sources

1. PyPI pandapower page: <https://pypi.org/project/pandapower/>
2. GitHub CHANGELOG.rst: <https://github.com/e2nIEE/pandapower/blob/develop/CHANGELOG.rst>
3. pandapower documentation — Power Flow: <https://pandapower.readthedocs.io/en/latest/powerflow.html>
4. pandapower documentation — OPF: <https://pandapower.readthedocs.io/en/latest/opf.html>
5. pandapower documentation — OPF Formulation: <https://pandapower.readthedocs.io/en/latest/opf/formulation.html>
6. pandapower documentation — Contingency: <https://pandapower.readthedocs.io/en/latest/contingency.html>
7. pandapower documentation — Time Series: <https://pandapower.readthedocs.io/en/latest/timeseries.html>
8. pandapower documentation — Topology: <https://pandapower.readthedocs.io/en/latest/topology.html>
9. pandapower documentation — File I/O: <https://pandapower.readthedocs.io/en/latest/file_io.html>
10. pandapower documentation — Converters: <https://pandapower.readthedocs.io/en/latest/converter.html>
11. Runtime introspection of installed pandapower 3.4.0 in devcontainer

## Gaps and Uncertainties

- **"Since Version" precision**: Most features predate the 3.x changelog window. Features marked as "1.x" or "2.x" are based on their presence in early documentation and the fact that they were not listed as new in the 3.x changelog. Exact introduction versions would require reviewing the full pre-3.0 changelog.
- **PandaModels.jl custom constraints**: pandapower can delegate OPF to PandaModels.jl (Julia), which supports custom constraints via JuMP. However, `pandamodels` is not installed in the current environment, so this path is untested. The 3.3.0 changelog notes migration to `juliacall` for Julia integration.
- **Parallel computation**: pandapower does not document a built-in parallel dispatcher for running multiple independent power flows concurrently. The `run_timeseries` function is sequential. External parallelism (e.g., Python multiprocessing) is possible but not provided by pandapower itself.
- **CSV import**: While pandapower has no dedicated CSV reader, pandas DataFrames are the internal data structure, so CSV-to-DataFrame-to-pandapower is straightforward. Whether this counts as "supported" depends on evaluation rubric interpretation.
- **SCED/SCUC**: These are fundamentally market/scheduling formulations. pandapower's OPF minimizes generation cost subject to network constraints but does not model unit commitment (binary on/off decisions), startup/shutdown costs, ramp rates, or N-1 security within the optimization. This is a design scope limitation, not a missing feature.
- **3.3.3 and 3.2.2 patch releases**: PyPI shows release dates of 2026-03-13 for both 3.3.3 and 3.2.2, which postdate the 3.4.0 release (2026-02-09). These appear to be backport patches to older release branches. Their changelogs were not individually fetched but are likely bug-fix-only releases.

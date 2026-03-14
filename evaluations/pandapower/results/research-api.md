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

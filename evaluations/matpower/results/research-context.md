# MATPOWER API Research

**Tool:** MATPOWER 8.1 (12-Jul-2025)
**Platform:** MATLAB / GNU Octave
**License:** 3-clause BSD
**Repository:** https://github.com/MATPOWER/matpower

## Key Findings

1. **Two parallel API frameworks.** MATPOWER 8.1 ships a "legacy" framework (`runpf`, `runopf`, etc.) and a new "flexible" framework (`run_pf`, `run_opf`, etc. built on MP-Core). The legacy API is fully documented in the PDF manual; the new API returns task objects with a data-model element tree. Both coexist and share the same `mpoption` configuration.

2. **Data model is a flat numeric matrix struct.** The central data structure is the `mpc` (MATPOWER case) struct with fields `baseMVA`, `bus`, `gen`, `branch`, and optionally `gencost`, `dcline`, `bus_name`, `gentype`, `genfuel`. Buses, generators, branches, and costs are dense numeric matrices indexed by named constants (`idx_bus`, `idx_gen`, `idx_brch`, `idx_cost`). There are no object-oriented abstractions in the legacy API; the new framework wraps this in `mp.dm_element` table objects.

3. **Supported problem formulations cover PF, CPF, OPF, and multi-period scheduling.** Core: AC power flow (Newton, Fast-Decoupled, Gauss-Seidel, radial methods), DC power flow, continuation power flow, AC OPF, DC OPF. Extensions: MOST adds multi-period stochastic SCUC/SCED with unit commitment, storage, wind, and contingency constraints.

4. **Broad solver interface via `mpoption`.** AC OPF solvers: MIPS (built-in), IPOPT, KNITRO, FMINCON, MINOPF, PDIPM, SDPOPF, TRALM. DC OPF solvers: MIPS, GUROBI, CPLEX, MOSEK, GLPK, IPOPT, OSQP, CLP, HiGHS, BPMPD, OT (MATLAB Optimization Toolbox). Solver selection is a single `mpoption` string.

5. **Input/output format is the `.m` case file,** the de facto standard for power system test cases. Also supports `.mat` (MATLAB binary), PSS/E RAW import (`psse2mpc`), IEEE CDF import (`cdf2mpc`), and PSS/E RAW export (`save2psse`).

## Detailed Notes

### Data Model: The `mpc` Struct

The MATPOWER case struct (`mpc`) is the universal data container. All functions accept either an `mpc` struct or a filename string (resolved by `loadcase`).

**Required fields:**

| Field | Shape | Description |
|-------|-------|-------------|
| `baseMVA` | scalar | System MVA base |
| `bus` | nb x 13 (input) / nb x 17 (after OPF) | Bus data |
| `gen` | ng x 21 (input) / ng x 25 (after OPF) | Generator data |
| `branch` | nl x 13 (input) / nl x 21 (after OPF) | Branch data |

**Optional fields:**

| Field | Shape | Description |
|-------|-------|-------------|
| `gencost` | ng x (5+) | Generator cost curves (piecewise linear or polynomial) |
| `dcline` | ndc x 17 | HVDC line data (enabled via `toggle_dcline`) |
| `bus_name` | nb x 1 cell | Bus name strings |
| `gentype` | ng x 1 cell | Generator type codes |
| `genfuel` | ng x 1 cell | Generator fuel type codes |
| `A`, `l`, `u` | user constraints | Linear constraints for OPF extensions |
| `N`, `H`, `Cw`, `fparm` | user costs | User-defined cost terms for OPF |

Source: `lib/caseformat.m`, `lib/idx_bus.m`, `lib/idx_gen.m`, `lib/idx_brch.m`, `lib/idx_cost.m`, `lib/idx_dcline.m`

#### Bus Matrix Columns (idx_bus)

| Col | Constant | Description | Units |
|-----|----------|-------------|-------|
| 1 | `BUS_I` | Bus number | integer |
| 2 | `BUS_TYPE` | 1=PQ, 2=PV, 3=ref, 4=isolated | enum |
| 3 | `PD` | Real power demand | MW |
| 4 | `QD` | Reactive power demand | MVAr |
| 5 | `GS` | Shunt conductance | MW @ 1 p.u. |
| 6 | `BS` | Shunt susceptance | MVAr @ 1 p.u. |
| 7 | `BUS_AREA` | Area number | integer |
| 8 | `VM` | Voltage magnitude | p.u. |
| 9 | `VA` | Voltage angle | degrees |
| 10 | `BASE_KV` | Base voltage | kV |
| 11 | `ZONE` | Loss zone | integer |
| 12 | `VMAX` | Max voltage magnitude | p.u. |
| 13 | `VMIN` | Min voltage magnitude | p.u. |
| 14-17 | `LAM_P`, `LAM_Q`, `MU_VMAX`, `MU_VMIN` | OPF dual variables | $/MW, $/MVAr, $/p.u. |

#### Generator Matrix Columns (idx_gen)

| Col | Constant | Description | Units |
|-----|----------|-------------|-------|
| 1 | `GEN_BUS` | Bus number | integer |
| 2 | `PG` | Real power output | MW |
| 3 | `QG` | Reactive power output | MVAr |
| 4-5 | `QMAX`, `QMIN` | Reactive power limits | MVAr |
| 6 | `VG` | Voltage setpoint | p.u. |
| 7 | `MBASE` | Machine MVA base | MVA |
| 8 | `GEN_STATUS` | 1=in-service, 0=out-of-service | boolean |
| 9-10 | `PMAX`, `PMIN` | Active power limits | MW |
| 11-16 | `PC1`, `PC2`, `QC1MIN`..`QC2MAX` | PQ capability curve | MW/MVAr |
| 17-20 | `RAMP_AGC`, `RAMP_10`, `RAMP_30`, `RAMP_Q` | Ramp rates | MW/min |
| 21 | `APF` | Area participation factor | - |
| 22-25 | `MU_PMAX`..`MU_QMIN` | OPF dual variables | $/MW, $/MVAr |

#### Branch Matrix Columns (idx_brch)

| Col | Constant | Description | Units |
|-----|----------|-------------|-------|
| 1-2 | `F_BUS`, `T_BUS` | From/to bus | integer |
| 3-5 | `BR_R`, `BR_X`, `BR_B` | Resistance, reactance, charging susceptance | p.u. |
| 6-8 | `RATE_A`, `RATE_B`, `RATE_C` | Long-term, short-term, emergency ratings | MVA |
| 9-10 | `TAP`, `SHIFT` | Transformer turns ratio, phase shift | ratio, degrees |
| 11 | `BR_STATUS` | 1=in-service, 0=out-of-service | boolean |
| 12-13 | `ANGMIN`, `ANGMAX` | Voltage angle difference limits | degrees |
| 14-17 | `PF`, `QF`, `PT`, `QT` | Solved branch flows | MW/MVAr |
| 18-21 | `MU_SF`, `MU_ST`, `MU_ANGMIN`, `MU_ANGMAX` | OPF dual variables | $/MVA, $/degree |

#### Generator Cost Matrix (idx_cost)

| Col | Constant | Description |
|-----|----------|-------------|
| 1 | `MODEL` | 1=piecewise linear, 2=polynomial |
| 2 | `STARTUP` | Startup cost ($) |
| 3 | `SHUTDOWN` | Shutdown cost ($) |
| 4 | `NCOST` | Number of cost data points/coefficients |
| 5+ | `COST` | Cost parameters (breakpoints for PWL, coefficients for polynomial) |

### API Surface: Core Functions

#### Power Flow

| Function | Description |
|----------|-------------|
| `runpf(mpc, mpopt)` | AC power flow (Newton's method by default) |
| `rundcpf(mpc, mpopt)` | DC power flow |
| `runcpf(base, target, mpopt)` | Continuation power flow (voltage stability) |

**AC PF algorithms** (set via `mpoption('pf.alg', ...)`):
- `'NR'` / `'NR-SP'` -- Newton-Raphson, power mismatch, polar (default)
- `'NR-SC'` -- Newton, power mismatch, cartesian
- `'NR-SH'` -- Newton, power mismatch, hybrid
- `'NR-IP'` -- Newton, current mismatch, polar
- `'NR-IC'` -- Newton, current mismatch, cartesian
- `'NR-IH'` -- Newton, current mismatch, hybrid
- `'FDXB'` -- Fast-Decoupled (XB version)
- `'FDBX'` -- Fast-Decoupled (BX version)
- `'GS'` -- Gauss-Seidel
- `'ZG'` -- Implicit Z-bus Gauss
- `'PQSUM'` -- Power Summation (radial only)
- `'ISUM'` -- Current Summation (radial only)
- `'YSUM'` -- Admittance Summation (radial only)

#### Optimal Power Flow

| Function | Description |
|----------|-------------|
| `runopf(mpc, mpopt)` | AC OPF |
| `rundcopf(mpc, mpopt)` | DC OPF |
| `runuopf(mpc, mpopt)` | AC OPF with unit decommitment |
| `runduopf(mpc, mpopt)` | DC OPF with unit decommitment |
| `runopf_w_res(mpc, mpopt)` | AC OPF with fixed reserve requirements |

**AC OPF solvers** (`mpoption('opf.ac.solver', ...)`):
`'MIPS'` (default, pure MATLAB/Octave), `'IPOPT'`, `'KNITRO'`, `'FMINCON'`, `'MINOPF'`, `'PDIPM'`, `'SDPOPF'`, `'TRALM'`

**DC OPF solvers** (`mpoption('opf.dc.solver', ...)`):
`'DEFAULT'` (auto-selects best available), `'MIPS'`, `'GUROBI'`, `'CPLEX'`, `'MOSEK'`, `'GLPK'`, `'IPOPT'`, `'OSQP'`, `'CLP'`, `'HiGHS'`, `'BPMPD'`, `'OT'` (MATLAB Optimization Toolbox)

**OPF flow limit formulations** (`mpoption('opf.flow_lim', ...)`):
`'S'` (apparent power, MVA), `'P'` (active power, MW), `'2'` (active power squared), `'I'` (current magnitude)

#### Multi-Period / SCUC / SCED (MOST)

| Function | Description |
|----------|-------------|
| `most(mdi, mpopt)` | Multi-period stochastic contingency-constrained OPF with UC |
| `loadmd(...)` | Load MOST data structure |
| `most_summary(mdo)` | Summarize MOST results |
| `addstorage(mpc, ...)` | Add energy storage to case |
| `addwind(mpc, ...)` | Add wind generation profiles |

MOST supports: multi-period scheduling, stochastic scenarios, contingency constraints, unit commitment (binary variables via MILP/MIQP), energy storage with cyclic/terminal constraints, ramp rate constraints, and fixed zonal reserve requirements. It uses DC flow constraints by default.

Source: `most/lib/most.m`

#### Network Analysis Utilities

| Function | Description |
|----------|-------------|
| `makeYbus(mpc)` | Build bus admittance matrix (Ybus) and branch matrices (Yf, Yt) |
| `makePTDF(mpc, slack)` | Build DC PTDF matrix (power transfer distribution factors) |
| `makeLODF(mpc, PTDF)` | Build line outage distribution factor matrix |
| `makeBdc(mpc)` | Build DC B matrices |
| `makeJac(mpc)` | Build AC Jacobian matrix |
| `makeSbus(mpc)` | Build complex bus power injection vector |
| `get_losses(results)` | Compute branch series losses and line charging |
| `total_load(mpc)` | Compute total load by zone |
| `scale_load(factor, mpc)` | Scale loads by zone |
| `find_islands(mpc)` | Find connected components |
| `find_bridges(mpc)` | Find bridge branches |
| `case_info(mpc)` | Print network island information |

#### Data Conversion

| Function | Description |
|----------|-------------|
| `loadcase(file)` | Load `.m` or `.mat` case file to `mpc` struct |
| `savecase(file, mpc)` | Save `mpc` struct to `.m` or `.mat` file |
| `ext2int(mpc)` | Convert external to internal bus numbering (remove out-of-service) |
| `int2ext(results)` | Convert internal back to external numbering |
| `psse2mpc(rawfile)` | Import PSS/E RAW file to `mpc` struct |
| `cdf2mpc(cdffile)` | Import IEEE CDF file to `mpc` struct |
| `save2psse(file, mpc)` | Export `mpc` struct to PSS/E RAW format (Rev 33) |

### OPF Extension Mechanisms

MATPOWER provides a callback-based extension system via `add_userfcn`. Five callback stages exist: `ext2int`, `formulation`, `int2ext`, `printpf`, `savecase`. Built-in extensions using this mechanism:

| Extension | Toggle Function | Adds |
|-----------|----------------|------|
| DC lines (HVDC) | `toggle_dcline(mpc, 'on')` | `mpc.dcline` field, modeled as linked generator pairs |
| Fixed reserves | `toggle_reserves(mpc, 'on')` | `mpc.reserves` field: zonal reserve requirements |
| Interface flow limits | `toggle_iflims(mpc, 'on')` | `mpc.if` field: aggregate flow limits across branch groups |
| Soft limits | `toggle_softlims(mpc, 'on')` | `mpc.softlims` field: relaxed inequality constraints with penalty costs |

The OPF also accepts direct user constraints (`A`, `l`, `u`) and user costs (`N`, `H`, `Cw`, `fparm`) as fields in the `mpc` struct or as arguments to `opf()`.

Source: `lib/add_userfcn.m`, `lib/toggle_dcline.m`, `lib/toggle_reserves.m`, `lib/toggle_iflims.m`, `lib/toggle_softlims.m`

### New Flexible Framework (MATPOWER 8.x)

MATPOWER 8.x introduces a new object-oriented framework alongside the legacy API:

| Function | Legacy Equivalent |
|----------|------------------|
| `run_pf(mpc)` | `runpf(mpc)` |
| `run_cpf(base, target)` | `runcpf(base, target)` |
| `run_opf(mpc)` | `runopf(mpc)` |
| `run_mp(task_class, mpc)` | Generic runner |

The new framework returns a `task` object with structured results:
```matlab
task = run_pf('case9');
va = task.dm.elements.bus.tab.va;    % bus voltage angles
pg = task.dm.elements.gen.tab.pg;    % generator active dispatch
```

This replaces the matrix-column-index pattern with named-field access on table objects. The legacy API continues to work and internally delegates to MP-Core by default.

Source: `lib/run_pf.m`, `lib/run_opf.m`

### Solver Configuration via `mpoption`

All solver and algorithm selection is done through the `mpoption` function, which returns and modifies an options struct. Key option namespaces:

- `model` -- `'AC'` or `'DC'`
- `pf.alg` -- Power flow algorithm selection
- `pf.tol`, `pf.nr.max_it` -- Convergence parameters
- `pf.enforce_q_lims` -- Reactive power limit enforcement
- `opf.ac.solver`, `opf.dc.solver` -- OPF solver selection
- `opf.flow_lim` -- Branch flow constraint type (`'S'`, `'P'`, `'2'`, `'I'`)
- `opf.violation` -- Constraint violation tolerance
- `cpf.parameterization` -- CPF parameterization (natural, arc length, pseudo arc length)
- `cpf.stop_at` -- CPF stopping criterion (`'NOSE'`, `'FULL'`, or target lambda)
- `verbose` -- Output verbosity (0-3)
- `out.*` -- Output formatting control

Example:
```matlab
mpopt = mpoption('opf.dc.solver', 'GUROBI', 'verbose', 0);
results = rundcopf(mpc, mpopt);
```

Source: `lib/mpoption.m`

### Input/Output Formats

**Native format:** MATPOWER case `.m` file -- a MATLAB/Octave function that returns an `mpc` struct. This is the de facto standard for sharing power system test cases across the research community. Also supports `.mat` (binary MATLAB format).

**Import:** PSS/E RAW (via `psse2mpc`), IEEE CDF (via `cdf2mpc`)

**Export:** MATPOWER `.m` / `.mat` (via `savecase`), PSS/E RAW Rev 33 (via `save2psse`)

**Bundled test cases:** 84 case files in `data/`, ranging from 4-bus pedagogical cases to 13,659-bus PEGASE models. Includes IEEE standard cases (9, 14, 30, 39, 57, 118, 300), Polish system cases (2383, 2736, 3012, 3120, 3375), RTE French cases (1888, 1951, 2848, 2868), and PEGASE cases (1354, 2869, 9241, 13659).

### Sub-Packages

| Package | Purpose | Key Function |
|---------|---------|-------------|
| **MIPS** | MATPOWER Interior Point Solver; pure MATLAB/Octave NLP solver | `mips()`, `qps_mips()` |
| **MP-Opt-Model** | Optimization modeling framework; solver abstraction layer; `have_feature` detection | `qps_matpower()`, `miqps_matpower()`, solver option translators |
| **MP-Test** | Testing framework | `t_begin()`, `t_ok()`, `t_is()` |
| **MOST** | Multi-period Optimal Scheduling Tool; SCUC/SCED | `most()` |

### Extras

The `extras/` directory contains optional packages not loaded by default:

- `sdp_pf` -- Semidefinite programming relaxation for OPF
- `se` / `state_estimator` -- State estimation
- `smartmarket` -- Electricity market auction simulation
- `syngrid` -- Synthetic grid generation
- `reduction` -- Network reduction
- `maxloadlim` -- Maximum loadability limit computation
- `simulink_matpower` -- Simulink integration

## Sources

- **Source code:** `evaluations/matpower/matpower8.1/lib/` -- all function headers read directly
- **MATPOWER website:** https://matpower.org
- **GitHub repository:** https://github.com/MATPOWER/matpower
- **Primary citation:** R. D. Zimmerman, C. E. Murillo-Sanchez, R. J. Thomas, "MATPOWER: Steady-State Operations, Planning and Analysis Tools for Power Systems Research and Education," IEEE Trans. Power Syst., vol. 26, no. 1, pp. 12-19, Feb. 2011. DOI: 10.1109/TPWRS.2010.2051168
- **MATPOWER 8.1 DOI:** 10.5281/zenodo.15871662
- **Docs directory:** `evaluations/matpower/matpower8.1/docs/` (PDF manual, technical notes, Sphinx source)
- **Install findings:** `evaluations/matpower/notes/install-findings.md`

## Gaps and Open Questions

1. **No programmatic JSON/CSV/DataFrame export.** Results are returned as MATLAB structs with numeric matrices. There is no built-in way to export results to JSON, CSV, or any format consumable by non-MATLAB tools without writing custom serialization code.

2. **New flexible framework documentation is incomplete.** The Sphinx-based reference manual for the new `run_pf`/`run_opf` framework states "the new web-based version of the User's Manual is not yet available" and refers users to the legacy PDF manual. The MP-Core class hierarchy is documented in the developer manual but not yet in a user-facing guide.

3. **Three-phase / unbalanced power flow.** The GitHub README mentions "single-phase to three-phase conversion capabilities" but this was not found in the 8.1 source. It may be experimental or in-development.

4. **MOST documentation.** The MOST sub-package has its own manual (referenced but not found as a standalone file in the distribution). The `mdi` input struct for `most()` is complex and not fully documented in function headers -- the manual is required.

5. **No native Python/Julia bindings.** MATPOWER is MATLAB/Octave only. Third-party wrappers exist (e.g., `matpower` PyPI package uses Oct2Py bridge) but are not part of the official distribution.

## 6. **Solver availability in Octave.** Several solver interfaces (FMINCON, CPLEX, GUROBI, KNITRO, MOSEK) require MATLAB toolboxes or commercial licenses. In Octave, the available solvers are typically limited to MIPS (built-in), IPOPT, GLPK, and OSQP. The `have_feature` system detects what is available at runtime.

# MATPOWER: Extension Mechanisms, Architecture, and Interoperability

Research compiled 2026-03-13 for contract .

## 1. Internal Architecture (Separation of Concerns)

### 1.1 Three-Layer Model Architecture (MP-Core, MATPOWER 8.x)

MATPOWER 8.x introduced a new object-oriented framework ("MP-Core") with explicit
separation into three model layers, coordinated by a **task** object:

| Layer | Base Class | Purpose |
|---|---|---|
| **Data Model** | `mp.data_model` | User-visible parameters, input/output data (analogous to legacy `mpc` struct) |
| **Network Model** | `mp.net_model` | Electrical topology, admittance relationships, node/port/state indexing |
| **Mathematical Model** | `mp.math_model` | Optimization problem formulation (variables, constraints, costs) |
| **Data Model Converter** | `mp.dm_converter` | Bridges external data formats (e.g. MPC structs) to internal representation |
| **Task** | `mp.task` | Orchestrates the full workflow: build models, solve, propagate solution |

Source: MATPOWER Developer's Manual, Sections 3-8 ([matpower.org/doc/dev-manual/](https://matpower.org/doc/dev-manual/)).

Each layer is a **container** (`mp.element_container`) holding typed **element** objects.
For example, the data model contains `mp.dme_bus`, `mp.dme_gen`, `mp.dme_branch`,
`mp.dme_load`, and `mp.dme_shunt` by default. Each element class encapsulates the
data and behavior for one type of power system component.

### 1.2 Element Container Pattern

Every model layer follows the same pattern: a container object holds a collection of
element objects, each identified by a `name()` method. Building proceeds in stages:

1. Create element objects from `element_classes` list
2. Count elements, remove empty types
3. Initialize status (online/offline)
4. Build parameters from data

Elements in one layer reference corresponding elements in other layers during the
build process, enabling cross-layer coordination without tight coupling.

Source: `mp.element_container` mixin; `mp.data_model.build()` method in
`lib/+mp/data_model.m`.

### 1.3 Two Parallel Frameworks

MATPOWER maintains two parallel execution frameworks:

- **Legacy framework**: Uses `runpf()`, `runopf()`, `runcpf()` entry points.
  Data flows through `ext2int()` / `int2ext()` conversion. Extensions use
  `userfcn` callbacks and `toggle_*` functions. Backward-compatible with
  MATPOWER 4.x-7.x code.

- **Flexible framework**: Uses `run_pf()`, `run_opf()`, `run_cpf()` (underscore
  variants) via `run_mp()`. Full OOP with `mp.extension` classes. Supports
  advanced features like three-phase unbalanced modeling.

Both frameworks coexist in MATPOWER 8.x; the legacy framework internally wraps
MP-Core via `mp.task_*_legacy` classes.

Source: MATPOWER Dev Manual, Section 3 "Two MATPOWER Frameworks"
([matpower.org/doc/dev-manual/architecture.html](https://matpower.org/doc/dev-manual/architecture.html)).

### 1.4 MP-Opt-Model (Mathematical Modeling Layer)

The mathematical model layer is built on **MP-Opt-Model** (`mp-opt-model/`), a
standalone optimization modeling framework. The `opt_model` class (and its modern
successor `mp.opt_model`) provides:

- Named variable sets: `om.add_var('V', nb, V0, Vmin, Vmax, 'C')`
- Linear constraints: `om.add_lin_constraint('Pmis', A, l, u, varsets)`
- Nonlinear constraints: `om.add_nln_constraint('Qmis', n, iseq, fcn, hess)`
- Quadratic costs: `om.add_quad_cost('gen_cost', Q, c, k, varsets)`
- Nonlinear costs: `om.add_nln_cost('fuel_cost', n, fcn, varsets)`
- Unified solver interface: `om.solve()` routes to appropriate backend

Supported solver backends: MIPS (built-in), IPOPT, GLPK, Gurobi, CPLEX, MOSEK,
HiGHS, OSQP, Knitro, fmincon, and others. Solver selection is automatic based
on problem type (LP/QP/MILP/NLP) or configurable via `mpoption`.

Source: MP-Opt-Model library at `mp-opt-model/lib/@opt_model/`;
[matpower.org/doc/mpom/](https://matpower.org/doc/mpom/).
## 2. Extension Mechanisms

### 2.1 Legacy userfcn Callback System

The legacy framework provides five callback stages, registered via
`add_userfcn(mpc, stage, fcn, args)`:

| Stage | When Called | Typical Use |
|---|---|---|
| `ext2int` | After external-to-internal conversion | Reorder extension data |
| `formulation` | After base OPF model setup, before solve | Add variables, constraints, costs |
| `int2ext` | Before internal-to-external conversion | Package results |
| `printpf` | During pretty-printing | Print extension results |
| `savecase` | During case file saving | Save extension data |

Signature examples:
```matlab
mpc = userfcn_reserves_ext2int(mpc, mpopt, args)
om  = userfcn_reserves_formulation(om, mpopt, args)
results = userfcn_reserves_int2ext(results, mpopt, args)
results = userfcn_reserves_printpf(results, fd, mpopt, args)
mpc = userfcn_reserves_savecase(mpc, fd, prefix, args)
```

Functions: `add_userfcn()`, `remove_userfcn()`, `run_userfcn()` in `lib/`.

Source: `lib/add_userfcn.m` lines 1-85.

### 2.2 toggle_* Convenience Functions (Legacy)

Built-in extensions using the userfcn mechanism:

| Function | Purpose |
|---|---|
| `toggle_reserves(mpc, 'on'/'off')` | Fixed zonal reserve co-optimization |
| `toggle_softlims(mpc, 'on'/'off')` | Relaxed OPF inequality constraints with penalties |
| `toggle_iflims(mpc, 'on'/'off')` | Interface flow limits (DC model) |
| `toggle_dcline(mpc, 'on'/'off')` | DC line modeling via linked generator pairs |

Each function registers/removes the five userfcn callbacks. Status can be queried:
`toggle_reserves(mpc, 'status')` returns 1 or 0.

Source: `lib/toggle_reserves.m`, `lib/toggle_softlims.m`, `lib/toggle_iflims.m`,
`lib/toggle_dcline.m`.

### 2.3 mp.extension API (Flexible Framework)

The modern extension API uses the `mp.extension` abstract base class. An extension
subclass overrides up to 9 methods to modify or replace default classes at each
model layer:

**Container-level class overrides** (return function handles to constructors):
```matlab
task_class(obj, task_class, mpopt)          % override task class
dm_converter_class(obj, dmc_class, fmt, mpopt)  % override converter class
dm_class(obj, dm_class, mpopt)              % override data model class
nm_class(obj, nm_class, mpopt)              % override network model class
mm_class(obj, mm_class, mpopt)              % override math model class
```

**Element-level class modifiers** (return cell arrays of modifiers):
```matlab
dmc_element_classes(obj, dmc_class, fmt, mpopt)   % data converter elements
dm_element_classes(obj, dm_class, task_tag, mpopt) % data model elements
nm_element_classes(obj, nm_class, task_tag, mpopt) % network model elements
mm_element_classes(obj, mm_class, task_tag, mpopt) % math model elements
```

Element class modifiers support three operations applied sequentially:

| Modifier Type | Syntax | Effect |
|---|---|---|
| Add | `@new_class` | Append new element class |
| Delete | `'old_class'` | Remove matching element class |
| Replace | `{@new_class, 'old_class'}` | Substitute matching class |

Usage:
```matlab
task = run_opf('case9', mpopt, 'mpx', mp.xt_reserves);
task = run_opf('case9', mpopt, 'mpx', {mpx1, mpx2});  % multiple extensions
```

Source: `lib/+mp/extension.m`; MATPOWER Dev Manual Section 9
([matpower.org/doc/dev-manual/customizing.html](https://matpower.org/doc/dev-manual/customizing.html));
[matpower.org/doc/howto/extension.html](https://matpower.org/doc/howto/extension.html).

### 2.4 Built-in Extensions (Flexible Framework)

| Extension Class | Purpose |
|---|---|
| `mp.xt_reserves` | Fixed zonal reserves for OPF (adds `reserve_gen` and `reserve_zone` elements) |
| `mp.xt_3p` | Three-phase unbalanced elements (bus3p, gen3p, load3p, line3p, shunt3p, xfmr3p) |

Source: `lib/+mp/xt_reserves.m`, `lib/+mp/xt_3p.m`.

### 2.5 Customization via MATPOWER Options

The `mpopt.exp` struct allows runtime class overrides without creating an extension:

```matlab
mpopt.exp.math_model_class = @custom_math_model;
mpopt.exp.mm_element_classes = {@custom_gen_opf, 'mp.mme_gen_opf'};
mpopt.exp.exclude_elements = {'shunt'};
```

Available `mpopt.exp` fields: `dm_converter_class`, `data_model_class`,
`network_model_class`, `math_model_class`, `dmc_element_classes`,
`dm_element_classes`, `nm_element_classes`, `mm_element_classes`,
`exclude_elements`.

Source: MATPOWER Dev Manual Section 9.2.

### 2.6 CPF Event and Callback System

The Continuation Power Flow (CPF) has its own event/callback registration mechanism:

**Events** detect specific conditions during CPF tracing:
```matlab
cpf_events = cpf_register_event(cpf_events, name, fcn, tol, locate)
```
Built-in events: voltage limits, flow limits, nose point detection, generator
reactive limits, target lambda.

**Callbacks** respond to events and control CPF behavior:
```matlab
cpf_callbacks = cpf_register_callback(cpf_callbacks, fcn, priority, args)
```
Callbacks have configurable priority (higher = runs first). Default priorities
range from 0 (`cpf_default_callback`) to 53 (`cpf_flim_event_cb`).

User callbacks are specified via `mpopt.cpf.user_callback` (string, struct with
`fcn`/`priority`/`args`, or cell array of these).

Source: `lib/cpf_register_event.m`, `lib/cpf_register_callback.m`.

### 2.7 Adding Custom OPF Constraints

Two approaches for adding custom constraints:

**Legacy approach** (via userfcn `formulation` callback):
```matlab
% Inside formulation callback, add to opt_model:
om.add_lin_constraint('my_constraint', A, l, u, {'Pg', 'Qg'});
om.add_nln_constraint('pq_cap', n, 0, @my_fcn, @my_hess, {'Pg', 'Qg'});
```

**Modern approach** (via element class subclassing):
Create a subclass of the relevant math model element (e.g., `mp.mme_gen_opf_ac`)
and override `add_constraints()` to call `add_nln_constraint()`. The how-to guide
demonstrates an "oval PQ capability curve" constraint as an example.

Source: [matpower.org/doc/howto/add-constraint.html](https://matpower.org/doc/howto/add-constraint.html);
`mp-opt-model/lib/@opt_model/add_nln_constraint.m`.

### 2.8 Creating New Element Types

A new element type requires classes at up to four layers:

1. **Data model element** (`mp.dm_element` subclass): Define `name()`,
   `main_table_var_names()`, `cxn_type()`, `cxn_idx_prop()`, `build_params()`.
   OPF variant adds cost parameters.

2. **Data model converter element** (`mp.dmc_element` subclass): Define
   `data_field()`, `table_var_map()` for import/export.

3. **Network model element** (`mp.nm_element` subclass): Define `np()` (ports),
   `nz()` (states), `build_params()`. Separate classes for AC polar, AC
   cartesian, and DC formulations.

4. **Math model element** (`mp.mm_element` subclass): Define `add_vars()`,
   `add_constraints()`, `add_costs()`, `data_model_update_on()`. Separate
   classes for PF vs OPF and AC vs DC.

Source: [matpower.org/doc/howto/element.html](https://matpower.org/doc/howto/element.html).
## 3. Graph/Network Topology Access

### 3.1 Admittance and Distribution Factor Matrices

MATPOWER provides direct access to key network matrices:

| Function | Returns | Size |
|---|---|---|
| `makeYbus(mpc)` | Bus admittance matrix `Ybus`, branch matrices `Yf`, `Yt` | nb x nb, nl x nb |
| `makeBdc(mpc)` | DC susceptance matrices `Bbus`, `Bf`, injection vectors | nb x nb, nl x nb |
| `makePTDF(mpc, slack)` | Power Transfer Distribution Factor matrix | nl x nb |
| `makeLODF(mpc, PTDF)` | Line Outage Distribution Factor matrix | nl x nl |
| `makeJac(mpc)` | Jacobian matrix for Newton power flow | 2nb x 2nb |

These matrices implicitly encode the network graph structure. `Ybus` is the
weighted graph Laplacian (with self-loops for shunts). The bus admittance
matrix is a sparse matrix with non-zero entries corresponding to direct
electrical connections.

Source: `lib/makeYbus.m`, `lib/makeBdc.m`, `lib/makePTDF.m`, `lib/makeLODF.m`.

### 3.2 Graph Topology Functions

Explicit graph-theoretic operations:

| Function | Purpose |
|---|---|
| `find_islands(mpc)` | Find connected components; returns cell array of bus groups |
| `extract_islands(mpc)` | Extract individual islands as separate MPC structs |
| `connected_components(C)` | BFS on node-branch incidence matrix `C` |
| `find_bridges(mpc)` | Tarjan's algorithm for bridge detection |
| `order_radial(mpc)` | Oriented ordering for radial networks |

The incidence matrix `C` is constructed from branch from/to bus data:
```matlab
C = sparse(1:nl, f, -status, nl, nb) + sparse(1:nl, t, status, nl, nb);
```
This `C` matrix is the directed node-branch incidence matrix of the network
graph.

Source: `lib/find_islands.m`, `lib/connected_components.m`,
`lib/find_bridges.m`, `lib/order_radial.m`.

### 3.3 Network Model Node/Port/State Framework

In the flexible framework, `mp.net_model` provides structured topology access:

- **Nodes**: Network connection points (buses). Tracked via `mp_idx_manager`.
- **Ports**: Element connection points mapped to nodes via incidence matrices `C`.
- **States**: Voltage (V) and non-voltage (Z) state variables.

Each network model element defines:
- `np()`: number of ports
- `nz()`: number of non-voltage states
- Incidence matrices mapping ports to nodes and states to variables

The network model inherits from `mp.nm_element`, `mp.element_container`, and
`mp_idx_manager`, providing both graph structure and variable indexing.

Source: `lib/+mp/net_model.m`, MATPOWER Dev Manual Section 7.

### 3.4 No Native Graph Object

MATPOWER does **not** provide a native graph object (e.g., no `Graph` class or
adjacency list structure). The network topology is encoded implicitly in:
- Sparse admittance matrices (`Ybus`)
- Branch from/to bus columns (`branch(:, F_BUS)`, `branch(:, T_BUS)`)
- Incidence matrices (`C`)

Users needing explicit graph representations must construct them from the
branch data. The adjacency matrix can be derived from `Ybus`:
```matlab
adj = spones(Ybus) - speye(nb);  % adjacency matrix (unweighted)
```
## 4. Interoperability

### 4.1 Native Format

MATPOWER's native data format is the **MPC struct** (MATPOWER Case), a MATLAB/Octave
struct with fields: `baseMVA`, `bus`, `gen`, `branch`, `gencost`, and optional
fields (`dcline`, `reserves`, `if`, `softlims`, `bus_name`, etc.).

Data is stored as numeric matrices with column indices defined by constant
functions (`idx_bus`, `idx_gen`, `idx_brch`, `idx_cost`, `idx_dcline`).

File formats: `.m` (MATLAB script) and `.mat` (MATLAB binary).
Functions: `loadcase()`, `savecase()`.

### 4.2 Industry Format Import/Export

| Function | Direction | Format |
|---|---|---|
| `psse2mpc(rawfile)` | Import | PSS/E RAW (auto-detects revision) |
| `save2psse(fname, mpc)` | Export | PSS/E RAW Rev 33 |
| `cdf2mpc(cdffile)` | Import | IEEE Common Data Format |

The PSS/E converter supports import from multiple revisions and export to Rev 33.

Source: `lib/psse2mpc.m`, `lib/save2psse.m`, `lib/cdf2mpc.m`.

### 4.3 Python Interoperability

The `matpower` PyPI package (`pip install matpower`) bundles MATPOWER 8.1 and
provides Python access via:
- **oct2py**: Python-to-Octave bridge
- **matlab.engine**: Python-to-MATLAB bridge

```python
from matpower import start_instance
m = start_instance()
mpc = m.loadcase('case9')
results = m.runpf(mpc)
```

**Limitations**:
- `runopf()` returns `opf_model` objects that oct2py cannot serialize; manual
  field removal is required.
- MATLAB engine does not support sparse matrices natively.
- Data crosses a process boundary (Python <-> Octave/MATLAB), incurring
  serialization overhead.

Source: [pypi.org/project/matpower/](https://pypi.org/project/matpower/).

### 4.4 No Native DataFrame/NetworkX/Graphs.jl Integration

MATPOWER has **no built-in integration** with:
- Python DataFrames (pandas)
- NetworkX graph library
- Julia Graphs.jl

All data lives in MATLAB/Octave numeric matrices and structs. The table-based
data model in the flexible framework (`dm.elements.bus.tab`) uses MATLAB's
`table` class or MATPOWER's `mp_table` wrapper, not pandas DataFrames.

Interoperability with these ecosystems requires explicit conversion:
- Export MPC to CSV/MAT and load in Python/Julia
- Use oct2py or matlab.engine bridges
- Construct graphs manually from branch `F_BUS`/`T_BUS` columns

### 4.5 MOST Integration

MOST (MATPOWER Optimal Scheduling Tool) extends MATPOWER for multi-period,
stochastic, security-constrained OPF with unit commitment. It uses the same
MPC data format augmented with:
- `md_init()`: Initialize MOST data structure
- `loadmd()`: Load MOST data
- `most(mdi, mpopt)`: Run scheduling optimization
- Storage, wind, profile, and ramping data structures

MOST is bundled with MATPOWER at `most/lib/`.

Source: `most/lib/most.m`.

### 4.6 Additional Toolboxes (extras/)

MATPOWER bundles several contributed extensions in `extras/`:

| Toolbox | Purpose |
|---|---|
| `se/` | State estimation |
| `syngrid/` | Synthetic grid generation |
| `reduction/` | Network reduction |
| `sdp_pf/` | SDP-based power flow relaxation |
| `smartmarket/` | Electricity market simulation |
| `maxloadlim/` | Maximum loadability limit |
| `simulink_matpower/` | Simulink integration |

## 5. Assessment Summary

### Strengths

- **Mature, well-documented extension architecture**: Both legacy (userfcn) and
  modern (mp.extension) APIs provide structured extensibility.
- **Clean separation of concerns**: Three-layer model architecture with distinct
  data/network/math layers and element-based decomposition.
- **Rich built-in extensions**: Reserves, soft limits, interface flow limits,
  DC lines, three-phase elements demonstrate the framework's flexibility.
- **Comprehensive network matrix functions**: Ybus, PTDF, LODF, Jacobian,
  and graph topology functions (islands, bridges) are directly accessible.
- **Multiple constraint addition mechanisms**: Both linear (`A*x` bounds) and
  nonlinear (function handle + Hessian) constraints.
- **Solver abstraction**: MP-Opt-Model decouples problem formulation from solver
  selection across 10+ solver backends.

### Weaknesses

- **No native graph object**: Network topology is implicit in sparse matrices,
  not exposed as a graph data structure.
- **MATLAB/Octave ecosystem lock-in**: No native Python, Julia, or cross-language
  bindings. The oct2py bridge has significant limitations (sparse matrix
  serialization, opf_model objects).
- **No DataFrame integration**: Data is in numeric matrices, not
  columnar/labeled structures accessible to data science ecosystems.
- **Extension complexity**: Creating a new element type requires implementing
  classes at 4 layers with up to 8+ subclasses for different formulations
  (AC polar, AC cartesian, DC) and tasks (PF, OPF).
- **Two parallel frameworks**: Maintaining legacy and flexible frameworks
  creates cognitive overhead and potential confusion about which API to use.

### Gaps and Uncertainties

- The full extent of mp.extension overriding capabilities (e.g., can an extension
  replace the solver itself?) is not fully documented beyond the examples.
- Performance implications of the OOP layered architecture in Octave (which has
  slower OOP dispatch than MATLAB) are not quantified.
- The `mp_table` class's compatibility with MATLAB's native `table` in Octave
## environments may vary; Octave's `table` support is relatively recent.
##
tool: matpower
research_date: 2026-03-13
focus: Known limitations, open issues, ecosystem, community size, documentation quality, release history
## version_evaluated: "8.1"

# MATPOWER — Limitations, Ecosystem & Community Research

## 1. Known Limitations

### 1.1 MOST Limited to DC Network Model

MOST (MATPOWER Optimal Scheduling Tool) provides multi-period OPF, unit commitment, and storage
optimization but is restricted to DC power flow network constraints. The MOST README states that
"some work has been done on an AC implementation, but it is not yet ready for release." This has
been the case since MOST's inception (~2014). Multi-period AC OPF is not available in the open-source
MATPOWER ecosystem.

**Evaluation impact:** Tests A-5 (SCUC), A-6 (SCED), and A-12 (multi-period DCOPF with storage)
use DC formulations and are unaffected. However, any future requirement for AC multi-period
optimization would be unmet.

*Source: [MOST README](https://github.com/MATPOWER/most/blob/master/README.md)*

### 1.2 No Native SCOPF Function

MATPOWER does not ship a standalone security-constrained OPF (SCOPF) function. MOST can model
contingency states with probability weighting in a stochastic framework, but there is no turnkey
`runSCOPF()` or equivalent. Users must either:
- Use MOST's contingency/scenario framework (DC only)
- Manually construct contingency constraints via the MP-Opt-Model Extension API
- Script iterative contingency screening by running `rundcopf()` in a loop with LODF-based
  post-contingency flow checks

**Evaluation impact:** Test A-9 (SCOPF) will require either the MOST approach or manual constraint
assembly, both of which are non-trivial. This is a qualified pass scenario at best.

*Source: Open issue survey; MATPOWER User's Manual lacks SCOPF section*

### 1.3 Scalability of MOST Model Construction

GitHub issue [MOST #7](https://github.com/MATPOWER/most/issues/7) documents that building a MOST
model for 8,760 periods (1 year) took 7 hours on a high-performance cluster before solving. The
bottleneck is in `add_named_set` and `params_lin_constraint` routines. A user-contributed patch
achieved ~20% speedup by optimizing sparse matrix operations. Workarounds include building
time-sliced sub-models and connecting them.

**Evaluation impact:** Suite C scalability tests use 24-hour horizons on MEDIUM (10k buses), which
is far smaller than 8,760 periods. This limitation is unlikely to affect Phase 1 but is relevant
for production deployment at annual planning horizons.

*Source: [MOST issue #7](https://github.com/MATPOWER/most/issues/7)*

### 1.4 No Native CSV Import

MATPOWER's `loadcase()` supports only `.m` and `.mat` files natively, plus PSS/E `.raw` via
`psse2mpc()`. There is no built-in CSV reader. Time-series data for MOST (load profiles, wind/solar
forecasts, storage parameters) must be loaded via custom MATLAB/Octave scripts.

**Evaluation impact:** Tests requiring augmented data (A-5, A-6, A-12) will need custom loading
scripts to read CSV files from `data/timeseries/case39/`.

### 1.5 No Built-In Parallel Computation

MATPOWER has no native parallel execution support. MATLAB users can wrap calls in `parfor`
(requires the commercial Parallel Computing Toolbox), but this has known issues with MATPOWER's
use of global variables. GNU Octave's `parallel` package is not equivalent and is not recommended
by the MATPOWER team.

**Evaluation impact:** Scalability tests (Suite C) will reflect single-threaded performance only.

### 1.6 No Distributed Slack in OPF (Standard API)

MATPOWER issue [#136](https://github.com/MATPOWER/matpower/issues/136) (open since 2022) requests
distributed slack bus support for power flow. The `makePTDF()` function accepts a custom slack
distribution vector, but the standard OPF formulation uses a single slack bus. Distributed slack
OPF would require custom constraint injection.

**Evaluation impact:** Test A-11 (distributed slack OPF) will require workaround construction.

*Source: [Issue #136](https://github.com/MATPOWER/matpower/issues/136)*

### 1.7 No LMP Decomposition API

MATPOWER's OPF produces nodal LMPs (shadow prices on bus power balance constraints), but does
not natively decompose them into energy, congestion, and loss components. Users must extract
shadow prices from the optimization result and perform the decomposition manually using PTDFs
and constraint multipliers.

**Evaluation impact:** Test A-10 (lossy DC OPF / LMP decomposition) will require manual
post-processing of solver output.

### 1.8 MOST Pro — Commercial Extension

The MATPOWER 8.1 release notes mention "MOST Pro 1.4.1" as a paid upgrade that adds DC
transmission line support. MOST Pro is not open-source and is available only by contacting
info@matpower.org. The open-source MOST 1.3.1 included with MATPOWER 8.1 does not include
DC line support.

**Evaluation impact:** Per protocol, only open-source packages are evaluated. MOST Pro
capabilities are excluded.

*Source: [MATPOWER 8.1 release notes](https://github.com/MATPOWER/matpower/releases/tag/8.1)*

### 1.9 Octave vs. MATLAB Compatibility

MATPOWER officially supports both MATLAB and GNU Octave. However, some edge cases exist:
- Issue [#270](https://github.com/MATPOWER/matpower/issues/270): `test_matpower` unrecognized
  field name "optimstatus" under MATLAB (fixed in 8.1)
- HiGHS solver integration works on both platforms as of 8.1
- Three-phase features are proof-of-concept and may have platform-specific behavior
- Performance differs: MATLAB's JIT compiler is generally faster than Octave's interpreter

**Evaluation impact:** Evaluation uses GNU Octave (devcontainer). Performance measurements
reflect Octave execution speed, not MATLAB.

## 2. Open Issues Relevant to Evaluation Tests

| Issue | Repo | Relevance | Status |
|-------|------|-----------|--------|
| [#136](https://github.com/MATPOWER/matpower/issues/136) — Distributed slack bus PF | matpower | A-11 (distributed slack OPF) | Open (since 2022) |
| [#104](https://github.com/MATPOWER/matpower/issues/104) — Extend zonal reserves | matpower | A-5 (SCUC reserve requirements) | Open (since 2020) |
| [#24](https://github.com/MATPOWER/matpower/issues/24) — Rate B/C not in OPF | matpower | Emergency ratings for SCOPF | Open (since 2017) |
| [#127](https://github.com/MATPOWER/matpower/issues/127) — makePTDF ext2int error | matpower | PTDF extraction (B-5) | Open (since 2021) |
| [#279](https://github.com/MATPOWER/matpower/issues/279) — CPF stuck in loop | matpower | Not directly tested in Phase 1 | Open (since 2025) |
| [MOST #5](https://github.com/MATPOWER/most/issues/5) — DC transmission lines | most | Multi-period with DC lines | Open (since 2019) |
| [MOST #50](https://github.com/MATPOWER/most/issues/50) — Downward reserve | most | Reserve requirements in UC | Open (since 2025) |

## 3. Ecosystem Packages

MATPOWER's ecosystem is a set of modular packages maintained under the MATPOWER GitHub organization,
all by the same core team (primarily Ray Zimmerman at Cornell / PSERC).

| Package | Description | Version | Stars | Forks | License | Last Push |
|---------|-------------|---------|-------|-------|---------|-----------|
| [matpower](https://github.com/MATPOWER/matpower) | Core PF/OPF engine | 8.1 | 539 | 173 | BSD 3-Clause | 2026-03-11 |
| [most](https://github.com/MATPOWER/most) | Multi-period scheduling, UC, storage | 1.3.1 | 39 | 15 | BSD 3-Clause | 2026-02-16 |
| [mp-opt-model](https://github.com/MATPOWER/mp-opt-model) | Optimization modeling layer | 5.0 | 10 | 5 | BSD 3-Clause | 2025-12-11 |
| [mips](https://github.com/MATPOWER/mips) | Interior point solver | 1.5.2 | 16 | 3 | BSD 3-Clause | 2025-07-12 |
| [mptest](https://github.com/MATPOWER/mptest) | Unit testing framework | 8.1 | 1 | 4 | BSD 3-Clause | 2025-07-08 |
| [mp-element](https://github.com/MATPOWER/mp-element) | New element modeling layer (merged into matpower 8.0) | — | 4 | 0 | BSD 3-Clause | 2023-02-02 |

### Third-Party Ecosystem

- **[matpower-pip](https://github.com/yasirroni/matpower-pip)** — Python wrapper via oct2py,
  installable via `pip install matpower[octave]`. Third-party, not evaluated.
- **SimulinkMATPOWER** — Simulink interface, included in MATPOWER Extras (requires MATLAB +
  Simulink). Not relevant for Octave-based evaluation.
- **matpowercaseframes** — Python package for reading/writing MATPOWER case files as DataFrames.
  Third-party, not evaluated.

### Dependency Composition

MATPOWER's dependency tree is minimal and entirely self-contained:
- MIPS (bundled) — only solver that ships with MATPOWER
- MP-Opt-Model (bundled) — optimization abstraction layer
- MP-Test (bundled) — testing framework
- MOST (bundled) — scheduling/UC extension

External optional solvers: IPOPT, GLPK, HiGHS, Knitro, CPLEX, Gurobi, MOSEK, SDPT3, SeDuMi.
The evaluation devcontainer provides IPOPT, GLPK, and HiGHS.

**Supply chain finding:** All bundled dependencies are BSD 3-Clause licensed and maintained by
the same team. No transitive dependency risk. External solvers have their own licenses (IPOPT:
EPL-2.0; GLPK: GPL-3.0; HiGHS: MIT).

## 4. Community Size

| Metric | Value | Date |
|--------|-------|------|
| GitHub stars | 539 | 2026-03-13 |
| GitHub forks | 173 | 2026-03-13 |
| Contributors (GitHub) | 17 | 2026-03-13 |
| Open issues (non-PR) | 14 | 2026-03-13 |
| Closed issues (non-PR) | ~212 | 2026-03-13 |
| Annual downloads | 40,000+ | per matpower.org |
| Total downloads | 800,000+ | per matpower.org |
| Google Scholar citations | 750+ per year (as of 2018) | per matpower.org/about |
| Countries using | 100+ | per matpower.org/about |

### Community Characteristics

- **Small core team, large user base:** 17 GitHub contributors but 40,000+ annual downloads.
  The project is primarily maintained by Ray Zimmerman (Cornell/PSERC) with occasional
  contributions from the community.
- **Academic-dominant user base:** Widely used in power systems education and research at
  universities worldwide. Referenced extensively in IEEE/PSCC conference papers.
- **Government and industry use:** matpower.org lists Cornell, IIT, ANL (Argonne National Lab),
  University of Washington, and RTE (French TSO) as users.
- **Low issue volume:** Only 14 open issues across 9+ years of GitHub hosting suggests either
  high code quality or low community engagement on GitHub (likely both — much support happens
  via the MATPOWER mailing list, not GitHub issues).
- **Mailing list activity:** The primary support channel is the MATPOWER discussion mailing list,
  not GitHub. Issue counts underrepresent community engagement.

## 5. Documentation Quality

### Available Documentation

| Document | Format | Quality |
|----------|--------|---------|
| [MATPOWER User's Manual](https://matpower.org/docs/MATPOWER-manual.pdf) | PDF (247 pages) | Comprehensive; covers data format, PF, OPF, extensions, options; not yet fully updated for 8.x flexible framework |
| [MATPOWER Developer's Manual](https://matpower.org/doc/) | HTML (Sphinx) | New in 8.0; covers MP-Core architecture, extension API |
| [MATPOWER Reference Manual](https://matpower.org/doc/) | HTML (Sphinx) | Function and class reference; generated from source |
| [MOST User's Manual](https://matpower.org/docs/MOST-manual.pdf) | PDF | Covers MOST problem formulation, data structures, examples |
| [MP-Opt-Model User's Manual](https://matpower.org/doc/) | HTML | Optimization modeling API documentation |
| Technical Notes (TN1-TN5) | PDF | Detailed mathematical derivations |
| How-To Guides | HTML | Practical guides (adding constraints, creating elements, three-phase PF) |
| In-code help | `help <function>` | Every function has a help block |

### Documentation Strengths

- **Mathematical rigor:** Technical notes provide full derivations of power flow equations,
  derivatives, and OPF formulations. Useful for verification against reference results.
- **Comprehensive options reference:** All solver and algorithm options documented in the
  User's Manual.
- **Case file format specification:** Detailed specification of the MATPOWER case format
  (version 1 and 2), enabling third-party interoperability.
- **DOI-registered releases:** Zenodo DOIs for reproducible research citation.

### Documentation Gaps

- **User's Manual not fully updated for 8.x:** The flexible framework (`run_pf`, `run_opf`)
  is documented in the Developer's Manual but the User's Manual still primarily covers the
  legacy framework. Users must consult multiple documents.
- **MOST documentation is sparse:** The MOST manual exists but lacks worked examples for
  common workflows (e.g., "add storage to a multi-period UC"). Users often resort to reading
  test scripts in `most/lib/t/` for guidance.
- **No tutorial/quickstart for Octave users:** Documentation assumes MATLAB. Octave-specific
  differences (e.g., package loading, solver availability) are not covered.
- **Extension API examples are minimal:** The 8.x Extension API is powerful but the how-to
  guides cover only basic cases. Complex extensions (e.g., custom element types with new
  state variables) require reading the Developer's Manual and MP-Core source code.

## 6. Release History

| Version | Date | Cadence |
|---------|------|---------|
| 8.1 | 2025-07-12 | 14 months after 8.0 |
| 8.0 | 2024-05-17 | 17 months after 8.0b1 |
| 8.0b1 | 2022-12-23 | 27 months after 7.1 |
| 7.1 | 2020-10-08 | 16 months after 7.0 |
| 7.0 | 2019-06-21 | 8 months after 7.0b1 |
| 7.0b1 | 2018-11-01 | — |

### Release Cadence Analysis

- **Irregular cadence:** 8-27 months between releases. No fixed release schedule.
- **Active development:** Last push to `master` was 2026-03-11 (2 days before research date).
  The project is actively maintained.
- **Long-lived major versions:** Major versions (7.x, 8.x) span multiple years. The 8.0 rewrite
  took 2+ years from beta to release.
- **Stability-oriented:** Long release cycles suggest emphasis on stability over rapid feature
  delivery. Suitable for production/research use where API stability matters.

### MOST Release History

| Version | Date | Notes |
|---------|------|-------|
| 1.3.1 | 2025-07-12 | Bundled with MATPOWER 8.1 |
| 1.3 | 2024-05-15 | TLMP calculation, improved speed/memory |
| 1.2 | 2022-12-13 | — |
| 1.1 | 2020-10-08 | — |
| 1.0.2 | 2019-06-20 | — |

MOST releases are synchronized with MATPOWER major releases.

## 7. Evaluation-Specific Risk Assessment

| Test | Risk Level | Key Finding |
|------|-----------|-------------|
| A-1 (DCPF) | Low | Core capability since 1997 |
| A-2 (ACPF) | Low | Core capability; multiple solvers available |
| A-3 (DC OPF) | Low | Core capability; cost curves and line limits well-supported |
| A-4 (AC feasibility) | Low | Standard workflow: solve DC OPF, then run ACPF on dispatch |
| A-5 (SCUC) | Medium | Via MOST; requires non-trivial setup; DC network model only |
| A-6 (SCED) | Medium | Via MOST; commitment schedule from A-5 can be fixed |
| A-9 (SCOPF) | High | No native SCOPF; requires MOST contingency framework or manual constraint construction |
| A-10 (Lossy DC OPF) | High | Loss approximation available but LMP decomposition requires manual post-processing |
| A-11 (Distributed slack) | High | Not natively supported in OPF; requires workaround via PTDF-based reformulation |
| A-12 (Multi-period DCOPF + storage) | Medium | Via MOST; storage and multi-period are supported but setup is manual |
| B-1 (Custom constraints) | Low | MP-Opt-Model Extension API well-documented |
| B-3 (Contingency analysis) | Low | Scriptable via loop over `rundcpf()` with branch removal |
| B-4 (Stochastic scenarios) | Medium | MOST supports stochastic scenarios; setup is complex |
| B-5 (PTDF/LODF) | Low | `makePTDF()` is a core function |

## 8. Gaps and Uncertainties

- **Citation count:** matpower.org states "over 750 citations in 2018." Current citation count
  is likely significantly higher but could not be verified via automated web search (Google
  Scholar blocks scraping).
- **MOST Pro feature set:** Only one feature (DC transmission lines) is documented in the 8.1
  release notes. Full MOST Pro capabilities are unknown without contacting info@matpower.org.
- **Octave performance baseline:** No published benchmarks comparing MATPOWER performance on
  Octave vs. MATLAB. Anecdotal reports suggest 2-5x slower on Octave for large problems.
- **Mailing list activity metrics:** The MATPOWER mailing list is the primary support channel
  but its archive was not searched. GitHub issue counts underrepresent community engagement.
- **RTE/utility deployment details:** matpower.org lists RTE as a user but no details on how
  MATPOWER is used in operational settings (research vs. production).

## Sources

1. [MATPOWER GitHub repository](https://github.com/MATPOWER/matpower) — stars, forks, issues, releases
2. [MOST GitHub repository](https://github.com/MATPOWER/most) — issues, releases, README
3. [MP-Opt-Model GitHub](https://github.com/MATPOWER/mp-opt-model) — metadata
4. [MIPS GitHub](https://github.com/MATPOWER/mips) — metadata
5. [MP-Test GitHub](https://github.com/MATPOWER/mptest) — metadata
6. [MP-Element GitHub](https://github.com/MATPOWER/mp-element) — metadata
7. [matpower.org](https://matpower.org) — download statistics, about page, documentation index
8. [matpower.org/about](https://matpower.org/about/) — capabilities, citation metrics, usage statistics
9. [matpower.org/about/license](https://matpower.org/about/license/) — licensing history
10. [matpower.org/doc](https://matpower.org/doc/) — documentation index
11. [MATPOWER 8.1 release notes](https://github.com/MATPOWER/matpower/releases/tag/8.1)
12. [MATPOWER 8.0 release notes](https://github.com/MATPOWER/matpower/releases/tag/8.0)
13. [MOST issue #7 — Large models](https://github.com/MATPOWER/most/issues/7) — scalability limitation
14. [MOST issue #3 — AC multi-period](https://github.com/MATPOWER/most/issues/3) — AC OPF limitation
15. [MATPOWER issue #134 — Python interop](https://github.com/MATPOWER/matpower/issues/134) — matpower-pip
16. [MATPOWER issue #136 — Distributed slack](https://github.com/MATPOWER/matpower/issues/136)
17. [MATPOWER issue #104 — Zonal reserves](https://github.com/MATPOWER/matpower/issues/104)
## 18. [MATPOWER issue #24 — Rate B/C in OPF](https://github.com/MATPOWER/matpower/issues/24)
##
tool: matpower
installed_version: "8.1"
release_date: 2025-07-12
latest_version: "8.1"
latest_release_date: 2025-07-12
## research_date: 2026-03-13

# matpower — Version & Capability Report

## Version Summary

MATPOWER 8.1 is the latest release (July 12, 2025) and is the version installed in this evaluation environment. It was downloaded via `setup.sh` from the official GitHub release. MATPOWER 8.1 builds on the major 8.0 rewrite (May 17, 2024) that introduced the MP-Core object-oriented architecture, replacing the legacy procedural internals. The 8.1 release adds three-phase modeling utilities, MP-Opt-Model 5.0 with QCQP support and HiGHS solver integration, and includes MOST 1.3.1 for multi-period scheduling.

Since the installed version is the latest available, there are no upgrade concerns or version gaps. The evaluation can rely on all documented 8.1 features.

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes | 1.0 (1997) | `rundcpf()` — core capability since inception |
| AC Power Flow (ACPF) | yes | 1.0 (1997) | `runpf()` — Newton-Raphson, fast-decoupled, Gauss-Seidel solvers; radial PF added in 7.0 |
| DC Optimal Power Flow (DC OPF) | yes | 2.0 (1997) | `rundcopf()` — linear formulation using DC power flow model |
| AC Optimal Power Flow (AC OPF) | yes | 2.0 (1997) | `runopf()` — full nonlinear formulation; supports MIPS, IPOPT, Knitro, fmincon solvers |
| Security-Constrained Unit Commitment (SCUC) | partial | 5.0 (2014) | Via MOST 1.x — solves stochastic, security-constrained, multi-period UC with DC network constraints; AC network model not yet implemented in MOST; requires manual problem setup via `most()` function |
| Security-Constrained Economic Dispatch (SCED) | partial | 5.0 (2014) | Via MOST 1.x — supports contingency-constrained ED with DC OPF; single-period or multi-period; no turnkey SCED function, requires MOST problem specification |
| PTDF / Shift Factor Extraction | yes | 3.x (~2006) | `makePTDF()` — builds nbr x nb DC PTDF matrix; supports custom slack distribution; efficient sparse computation for specific transfers added in 7.1 |
| Contingency Analysis (N-1) | partial | 5.0 (2014) | Via MOST — contingency states modeled as separate network islands with probability weighting; no standalone `runCA()` function; users can script N-1 by iterating `runpf()`/`runopf()` with branch removals |
| Custom Constraint Injection | yes | 4.0 (2011) | MP-Opt-Model `add_lin_constraint()`, `add_nln_constraint()`, `add_quad_cost()`; 8.x Extension API allows adding custom variables, constraints, and costs to OPF via callback mechanism |
| Network Graph Access | yes | 3.x (~2006) | Bus-branch data directly accessible as matrices; `makeYbus()` for admittance matrix; `makeBdc()` for B matrices; `connected_components()` for topology analysis; no native graph object, but adjacency/incidence matrices are straightforward to construct |
| CSV Data Import | no | — | `loadcase()` supports only `.m` and `.mat` files natively; CSV requires custom parsing scripts; third-party `matpowercaseframes` (Python) can convert |
| MATPOWER Case Import | yes | 1.0 (1997) | `loadcase()` — supports `.m` (v1 and v2 formats) and `.mat` files; also imports PSS/E `.raw` files via `psse2mpc()` |
| Multi-Period / Time Series | partial | 5.0 (2014) | Via MOST — multi-period DC OPF with ramping constraints, storage, deferrable demands; no built-in time-series AC OPF; each period uses DC network model only |
| Warm Start / Solution Reuse | partial | 7.0 (2019) | `opf.start` option can initialize from a solved case (`mpc.bus(:,VM)`, `mpc.gen(:,PG)` etc.); MIPS 1.5+ supports LU factorization reuse; no formal warm-start API — user manually passes previous solution as starting point |
| Parallel Computation | no | — | No built-in parallel support; MATLAB users can wrap calls in `parfor` (requires Parallel Computing Toolbox, known issues with MATPOWER globals); GNU Octave has limited parallel packages; no native MATPOWER parallelism |

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|----------------------|
| 8.0 | Major rewrite: MP-Core replaces legacy internals; new `run_pf()`, `run_cpf()`, `run_opf()` functions alongside legacy `runpf()`, `runopf()` | Legacy functions still work via backward-compatibility wrappers; evaluation scripts using legacy API are unaffected |
| 8.0 | Deprecated `opt_model` methods removed (`add_constraints`, `add_costs`, etc.) | Must use `add_lin_constraint()`, `add_nln_constraint()`, `add_quad_cost()` etc. |
| 8.0 | `opf.init_from_mpc` option removed | Use `opf.start` option instead |
| 8.0 | Requires MATLAB 9.1+ or Octave 6.2+ | Our devcontainer uses Octave 9.x — no issue |
| 8.1 | Legacy `opt_model` and `mp_idx_manager` classes superseded by `mp.opt_model` | Legacy classes retained for backward compatibility; no immediate breakage |

## Changelog Analysis

**8.0 (May 17, 2024):** Landmark release introducing MP-Core — a three-layer object-oriented architecture (data model, network model, mathematical model) with a task management layer. Added the "flexible framework" (`run_pf`, `run_opf`, `run_cpf`) alongside the legacy framework. Introduced Extension API for customization (new element types, formulations). Added QCQP support and HiGHS solver. Improved radial power flow robustness. Broke backward compatibility on deprecated `opt_model` methods and the `opf.init_from_mpc` option.

**8.1 (July 12, 2025):** Incremental release building on 8.0. Added three-phase conversion utility and prototype three-phase models (shunt, transformer). MP-Opt-Model 5.0 with redesigned optimization classes, quadratic constraint support, HiGHS integration for LP/QP/MILP, and `relax_integer` option. New case files (`case1197`, `case59`). PSS/E ROP export. MOST updated to 1.3.1. Bug fixes for Knitro 15.x and Octave compatibility.

No breaking changes between 8.0 and 8.1 that affect this evaluation. Since 8.1 is both installed and latest, there is no version gap.

## Sources

1. [MATPOWER All Releases](https://matpower.org/download/all-releases/) — full version history and release dates
2. [MATPOWER 8.1 Launch Announcement](https://matpower.org/matpower-8-1-launch/) — 8.1 feature summary
3. [MATPOWER 8.0 Release Announcement](https://matpower.org/2024/05/17/matpower-8-0-released/) — MP-Core architecture overview
4. [What's New in MATPOWER 8](https://matpower.org/whats-new-in-matpower-8/) — detailed 8.0 feature descriptions
5. [MATPOWER CHANGES.md](https://github.com/MATPOWER/matpower/blob/master/CHANGES.md) — detailed changelog
6. [MATPOWER Reference Manual 8.1](https://matpower.org/doc/_downloads/13f33e22ecbbad1ede2ee92dbf7e51ac/matpower_ref_manual.pdf) — function reference
7. [MATPOWER User's Manual 8.1](https://matpower.org/docs/MATPOWER-manual.pdf) — user guide
8. [MOST User's Manual 1.3.1](https://matpower.org/docs/MOST-manual.pdf) — MOST capabilities and API
9. [MOST GitHub README](https://github.com/MATPOWER/most/blob/master/README.md) — MOST overview
10. [makePTDF Documentation (8.1)](https://matpower.org/doc/ref-manual/legacy/functions/makePTDF.html) — PTDF function reference
11. [How to Add an OPF Constraint (8.1)](https://matpower.org/documentation/howto/add-constraint.html) — custom constraint injection guide
12. [MP-Opt-Model GitHub](https://github.com/MATPOWER/mp-opt-model) — optimization model package
13. [connected_components Documentation](https://matpower.org/docs/ref/matpower5.0/connected_components.html) — network topology analysis
14. [MATPOWER Data File Format](https://matpower.app/manual/matpower/DataFileFormat.html) — loadcase file format specification
15. [Linear Shift Factors](https://matpower.app/manual/matpower/LinearShiftFactors.html) — PTDF/LODF theory and usage

## Gaps and Uncertainties

- **SCUC/SCED "since version" attribution:** MOST was first bundled with MATPOWER 5.0 (2014), but earlier standalone versions of MOST existed. The "since 5.0" designation reflects when it became part of the standard MATPOWER distribution.
- **Warm start specifics:** MATPOWER does not have a formal warm-start API. The `opf.start` option and manual initialization from a previous solution provide partial warm-start capability, but solver-level warm start (e.g., passing dual variables) depends on the underlying solver (IPOPT, Knitro).
- **Parallel computation on Octave:** GNU Octave's `parallel` package exists but is not equivalent to MATLAB's Parallel Computing Toolbox. MATPOWER does not use or recommend it. Users who need parallelism must implement it externally.
- **MOST AC network model:** MOST's formulation is general and supports AC, but the current implementation (through 1.3.1) only supports DC power flow network constraints. This is a long-standing limitation.
- **CSV import:** No evidence of native CSV import was found in any MATPOWER version. The `.m` case file format is the canonical input format.
- **makePTDF origin version:** The function exists in MATPOWER 4.0 documentation (2011) and likely predates it. Attributed to "3.x (~2006)" based on copyright dates in source code, but exact introduction version is uncertain.

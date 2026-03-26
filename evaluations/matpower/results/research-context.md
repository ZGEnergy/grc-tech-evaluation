# MATPOWER — Combined Research Context

---

## Section 1: API & Formulations

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
| **MP-Opt-Model** | Optimization modeling framework; unified solver abstraction layer for LP/MILP/QP/MIQP/NLP/NLE problems; runtime `have_feature` detection | `qps_master()` (LP/QP dispatch), `miqps_master()` (MILP/MIQP dispatch), `nlps_master()` (NLP dispatch), `nleqs_master()` (nonlinear equations dispatch), plus per-solver wrappers: `qps_glpk`, `qps_gurobi`, `qps_highs`, `qps_cplex`, `qps_mosek`, `qps_osqp`, `qps_clp`, `qps_ipopt`, `qps_knitro`, `miqps_glpk`, `miqps_gurobi`, `miqps_highs`, `miqps_cplex`, `miqps_mosek`, `nlps_ipopt`, `nlps_fmincon`, `nlps_knitro` |
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
- **MATPOWER Reference Manual (8.1):** https://matpower.org/documentation/ref-manual/legacy/functions/runpf.html (and sibling pages for `runopf`, `rundcopf`, `runcpf`, `caseformat`, `mpoption`)
- **MATPOWER Reference Manual index:** https://matpower.org/doc/ref-manual/
- **Case format spec:** https://matpower.org/documentation/ref-manual/legacy/functions/caseformat.html
- **MP-Opt-Model GitHub:** https://github.com/MATPOWER/mp-opt-model
- **MOST GitHub:** https://github.com/MATPOWER/most
- **Primary citation:** R. D. Zimmerman, C. E. Murillo-Sanchez, R. J. Thomas, "MATPOWER: Steady-State Operations, Planning and Analysis Tools for Power Systems Research and Education," IEEE Trans. Power Syst., vol. 26, no. 1, pp. 12-19, Feb. 2011. DOI: 10.1109/TPWRS.2010.2051168
- **MATPOWER 8.1 DOI:** 10.5281/zenodo.15871662
- **Docs directory:** `evaluations/matpower/matpower8.1/docs/` -- MATPOWER-manual.pdf, TN1-TN5, MATPOWER-dev-guide.md
- **MOST manual:** `evaluations/matpower/matpower8.1/most/docs/MOST-manual.pdf`
- **MP-Opt-Model manual:** `evaluations/matpower/matpower8.1/mp-opt-model/docs/MP-Opt-Model-manual.pdf`
- **MIPS manual:** `evaluations/matpower/matpower8.1/mips/docs/MIPS-manual.pdf`
- **Install findings:** `evaluations/matpower/notes/install-findings.md`

## Gaps and Open Questions

1. **No programmatic JSON/CSV/DataFrame export.** Results are returned as MATLAB structs with numeric matrices. There is no built-in way to export results to JSON, CSV, or any format consumable by non-MATLAB tools without writing custom serialization code.

2. **New flexible framework documentation is incomplete.** The Sphinx-based reference manual for the new `run_pf`/`run_opf` framework states "the new web-based version of the User's Manual is not yet available" and refers users to the legacy PDF manual. The MP-Core class hierarchy is documented in the developer manual but not yet in a user-facing guide.

3. **Three-phase / unbalanced power flow is present but undocumented.** The MP-Core `+mp/` namespace contains extensive three-phase element classes (`dme_bus3p`, `dme_gen3p`, `dme_line3p`, `dme_load3p`, `dme_shunt3p`, `dme_xfmr3p` with corresponding network model, math model, and converter classes -- ~39 files total). There is also an `xt_3p` extension class and a `convert_1p_to_3p_ex1.mlx` example. However, no user-facing documentation, manual section, or function-header examples were found for this feature in 8.1. It appears to be a new capability in the flexible framework without a legacy API equivalent.

4. **MOST documentation.** The MOST sub-package has its own PDF manual at `most/docs/MOST-manual.pdf`. The `mdi` input struct for `most()` is complex and not fully documented in function headers -- the manual is required. MOST's network modeling is limited to DC power flow; the general formulation supports AC but the current implementation does not.

5. **No native Python/Julia bindings.** MATPOWER is MATLAB/Octave only. Third-party wrappers exist (e.g., `matpower` PyPI package uses Oct2Py bridge) but are not part of the official distribution.

6. **Solver availability in Octave.** Several solver interfaces (FMINCON, CPLEX, GUROBI, KNITRO, MOSEK) require MATLAB toolboxes or commercial licenses. In Octave, the available solvers are typically limited to MIPS (built-in), IPOPT, GLPK, and OSQP. The `have_feature` system detects what is available at runtime.

---

## Section 2: Extensions & Architecture

# MATPOWER -- Research: Extensions & Architecture

## Key Findings

- MATPOWER 8 introduced a major object-oriented rewrite (MP-Core) with a three-layer architecture: Data Model, Network Model, and Mathematical Model, each decoupled via element containers and converter services.
- The `mp.extension` API provides nine override points (5 container-class constructors + 4 element-class modifier lists) enabling users to add, remove, or replace element types at every layer without modifying core code.
- Legacy callback API (`add_userfcn`) supports five stages (`ext2int`, `formulation`, `int2ext`, `printpf`, `savecase`) for injecting custom variables, constraints, and costs into OPF problems.
- The Continuation Power Flow (CPF) has its own event/callback system (`cpf_register_event`, `cpf_register_callback`) with priority-based ordering, enabling user-defined termination criteria and solution monitoring.
- Custom nonlinear OPF constraints can be added via `mm.add_nln_constraint()` (with user-supplied function, Jacobian, and Hessian), or by subclassing math model element classes and deploying them through the extension API.
- Graph/topology analysis is supported natively: `makeYbus` (admittance matrix), `connected_components` (BFS traversal on incidence matrix), `find_islands`, `extract_islands`, `find_bridges` (Tarjan's algorithm), `makePTDF`, `makeLODF`, and `order_radial`.
- No native DataFrame, NetworkX, or CSV export exists within MATPOWER itself; interoperability requires external bridges: `matpower-pip` + `oct2py` for Python/Octave integration, `matpowercaseframes` for pandas DataFrame parsing, and `pandapower` for bidirectional MATPOWER case conversion.
- MOST (MATPOWER Optimal Scheduling Tool) extends MATPOWER to multiperiod, stochastic, security-constrained unit commitment and OPF with storage, ramping, and reserves.
- The `extras/` directory ships community-contributed packages: state estimation, SDP-OPF, network reduction, synthetic grid generation, and maximum loadability limits -- each using the userfcn callback or standalone function patterns.
- Data structures are MATLAB/Octave structs and numeric matrices (the `mpc` case struct), with a newer `mp_table` class providing basic named-column table access compatible with Octave.

## Detailed Notes

### Three-Layer Architecture (MP-Core, MATPOWER 8+)

MATPOWER 8 replaced the legacy monolithic codebase with a layered, object-oriented architecture called MP-Core. The three layers are:

1. **Data Model (`mp.data_model`)** -- Encapsulates user-visible parameters (bus, gen, branch, load, shunt data). Element data is stored in table objects (`dme.tab`). A data model converter (`mp.dm_converter`) decouples the data model from specific file formats (MATPOWER case struct v2, PSS/E RAW, IEEE CDF).

2. **Network Model (`mp.net_model`)** -- Defines nodes, ports, states, and the relationships between them. Builds the admittance matrix (Ybus) and related network parameters from data model elements. Formulation-specific subclasses exist for DC (`mp.net_model_dc`), AC polar (`mp.net_model_acp`), and AC cartesian (`mp.net_model_acc`).

3. **Mathematical Model (`mp.math_model`)** -- Inherits from `opt_model` (MP-Opt-Model). Formulates the actual optimization or simulation problem: variables, constraints, objective function. Task-specific and formulation-specific subclasses (e.g., `mp.math_model_opf_acps` for AC polar power OPF).

A **Task** object (`mp.task`) orchestrates the workflow: it creates the data model converter, builds the three models in sequence, solves the math model, and propagates solutions back through the layers. Task subclasses exist for PF (`mp.task_pf`), CPF (`mp.task_cpf`), and OPF (`mp.task_opf`).

Each layer is organized as an **element container** (`mp.element_container`), holding typed element objects in a `mp.mapped_array` accessible by both name and index.

**Sources:**
- [Architecture Overview (MATPOWER Dev Manual)](https://matpower.org/documentation/dev-manual/architecture.html)
- `/workspace/evaluations/matpower/matpower8.1/lib/+mp/task.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/+mp/data_model.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/+mp/net_model.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/+mp/math_model.m`

### Extension API (`mp.extension`)

The `mp.extension` abstract base class defines nine virtual methods that an extension can override:

**Container-class constructors** (return a function handle to replace the default constructor):
- `task_class(task_class, mpopt)` -- override the task object
- `dm_converter_class(dmc_class, fmt, mpopt)` -- override the data model converter
- `data_model_class(dm_class, task_tag, mpopt)` -- override the data model
- `network_model_class(nm_class, task_tag, mpopt)` -- override the network model
- `math_model_class(mm_class, task_tag, mpopt)` -- override the math model

**Element-class modifiers** (return a cell array of modifications):
- `dmc_element_classes(dmc_class, fmt, mpopt)`
- `dm_element_classes(dm_class, task_tag, mpopt)`
- `nm_element_classes(nm_class, task_tag, mpopt)`
- `mm_element_classes(mm_class, task_tag, mpopt)`

Element class modifiers use three operations:
| Operation | Syntax | Effect |
|-----------|--------|--------|
| Append | `@new_class` | Adds a new element type |
| Remove | `'old_class'` (string) | Removes elements where `isa(E(), 'old_class')` is true |
| Replace | `{@new_class, 'old_class'}` | Replaces matching elements |

Extensions are passed to `run_mp`/`run_opf`/`run_pf` via the `'mpx'` named argument:
```matlab
task = run_opf('case9', mpopt, 'mpx', mp.xt_reserves);
```

Multiple extensions can be composed as a cell array:
```matlab
task = run_opf('case9', mpopt, 'mpx', {mp.xt_reserves, mp.xt_3p});
```

**Shipped extensions:**
- `mp.xt_reserves` -- Co-optimization of fixed zonal reserves in OPF. Adds `reserve_gen` and `reserve_zone` elements to data model converter, data model, and math model.
- `mp.xt_3p` -- Prototype unbalanced three-phase element support (`bus3p`, `gen3p`, `load3p`, `line3p`, `xfmr3p`, `shunt3p`, `buslink`) for AC PF, CPF, and OPF.

**Sources:**
- `/workspace/evaluations/matpower/matpower8.1/lib/+mp/extension.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/+mp/xt_reserves.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/+mp/xt_3p.m`
- [Customizing MATPOWER (Dev Manual)](https://matpower.org/documentation/dev-manual/customizing.html)
- [mp.extension reference](https://matpower.org/documentation/ref-manual/classes/mp/extension.html)

### Legacy Callback / Userfcn API

The pre-MATPOWER-8 extension mechanism, still supported, uses `add_userfcn(mpc, stage, fcn, args)` to register callbacks at five stages:

1. **`ext2int`** -- Called after external-to-internal index conversion. Used to reorder custom data.
2. **`formulation`** -- Called after the OPF model (OM) is initialized but before the solver. This is where custom variables, constraints, and costs are added to the `opt_model`.
3. **`int2ext`** -- Called before converting results back to external indexing. Used to extract custom results.
4. **`printpf`** -- Called after standard pretty-printing. Used for custom output.
5. **`savecase`** -- Called when saving case to file. Used to write custom fields.

Built-in toggle functions use this pattern:
- `toggle_reserves(mpc, 'on')` -- fixed zonal reserve requirements
- `toggle_iflims(mpc, 'on')` -- interface flow limits (DC model)
- `toggle_softlims(mpc, 'on')` -- relaxed OPF inequality constraints (VMIN, VMAX, RATE_A, PMIN, PMAX, QMIN, QMAX, ANGMIN, ANGMAX) with user-specified violation costs
- `toggle_dcline(mpc, 'on')` -- DC transmission line modeling

**Sources:**
- `/workspace/evaluations/matpower/matpower8.1/lib/add_userfcn.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/toggle_reserves.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/toggle_softlims.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/toggle_iflims.m`

### Custom OPF Constraints

Two approaches are documented for adding custom constraints:

**Approach 1: Legacy direct specification.** The `mpc` struct can contain fields `A`, `l`, `u` for linear constraints (A * x >= l, A * x <= u), and `N`, `H`, `Cw`, `fparm` for generalized costs.

**Approach 2: Extension/element subclass (MATPOWER 8+).** Subclass a math model element (e.g., `mp.mme_gen_opf_ac`) and override `add_constraints()` to call `mm.add_nln_constraint(name, N, iseq, fcn, hess, varsets)`. The constraint function must return the constraint vector and Jacobian; the Hessian function returns second derivatives. Deploy via `mpopt.exp.mm_element_classes` or through an `mp.extension` subclass.

The `add_nln_constraint` method on `opt_model` accepts:
- `name` -- constraint set name
- `N` -- number of constraints
- `iseq` -- 1 for equality, 0 for inequality
- `fcn` -- function handle returning `[g, dg]` (constraint values and Jacobian)
- `hess` -- function handle returning `d2g` (Hessian of Lagrangian)
- `varsets` -- cell array of variable set names (e.g., `{'Pg', 'Qg'}`)

**Sources:**
- [How to Add an OPF Constraint](https://matpower.org/documentation/howto/add-constraint.html)
- [Extending the OPF](https://matpower.app/manual/matpower/ExtendingtheOPF.html)
- `/workspace/evaluations/matpower/matpower8.1/mp-opt-model/lib/@opt_model/add_nln_constraint.m`

### CPF Event and Callback System

The Continuation Power Flow has a separate extensibility mechanism:

**Events** (`cpf_register_event`): Register functions that return a scalar/vector value; when the value crosses zero, an event is detected. Built-in events:
- `cpf_nose_event` -- nose point detection (priority 51)
- `cpf_vlim_event` -- voltage limit violations (priority 52)
- `cpf_flim_event` -- flow limit violations (priority 53)
- `cpf_target_lam_event` -- target loading parameter reached (priority 50)
- `cpf_qlim_event` -- reactive power limit (priority 41)
- `cpf_plim_event` -- active power limit (priority 40)

**Callbacks** (`cpf_register_callback`): Registered with a priority (higher runs first). The callback receives current, next, and previous states, and can modify the step, request rollback, or signal termination. User callbacks are specified via `mpopt.cpf.user_callback`.

**Sources:**
- `/workspace/evaluations/matpower/matpower8.1/lib/cpf_register_callback.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/cpf_register_event.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/cpf_default_callback.m`

### Graph and Topology Access

MATPOWER provides several functions for network topology analysis, all operating on the `mpc` case struct or derived sparse matrices:

| Function | Description |
|----------|-------------|
| `makeYbus(mpc)` | Builds sparse bus admittance matrix `Ybus` and branch matrices `Yf`, `Yt` |
| `makePTDF(mpc, slack)` | DC Power Transfer Distribution Factor matrix (nbr x nb) |
| `makeLODF(mpc, PTDF)` | Line Outage Distribution Factor matrix (nbr x nbr) |
| `connected_components(C)` | BFS on node-branch incidence matrix; returns cell array of node groups |
| `find_islands(mpc)` | Finds connected islands in the network |
| `extract_islands(mpc, k)` | Extracts island k as a separate `mpc` struct |
| `find_bridges(mpc)` | Tarjan's algorithm for bridge detection |
| `order_radial(mpc)` | Oriented ordering for radial networks |
| `makeBdc(mpc)` | DC model B matrices |

The incidence matrix `C` is constructed from `mpc.branch(:, F_BUS)` and `mpc.branch(:, T_BUS)` columns. There is no built-in adjacency list or adjacency matrix function, but the sparse incidence matrix is trivially convertible. No native BFS/DFS/shortest-path API exists beyond `connected_components`.

**Sources:**
- `/workspace/evaluations/matpower/matpower8.1/lib/makeYbus.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/makePTDF.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/makeLODF.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/connected_components.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/find_islands.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/find_bridges.m`

### Interoperability and Data Export

MATPOWER's native data format is the `mpc` struct (MATLAB/Octave struct with numeric matrices for `bus`, `gen`, `branch`, `gencost`). Import/export support:

**Native formats:**
- MATPOWER case file (`.m` or `.mat`) -- `loadcase()` / `savecase()`
- PSS/E RAW -- `psse2mpc()` / `save2psse()`
- IEEE CDF -- `cdf2mpc()`

**No native CSV, JSON, or DataFrame export.** All data lives in MATLAB/Octave matrices and structs.

**Python bridges (third-party):**
- **[matpower-pip](https://pypi.org/project/matpower/)** (PyPI) -- Packages MATPOWER 8.1 for pip install. Uses `oct2py` to run Octave from Python. `matpower.start_instance()` returns an Octave session with MATPOWER on path.
- **[matpowercaseframes](https://pypi.org/project/matpowercaseframes/)** -- Pure-Python parser (regex-based, no Octave required) that converts `.m` case files into pandas DataFrames. Supports `to_excel()` export.
- **[pandapower](https://pandapower.readthedocs.io/en/latest/converter/matpower.html)** -- `from_mpc()` and `to_mpc()` converters between pandapower networks and MATPOWER case structs. Uses `matpowercaseframes` for `.m` file parsing.
- **[PYPOWER](https://github.com/rwl/PYPOWER)** -- Pure-Python port of MATPOWER 4.1 (very outdated, no active development).

**No native NetworkX integration.** The sparse admittance/incidence matrices from `makeYbus`/`connected_components` could be converted to NetworkX graphs via `scipy.sparse` + `networkx.from_scipy_sparse_array()`, but this requires manual bridging.

**Sources:**
- `/workspace/evaluations/matpower/matpower8.1/lib/savecase.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/save2psse.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/psse2mpc.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/cdf2mpc.m`
- [matpower-pip on PyPI](https://pypi.org/project/matpower/)
- [matpowercaseframes on PyPI](https://pypi.org/project/matpowercaseframes/)
- [pandapower MATPOWER converter](https://pandapower.readthedocs.io/en/latest/converter/matpower.html)
- [GitHub Issue #134: Run MATPOWER from Python](https://github.com/MATPOWER/matpower/issues/134)

### MOST (MATPOWER Optimal Scheduling Tool)

MOST extends MATPOWER to solve multiperiod, stochastic, contingency-constrained OPF with unit commitment. Key capabilities:
- Multiperiod scheduling with ramping constraints and costs
- Stochastic scenarios for load and renewable generation
- Security constraints (N-1 contingency)
- Lossy storage resources with terminal targets and cyclic constraints
- Deferrable/flexible demands
- Fixed zonal reserves (locational)
- Mixed-integer programming for unit commitment (min up/down times)

MOST uses the legacy framework (not MP-Core extensions). Input is an `mdi` (MOST Data Input) struct; output is `mdo` (MOST Data Output).

**Sources:**
- `/workspace/evaluations/matpower/matpower8.1/most/lib/most.m`
- [MOST User's Manual (PDF)](https://matpower.org/docs/MOST-manual.pdf)
- [MOST GitHub repository](https://github.com/MATPOWER/most)

### Extras / Community Extensions

The `extras/` directory ships with several contributed packages:

| Package | Description |
|---------|-------------|
| `se/` | State estimation (`run_se`, `doSE`, `isobservable`) |
| `sdp_pf/` | Semidefinite programming OPF solver (`runsdpopf`) |
| `syngrid/` | Synthetic grid generation |
| `reduction/` | Network reduction toolbox (Kron reduction, Ward equivalents) |
| `maxloadlim/` | Maximum loadability limit computation (uses userfcn callbacks) |
| `smartmarket/` | Auction/market clearing |
| `simulink_matpower/` | Simulink integration blocks |
| `state_estimator/` | Alternative state estimator |

These are not integrated via the `mp.extension` API; they use standalone functions or the legacy userfcn callback pattern.

**Source:** `/workspace/evaluations/matpower/matpower8.1/extras/`

### mp_table and Data Access in MP-Core

MATPOWER 8 introduced `mp_table`, a basic table class compatible with MATLAB's `table` but also working in Octave (which lacks native table support). In the MP-Core framework, data model elements store their data in `dme.tab` (an `mp_table` instance) with named columns:

```matlab
task = run_opf('case9');
lam_p = task.dm.elements.bus.tab.lam_p;   % nodal prices
pg = task.dm.elements.gen.tab.pg;          % generator dispatch
```

This provides named-column access similar to a DataFrame, though without filtering, grouping, or join operations.

**Sources:**
- `/workspace/evaluations/matpower/matpower8.1/lib/mp_table.m`
- `/workspace/evaluations/matpower/matpower8.1/lib/run_mp.m` (docstring examples)

## Sources

1. [MATPOWER Architecture Overview (Dev Manual)](https://matpower.org/documentation/dev-manual/architecture.html)
2. [Customizing MATPOWER (Dev Manual)](https://matpower.org/documentation/dev-manual/customizing.html)
3. [mp.extension reference](https://matpower.org/documentation/ref-manual/classes/mp/extension.html)
4. [How to Add an OPF Constraint](https://matpower.org/documentation/howto/add-constraint.html)
5. [Extending the OPF (User Manual)](https://matpower.app/manual/matpower/ExtendingtheOPF.html)
6. [Callback Stages and Example](https://matpower.app/manual/matpower/CallbackStagesandExample.html)
7. [MATPOWER 8.0 Release Notes](https://github.com/MATPOWER/matpower/blob/master/docs/relnotes/MATPOWER-Release-Notes-8.0.md)
8. [MP-Element GitHub (historical)](https://github.com/MATPOWER/mp-element)
9. [MOST GitHub](https://github.com/MATPOWER/most)
10. [MOST User's Manual (PDF)](https://matpower.org/docs/MOST-manual.pdf)
11. [matpower-pip on PyPI](https://pypi.org/project/matpower/)
12. [matpowercaseframes on PyPI](https://pypi.org/project/matpowercaseframes/)
13. [pandapower MATPOWER converter docs](https://pandapower.readthedocs.io/en/latest/converter/matpower.html)
14. [GitHub Issue #134: Run MATPOWER from Python](https://github.com/MATPOWER/matpower/issues/134)
15. [MATPOWER OPF Architecture slides (PSERC)](http://www.pserc.cornell.edu/matpower/MATPOWER-OPF-slides.pdf)
16. [MATPOWER User's Manual 8.1 (PDF)](https://matpower.org/docs/MATPOWER-manual.pdf)
17. Source files in `/workspace/evaluations/matpower/matpower8.1/lib/` (see individual section citations)

## Gaps and Uncertainties

- **MP-Core extension composition**: It is unclear how conflicts are resolved when multiple extensions modify the same element class (e.g., two extensions both replacing `mp.mme_gen_opf_ac`). The documentation does not describe priority or ordering rules for conflicting element class modifiers across extensions.
- **MOST and MP-Core integration**: MOST still uses the legacy framework and has not been ported to the MP-Core extension architecture. A [GitHub issue](https://github.com/MATPOWER/most/issues/8) requests user-defined variables/constraints/costs in MOST, which remains open.
- **No native CSV/JSON/DataFrame export**: All interoperability with Python/pandas requires third-party bridges. The quality and maintenance status of `matpowercaseframes` and `matpower-pip` should be independently verified.
- **NetworkX bridge**: No documented or maintained bridge exists between MATPOWER's sparse matrices and NetworkX graph objects. Manual conversion is straightforward but undocumented.
- **PYPOWER staleness**: PYPOWER is a port of MATPOWER 4.1 (circa 2011) and lacks all features from MATPOWER 5-8. It should not be considered a current interoperability path.
- **Three-phase support maturity**: The `mp.xt_3p` extension is described as a "prototype" in the source code. Its production readiness and completeness are uncertain.
- **Documentation gaps**: Technical Note 5 (TN5-MP-Element.pdf) provides mathematical details on the element model but is a dense PDF without web-searchable content. The dev manual's "How To" section returned 404 for the constraint guide at one URL path, suggesting documentation is still being reorganized.

---

## Section 3: Limitations & Ecosystem

---
tool: matpower
research_date: 2026-03-24
focus: Known limitations, open issues, ecosystem, community size, documentation quality, release history
version_evaluated: "8.1"
prior_research: 2026-03-13
---

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
| [MOST #50](https://github.com/MATPOWER/most/issues/50) — Downward reserve | most | Reserve requirements in UC | Open (since 2025-03) |
| [MOST #52](https://github.com/MATPOWER/most/issues/52) — Update to mp.opt_model | most | Internal refactoring to new API | Open (since 2025-06) |
| [#269](https://github.com/MATPOWER/matpower/issues/269) — Update to mp.opt_model | matpower | Internal refactoring to new API | Open (since 2025-06) |

## 3. Ecosystem Packages

MATPOWER's ecosystem is a set of modular packages maintained under the MATPOWER GitHub organization,
all by the same core team (primarily Ray Zimmerman at Cornell / PSERC).

| Package | Description | Version | Stars | Forks | License | Last Push |
|---------|-------------|---------|-------|-------|---------|-----------|
| [matpower](https://github.com/MATPOWER/matpower) | Core PF/OPF engine | 8.1 | 545 | 173 | BSD 3-Clause | 2026-03-11 |
| [most](https://github.com/MATPOWER/most) | Multi-period scheduling, UC, storage | 1.3.1 | 39 | — | BSD 3-Clause | 2026-02-16 |
| [mp-opt-model](https://github.com/MATPOWER/mp-opt-model) | Optimization modeling layer | 5.0 | 10 | — | BSD 3-Clause | 2025-12-11 |
| [mips](https://github.com/MATPOWER/mips) | Interior point solver | 1.5.2 | 16 | — | BSD 3-Clause | 2025-07-12 |
| [mptest](https://github.com/MATPOWER/mptest) | Unit testing framework | — | 1 | — | BSD 3-Clause | 2025-07-08 |
| [mp-element](https://github.com/MATPOWER/mp-element) | New element modeling layer (merged into matpower 8.0) | — | 4 | — | BSD 3-Clause | 2023-02-02 |

### Additional MATPOWER Organization Packages

| Package | Description | Stars | Last Push |
|---------|-------------|-------|-----------|
| [mx-se](https://github.com/MATPOWER/mx-se) | State estimation (contributed by Rui Bo) | 10 | 2024-05-14 |
| [mx-sdp_pf](https://github.com/MATPOWER/mx-sdp_pf) | SDP relaxation of power flow (Dan Molzahn) | 7 | 2024-05-14 |
| [mx-syngrid](https://github.com/MATPOWER/mx-syngrid) | Synthetic grid creation | 14 | 2024-05-21 |
| [mx-maxloadlim](https://github.com/MATPOWER/mx-maxloadlim) | OPF extension for max loadability limits | 1 | 2024-05-14 |
| [mx-reduction](https://github.com/MATPOWER/mx-reduction) | Network reduction toolbox | 0 | 2019-06-20 |
| [mx-simulink_matpower](https://github.com/MATPOWER/mx-simulink_matpower) | Simulink interface | 1 | 2024-05-14 |
| [mpsim](https://github.com/MATPOWER/mpsim) | Simulator framework | 4 | 2024-05-14 |
| [mpng](https://github.com/MATPOWER/mpng) | MATPOWER Natural Gas extension | 11 | 2023-09-13 |
| [wy-wind-model](https://github.com/MATPOWER/wy-wind-model) | Wind model for MOST | 1 | 2022-11-16 |
| [tpc-form](https://github.com/MATPOWER/tpc-form) | Approx PF in transformed polar coordinates | 0 | 2025-11-12 |
| [matpower-extras](https://github.com/MATPOWER/matpower-extras) | Contributed/unsupported code | 12 | 2025-07-13 |

### Third-Party Ecosystem

- **[matpower-pip](https://github.com/yasirroni/matpower-pip)** — Python wrapper via oct2py,
  installable via `pip install matpower[octave]`. Third-party, not evaluated.
- **SimulinkMATPOWER** — Simulink interface, included in MATPOWER Extras (requires MATLAB +
  Simulink). Not relevant for Octave-based evaluation.
- **matpowercaseframes** — Python package for reading/writing MATPOWER case files as DataFrames.
  Third-party, not evaluated.
- **GMLC-TDC/MATPOWER-wrapper** — HELICS co-simulation wrapper for transmission system
  simulation. Used for ISO-DSO co-simulation research.

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
| GitHub stars | 545 | 2026-03-24 |
| GitHub forks | 173 | 2026-03-24 |
| Contributors (GitHub) | 17 | 2026-03-24 |
| Open issues (non-PR) | 16 | 2026-03-24 |
| Closed issues (non-PR) | ~260 | 2026-03-24 (estimated from pagination) |
| Annual downloads | 22,000+ | per matpower.org/about (updated figure) |
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
  Scholar blocks scraping). The primary paper (Zimmerman et al., 2011, IEEE TPWRS) has a
  Zenodo DOI (10.5281/zenodo.3236535) for version-neutral citation.
- **Download count discrepancy:** matpower.org/about states "more than 22,000 times per year"
  (as of 2026-03-24 fetch). A prior version of the site stated 40,000+. The lower figure may
  reflect a change in counting methodology or the current accurate number.
- **MOST Pro feature set:** Only one feature (DC transmission lines) is documented in the 8.1
  release notes. Full MOST Pro capabilities are unknown without contacting info@matpower.org.
- **Octave performance baseline:** No published benchmarks comparing MATPOWER performance on
  Octave vs. MATLAB. Anecdotal reports suggest 2-5x slower on Octave for large problems.
  pandapower's benchmarking paper (Thurner et al., 2018) found pandapower faster than MATPOWER
  on large networks (>1000 buses), but that comparison used PYPOWER (Python port), not MATPOWER
  on MATLAB directly.
- **Mailing list activity metrics:** The MATPOWER mailing list (MATPOWER-L at Cornell) is the
  primary support channel. Archive available at
  https://www.mail-archive.com/matpower-l@cornell.edu/. GitHub issue counts underrepresent
  community engagement. A developer list (MATPOWER-DEV-L) also exists.
- **RTE/utility deployment details:** matpower.org lists RTE as a user but no details on how
  MATPOWER is used in operational settings (research vs. production). No evidence found of
  MATPOWER in ISO/RTO production dispatch. Primary use case appears to be research and education.
- **Three-phase support maturity:** MATPOWER 8.1 added prototype three-phase conversion, shunt
  models, and off-nominal transformer taps. These are described as "prototype" — maturity and
  correctness for production use are unverified.
- **MATPOWER 8.x MP-Core adoption:** The 8.0 release introduced a completely rewritten
  object-oriented core (MP-Core) with a "flexible framework" alongside the "legacy framework."
  The User's Manual still primarily documents the legacy framework. Real-world adoption of the
  new flexible framework is unclear.
- **HiGHS solver integration:** MP-Opt-Model 5.0 (bundled with MATPOWER 8.1) added support for
  the open-source HiGHS solver for LP, QP, and MILP. This is notable as it provides a
  high-performance open-source alternative to commercial solvers for MILP (needed for UC in MOST).
- **QCQP support:** MP-Opt-Model 5.0 added quadratic constraints and QCQP solver support,
  expanding optimization modeling capabilities beyond LP/QP/NLP.

## Sources

1. [MATPOWER GitHub repository](https://github.com/MATPOWER/matpower) — stars, forks, issues, releases
2. [MOST GitHub repository](https://github.com/MATPOWER/most) — issues, releases, README
3. [MP-Opt-Model GitHub](https://github.com/MATPOWER/mp-opt-model) — metadata
4. [MIPS GitHub](https://github.com/MATPOWER/mips) — metadata
5. [MP-Test GitHub](https://github.com/MATPOWER/mptest) — metadata
6. [MP-Element GitHub](https://github.com/MATPOWER/mp-element) — metadata
7. [matpower.org](https://matpower.org) — download statistics, about page, documentation index
8. [matpower.org/about](https://matpower.org/about/) — capabilities, citation metrics, usage statistics (fetched 2026-03-24)
9. [matpower.org/license](https://matpower.org/license/) — licensing history (BSD 3-Clause since v5.1; GPL for v4.0-5.0)
10. [matpower.org/doc](https://matpower.org/doc/) — documentation index
11. [MATPOWER 8.1 release notes](https://github.com/MATPOWER/matpower/releases/tag/8.1)
12. [MATPOWER 8.0 release notes](https://github.com/MATPOWER/matpower/releases/tag/8.0)
13. [MATPOWER 8.1 launch page](https://matpower.org/matpower-8-1-launch/) — detailed feature list
14. [MOST issue #7 — Large models](https://github.com/MATPOWER/most/issues/7) — scalability limitation
15. [MOST issue #3 — AC multi-period](https://github.com/MATPOWER/most/issues/3) — AC OPF limitation
16. [MOST issue #50 — Downward reserve](https://github.com/MATPOWER/most/issues/50) — open since 2025-03
17. [MOST issue #52 — Update to mp.opt_model](https://github.com/MATPOWER/most/issues/52) — refactoring
18. [MATPOWER issue #134 — Python interop](https://github.com/MATPOWER/matpower/issues/134) — matpower-pip
19. [MATPOWER issue #136 — Distributed slack](https://github.com/MATPOWER/matpower/issues/136)
20. [MATPOWER issue #104 — Zonal reserves](https://github.com/MATPOWER/matpower/issues/104)
21. [MATPOWER issue #24 — Rate B/C in OPF](https://github.com/MATPOWER/matpower/issues/24)
22. [MATPOWER issue #279 — CPF stuck in loop](https://github.com/MATPOWER/matpower/issues/279) — open since 2025-12
23. [matpower.org/citing](https://matpower.org/citing/) — citation format and DOIs
24. [matpower.org/mailing-lists](https://matpower.org/mailing-lists/) — community channels
25. [MATPOWER-L archive](https://www.mail-archive.com/matpower-l@cornell.edu/) — mailing list archive
26. [MATPOWER User's Manual v8.1](https://matpower.org/docs/MATPOWER-manual.pdf)
27. [MATPOWER Reference Manual v8.1](https://matpower.org/doc/_downloads/13f33e22ecbbad1ede2ee92dbf7e51ac/matpower_ref_manual.pdf)
28. [NSF Award #1931421](https://www.nsf.gov/awardsearch/showAward?AWD_ID=1931421) — NSF funding for MATPOWER
29. [pandapower paper (Thurner et al., 2018)](https://arxiv.org/pdf/1709.06743) — performance comparison
30. [PyPSA comparable software](https://docs.pypsa.org/v0.19.1/comparable_software.html) — tool comparison
31. [GMLC-TDC/MATPOWER-wrapper](https://github.com/GMLC-TDC/MATPOWER-wrapper) — HELICS co-simulation
32. [MATPOWER GitHub LICENSE](https://github.com/MATPOWER/matpower/blob/master/LICENSE) — BSD 3-Clause + case file caveat

---

## Section 4: Version & Capability Report

---
tool: matpower
installed_version: "8.1"
release_date: 2025-07-12
latest_version: "8.1"
latest_release_date: 2025-07-12
research_date: 2026-03-24
---

# matpower — Version & Capability Report

## Version Summary

The evaluation environment installs MATPOWER 8.1, downloaded from the official GitHub release archive (`matpower8.1.zip`, SHA-256 verified) per `evaluations/matpower/setup.sh`. The `verify_install.m` script confirms the version string via `mpver()` and validates basic DC power flow on the IEEE 39-bus case. MATPOWER 8.1 was released on July 12, 2025, and is the latest stable release as of the research date.

MATPOWER 8.1 builds on the major architectural overhaul introduced in 8.0 (May 17, 2024), which replaced the legacy procedural internals with the object-oriented MP-Core framework. The 8.x line requires MATLAB 9.1+ or GNU Octave 6.2+ for MP-Core features; older environments fall back to legacy code paths. The evaluation devcontainer uses Octave, which is fully supported. Bundled sub-packages in 8.1 include MP-Opt-Model 5.0, MIPS 1.5.2, MP-Test 8.1, and MOST 1.3.1.

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes | 1.0 (1997) | `rundcpf()` / `run_pf()` with DC option. Core capability since initial release. |
| AC Power Flow (ACPF) | yes | 1.0 (1997) | `runpf()` / `run_pf()`. Newton-Raphson, fast-decoupled, Gauss-Seidel solvers. 8.0 added `fsolve()`-based and implicit Z-bus Gauss solvers for distribution systems. |
| DC Optimal Power Flow (DC OPF) | yes | 2.0 (1997) | `rundcopf()` / `run_opf()` with DC option. Supports piecewise-linear and polynomial cost functions. |
| AC Optimal Power Flow (AC OPF) | yes | 2.0 (1997) | `runopf()` / `run_opf()`. Interior-point (MIPS), fmincon, IPOPT, Knitro, and others via solver plugins. |
| Security-Constrained Unit Commitment (SCUC) | partial | 6.0 (2016, via MOST) | MOST solves multi-period stochastic security-constrained unit commitment with DC network constraints. AC network model formulated but current implementation limited to DC. Requires MOST sub-package (bundled as 1.3.1). |
| Security-Constrained Economic Dispatch (SCED) | partial | 6.0 (2016, via MOST) | MOST handles deterministic and stochastic economic dispatch with contingency constraints. DC-only network model in practice. Single-period ED also solvable via DC OPF with appropriate setup. |
| PTDF / Shift Factor Extraction | yes | 3.2 (2007) | `makePTDF()` builds DC PTDF matrix (nbr x nb). Supports scalar slack bus or slack distribution vector. 8.0 extended to per-bus slack distribution matrices. `makeLODF()` builds line outage distribution factors. Performance optimizations in 7.1 for large cases (70%+ speedup on pegase-9241). |
| Contingency Analysis (N-1) | partial | 3.2 (2007) | No built-in single-command N-1 screening. Users combine `makeLODF()` for fast linear screening or loop `runpf()`/`runopf()` over modified cases. `toggle_softlims` enables soft-limit relaxation for contingency-aware OPF. `connected_components()` detects islanding. |
| Custom Constraint Injection | yes | 4.0 (2011) | Legacy: `add_userfcn()` callback API adds variables, constraints, and costs to OPF formulation. 8.0+: MP-Core extension API and `mp.opt_model` class provide structured constraint injection. `toggle_softlims` is a built-in example of this pattern. |
| Network Graph Access | yes | 3.0 (2004) | `makeYbus()` (admittance), `makeBdc()` (DC B-matrices), `makeIncidence()` (bus-branch incidence), `connected_components()` (graph connectivity). Sparse Cf/Ct connection matrices available. No high-level graph object, but all adjacency/incidence data is extractable from bus/branch arrays. |
| CSV Data Import | no | — | MATPOWER natively loads `.m` (function files) and `.mat` (binary) case formats via `loadcase()`. No built-in CSV parser. Users must write custom Octave/MATLAB code to read CSV and populate the mpc struct. |
| MATPOWER Case Import | yes | 1.0 (1997) | Native format. `loadcase()` reads `.m` and `.mat` files in both version 1 (deprecated) and version 2 case formats. `savecase()` and `save2psse()` (PSS/E RAW export) also available. 8.1 adds `save2psse_rop()` for PSS/E ROP file export. |
| Multi-Period / Time Series | partial | 6.0 (2016, via MOST) | MOST provides multi-period optimal scheduling with ramping constraints, storage, deferrable demand, and stochastic scenarios. DC network model only. Core MATPOWER has no native time-series / multi-period power flow. |
| Warm Start / Solution Reuse | partial | 7.0 (2019) | `opf.start` option controls initialization (flat start, previous solution, etc.). MP-Opt-Model warm-start parameters passed to solvers when available. Effectiveness depends on the underlying solver (e.g., IPOPT, Knitro support warm starts natively). |
| Parallel Computation | no | — | No built-in parallel execution. Users can parallelize via Octave/MATLAB parallel toolboxes externally, but MATPOWER itself provides no parallel dispatch, multi-threaded solvers, or distributed computation API. |

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|----------------------|
| 8.0 | Removed deprecated functions `d2AIbr_dV2()`, `d2ASbr_dV2()` (replaced by `dA2br_dV2()`) | Low. Evaluation scripts unlikely to use second-derivative branch functions. |
| 8.0 | Removed deprecated `opf_model` methods (`add_constraints`, `add_costs`, `add_vars`, `build_cost_params`, `get_cost_params`, `getv`, `linear_constraints`) | Medium. Custom constraint tests must use the new `mp.opt_model` API or legacy `add_userfcn` callbacks. |
| 8.0 | Removed `opf.init_from_mpc` option; use `opf.start` | Low. Evaluation should use `opf.start` for warm-start tests. |
| 8.0 | Removed unused `mpopt` argument from `opf_gen_cost_fcn()` | Low. Only affects custom cost function code referencing old signature. |
| 8.0 | `loadcase()` with 5 outputs now returns `[baseMVA, bus, gen, branch, gencost]` instead of `[baseMVA, bus, gen, branch, info]` | Low. Evaluation scripts use struct output form (`mpc = loadcase(...)`). |
| 8.0 | MOST optimization failure no longer halts to debugger; adds `md.results.success` flag | Low-positive. Easier to detect MOST failures programmatically. |
| 8.0 | Requires Octave 6.2+ for MP-Core features | Low. Devcontainer provides a current Octave version. |
| 8.1 | R2025b `linprog` interior-point algorithm skipped in DC OPF tests due to failures | None. Octave does not use MATLAB's `linprog`. |

## Changelog Analysis

### Architecture (8.0)

The 8.0 release was a major rewrite. The new MP-Core introduces a three-layer architecture: data model (case data), network model (admittance/incidence matrices), and mathematical model (optimization formulation). Legacy functions (`runpf`, `runopf`, `rundcpf`, etc.) are retained and work via MP-Core internally, so existing scripts remain functional. New entry points `run_pf()`, `run_cpf()`, `run_opf()` expose the flexible framework with extension hooks.

### Solver Ecosystem (8.0-8.1)

8.0 added MP-Opt-Model 4.x with parameterized nonlinear equation solvers. 8.1 upgraded to MP-Opt-Model 5.0, adding QCQP support (Gurobi, Knitro, and NLP-based), the open-source HiGHS solver for LP/QP/MILP, and a `relax_integer` option for MILP/MIQP relaxation. Knitro 15.x and MOSEK 11.x compatibility were also added.

### Distribution System Modeling (8.0-8.1)

8.0 introduced an implicit Z-bus Gauss method for radial distribution systems and two real-world Swedish DSO test cases (case533mt). 8.1 added three-phase proof-of-concept capabilities (single-to-three-phase conversion, three-phase shunt and transformer models) and a 1197-bus radial distribution test case.

### Test Cases

8.0 added case60nordic (60-bus Nordic), case8387pegase (8387-bus PEGASE), and the Swedish DSO cases. 8.1 added case1197 (distribution), case59 (Australian network), and a Kundur 11-bus example.

### Bug Fixes (8.0-8.1)

Notable fixes include: fatal error in `int2ext()` with user callbacks (8.0), AC OPF initialization with piecewise-linear costs (8.0), radial power flow numerical errors with multiple generators (8.0), `save2psse()` fatal error with dispatchable loads (8.0/8.1), and Octave 10.x compatibility typos (8.1).

## Sources

1. [MATPOWER GitHub Releases](https://github.com/MATPOWER/matpower/releases) — version list and release notes
2. [MATPOWER All Releases](https://matpower.org/download/all-releases/) — complete release history with dates
3. [MATPOWER 8.0 Release Notes (GitHub)](https://github.com/MATPOWER/matpower/blob/master/docs/relnotes/MATPOWER-Release-Notes-8.0.md) — breaking changes and new features
4. [MATPOWER CHANGES.md (GitHub)](https://github.com/MATPOWER/matpower/blob/master/CHANGES.md) — detailed changelog
5. [MATPOWER Reference Manual 8.1 (PDF)](https://matpower.org/doc/_downloads/13f33e22ecbbad1ede2ee92dbf7e51ac/matpower_ref_manual.pdf) — function reference
6. [MATPOWER User's Manual 8.1 (PDF)](https://matpower.org/docs/MATPOWER-manual.pdf) — usage guide
7. [makePTDF documentation](https://matpower.org/doc/ref-manual/legacy/functions/makePTDF.html) — PTDF function reference
8. [makeLODF documentation](https://matpower.org/documentation/ref-manual/legacy/functions/makeLODF.html) — LODF function reference
9. [MOST GitHub README](https://github.com/MATPOWER/most/blob/master/README.md) — multi-period scheduling tool overview
10. [MOST User's Manual 1.3.1 (PDF)](https://matpower.org/docs/MOST-manual.pdf) — MOST capabilities and limitations
11. [MATPOWER Callback Functions](https://matpower.app/manual/matpower/CallbackFunctions.html) — custom constraint injection API
12. [Linear Shift Factors manual section](https://matpower.app/manual/matpower/LinearShiftFactors.html) — PTDF/LODF usage
13. [connected_components reference](https://matpower.org/docs/ref/matpower5.0/connected_components.html) — graph connectivity function
14. [toggle_softlims reference](https://matpower.org/docs/ref/matpower5.0/toggle_softlims.html) — soft limit extension for OPF
15. `evaluations/matpower/setup.sh` — installation script confirming version 8.1

## Gaps and Uncertainties

- **Exact "since version" for ACPF/DCPF solvers**: Power flow has been present since MATPOWER 1.0 (1997), but specific solver algorithms (e.g., fast-decoupled, Gauss-Seidel) were added incrementally. The version 1.0 attribution covers basic Newton-Raphson PF; detailed solver-by-solver provenance was not traced.
- **MOST DC-only limitation**: The MOST formulation supports AC network constraints in theory, but the implementation is DC-only. It is unclear whether a future release will add AC support or if this is a permanent architectural constraint.
- **SCOPF completeness**: MATPOWER does not include a turnkey SCOPF command. Users must construct SCOPF workflows using `makeLODF()`, `toggle_softlims`, and looped OPF calls. The "partial" rating for contingency analysis and SCUC/SCED reflects this user-assembly requirement.
- **Warm-start effectiveness**: The `opf.start` option and MP-Opt-Model warm-start parameters exist, but their practical effectiveness depends on the solver backend. No benchmarks were found for warm-start speedup in MATPOWER specifically.
- **Parallel computation**: While Octave supports `parfor` and `parcellfun`, MATPOWER itself does not expose parallel interfaces. It is unknown whether any internal operations use multithreaded BLAS/LAPACK via Octave's linear algebra backend.
- **CSV import**: Confirmed absent from native MATPOWER. Custom scripts are required. The third-party Python package `matpowercaseframes` can convert MATPOWER cases to/from pandas DataFrames, but this is outside the Octave evaluation scope.
- **MOST Pro**: A commercial extension (MOST Pro 1.4.1) adds features beyond the open-source MOST 1.3.1 bundled with MATPOWER 8.1. The capabilities of MOST Pro were not evaluated as it requires a paid license.

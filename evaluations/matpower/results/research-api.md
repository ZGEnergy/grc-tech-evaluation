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

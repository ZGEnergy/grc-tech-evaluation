# MATPOWER -- Research: API & Formulations

## Key Findings

- MATPOWER 8.1 provides two parallel APIs: a **legacy framework** (`runpf`, `runopf`, etc.) and a **new flexible OO framework** (`run_pf`, `run_opf`, etc.) built on a three-layer data/network/math model architecture (MP-Core).
- The data model is a flat MATLAB struct (`mpc`) with numeric matrices: `bus`, `branch`, `gen`, `gencost`, and optionally `dcline`. Column semantics are defined by index functions (`idx_bus`, `idx_brch`, `idx_gen`, `idx_cost`).
- Supported problem types: AC power flow (Newton variants, fast-decoupled, Gauss-Seidel, radial), DC power flow, continuation power flow, AC OPF, DC OPF, unit decommitment OPF, and via MOST: multiperiod stochastic security-constrained unit commitment.
- AC OPF supports multiple formulations: polar/cartesian voltage, power/current balance, apparent-power/active-power/current flow limits, and SDP relaxation.
- AC OPF solvers: MIPS (built-in), FMINCON, IPOPT, KNITRO, MINOPF, PDIPM, SDPOPF, TRALM. DC OPF solvers: MIPS, GUROBI, CPLEX, MOSEK, OSQP, GLPK, CLP, BPMPD, IPOPT, and MATLAB Optimization Toolbox.
- Network analysis utilities include `makePTDF`, `makeLODF`, `makeYbus`, `makeBdc`, `makeJac`, enabling direct computation of shift factors without re-solving.
- I/O supports native `.m` case files, `.mat` binary, PSS/E RAW import (`psse2mpc`) and export (`save2psse`), and IEEE CDF import (`cdf2mpc`).
- MATPOWER ships with 84 built-in test cases ranging from 4-bus to 13,659-bus (PEGASE) systems.
- MOST (bundled) adds multiperiod scheduling, stochastic scenarios, contingency constraints, unit commitment with min up/down times, storage, and ramping -- all as a DC MIQP formulation.
- MATPOWER does NOT have a native SCOPF function; security-constrained dispatch requires either MOST or manual contingency loop construction using PTDF/LODF.

## Detailed Notes

### Entry Points and Calling Conventions

**Legacy framework (backward-compatible):**

| Function | Purpose |
|----------|---------|
| `runpf(mpc, mpopt)` | AC power flow (Newton's method default) |
| `rundcpf(mpc, mpopt)` | DC power flow |
| `runopf(mpc, mpopt)` | AC optimal power flow |
| `rundcopf(mpc, mpopt)` | DC optimal power flow |
| `runuopf(mpc, mpopt)` | AC OPF with unit decommitment heuristic |
| `runduopf(mpc, mpopt)` | DC OPF with unit decommitment |
| `runcpf(mpcbase, mpctarget, mpopt)` | Continuation power flow (voltage stability) |
| `runopf_w_res(mpc, mpopt)` | OPF with fixed zonal reserves |
| `most(mdi, mpopt)` | Multiperiod stochastic UC/OPF |

All legacy functions accept the same pattern: `results = func(casedata, mpopt, fname, solvedcase)`. The `results` struct contains all input fields plus solved values and metadata (`success`, `et`, `order`, and for OPF: `f` objective value, dual variables in `mu_*` columns).

Source: [`runpf.m`](https://github.com/MATPOWER/matpower/blob/master/lib/runpf.m), [`runopf.m`](https://github.com/MATPOWER/matpower/blob/master/lib/runopf.m) (confirmed in local `/workspace/evaluations/matpower/matpower8.1/lib/`)

**New flexible framework (MATPOWER 8+):**

```matlab
task = run_pf('case9');
task = run_opf('case9', mpopt);
task = run_cpf(mpcbase, mpctarget, mpopt);
```

Returns a `task` object with `task.dm` (data model), `task.nm` (network model), `task.mm` (math model). Results accessed via: `task.dm.elements.bus.tab.va` for bus voltage angles, `task.dm.elements.gen.tab.pg` for generator dispatch.

Supports MATPOWER extensions via `'mpx'` argument for user-defined element types and formulations.

Source: [`run_pf.m`](https://github.com/MATPOWER/matpower/blob/master/lib/run_pf.m) (confirmed locally), [Architecture Overview](https://matpower.org/documentation/dev-manual/architecture.html)

### Data Model (MPC Struct)

The MATPOWER case format version 2 is a MATLAB struct (`mpc`) with:

- `mpc.version` -- string `'2'`
- `mpc.baseMVA` -- system MVA base (scalar)
- `mpc.bus` -- nb x 13+ matrix (input columns 1-13, output adds cols 14-17 for LMPs/duals)
- `mpc.branch` -- nbr x 13+ matrix (input columns 1-13, output adds cols 14-21 for flows/duals)
- `mpc.gen` -- ng x 21+ matrix (input columns 1-21, output adds cols 22-25 for duals)
- `mpc.gencost` -- ng (or 2*ng) x (5+N) matrix for cost curves
- `mpc.dcline` -- (optional) ndc x 17+ matrix for DC transmission lines

**Bus columns (mpc.bus):**

| Col | Constant | Description | Units |
|-----|----------|-------------|-------|
| 1 | `BUS_I` | Bus number | integer |
| 2 | `BUS_TYPE` | 1=PQ, 2=PV, 3=ref, 4=isolated | enum |
| 3 | `PD` | Real power demand | MW |
| 4 | `QD` | Reactive power demand | MVAr |
| 5 | `GS` | Shunt conductance (at V=1.0) | MW |
| 6 | `BS` | Shunt susceptance (at V=1.0) | MVAr |
| 7 | `BUS_AREA` | Area number | integer |
| 8 | `VM` | Voltage magnitude | p.u. |
| 9 | `VA` | Voltage angle | degrees |
| 10 | `BASE_KV` | Base voltage | kV |
| 11 | `ZONE` | Loss zone | integer |
| 12 | `VMAX` | Max voltage magnitude | p.u. |
| 13 | `VMIN` | Min voltage magnitude | p.u. |
| 14 | `LAM_P` | LMP for real power (OPF output) | $/MW |
| 15 | `LAM_Q` | LMP for reactive power (OPF output) | $/MVAr |
| 16 | `MU_VMAX` | Upper voltage bound dual (OPF output) | $/p.u. |
| 17 | `MU_VMIN` | Lower voltage bound dual (OPF output) | $/p.u. |

**Branch columns (mpc.branch):**

| Col | Constant | Description | Units |
|-----|----------|-------------|-------|
| 1 | `F_BUS` | From bus | integer |
| 2 | `T_BUS` | To bus | integer |
| 3 | `BR_R` | Resistance | p.u. |
| 4 | `BR_X` | Reactance | p.u. |
| 5 | `BR_B` | Line charging susceptance | p.u. |
| 6 | `RATE_A` | Long-term rating (0=unlimited) | MVA |
| 7 | `RATE_B` | Short-term rating | MVA |
| 8 | `RATE_C` | Emergency rating | MVA |
| 9 | `TAP` | Transformer tap ratio (0=line) | p.u. |
| 10 | `SHIFT` | Phase shift angle | degrees |
| 11 | `BR_STATUS` | 1=in-service, 0=out | binary |
| 12 | `ANGMIN` | Min angle difference | degrees |
| 13 | `ANGMAX` | Max angle difference | degrees |
| 14-17 | `PF,QF,PT,QT` | Power flows (output) | MW/MVAr |
| 18-21 | `MU_SF,MU_ST,MU_ANGMIN,MU_ANGMAX` | Duals (OPF output) | |

**Generator columns (mpc.gen):**

| Col | Constant | Description | Units |
|-----|----------|-------------|-------|
| 1 | `GEN_BUS` | Bus number | integer |
| 2 | `PG` | Real power output | MW |
| 3 | `QG` | Reactive power output | MVAr |
| 4 | `QMAX` | Max reactive power | MVAr |
| 5 | `QMIN` | Min reactive power | MVAr |
| 6 | `VG` | Voltage setpoint | p.u. |
| 7 | `MBASE` | Machine MVA base | MVA |
| 8 | `GEN_STATUS` | >0=on, <=0=off | |
| 9 | `PMAX` | Max real power | MW |
| 10 | `PMIN` | Min real power | MW |
| 11-16 | `PC1,PC2,QC1MIN,...` | PQ capability curve | MW/MVAr |
| 17 | `RAMP_AGC` | AGC ramp rate | MW/min |
| 18 | `RAMP_10` | 10-min ramp rate | MW |
| 19 | `RAMP_30` | 30-min ramp rate | MW |
| 20 | `RAMP_Q` | Reactive ramp rate | MVAr/min |
| 21 | `APF` | Area participation factor | |
| 22-25 | `MU_PMAX,...` | Duals (OPF output) | |

**Generator cost (mpc.gencost):**

| Col | Constant | Description |
|-----|----------|-------------|
| 1 | `MODEL` | 1=piecewise linear, 2=polynomial |
| 2 | `STARTUP` | Startup cost ($) |
| 3 | `SHUTDOWN` | Shutdown cost ($) |
| 4 | `NCOST` | Number of data points/coefficients |
| 5+ | `COST` | Cost parameters (see below) |

- Polynomial (MODEL=2): `c_n, ..., c_1, c_0` for `f(p) = c_n*p^n + ... + c_0`
- Piecewise linear (MODEL=1): `p_1, f_1, p_2, f_2, ...` breakpoint pairs

If `gencost` has 2*ng rows, rows ng+1:2*ng define reactive power costs.

Named column constants are accessed via `idx_bus`, `idx_brch`, `idx_gen`, `idx_cost`, or `define_constants` which loads all at once.

Source: [Data File Format](https://matpower.app/manual/matpower/DataFileFormat.html), [caseformat](https://matpower.org/documentation/ref-manual/legacy/functions/caseformat.html)

### Solver Interfaces

**Power flow algorithms** (`pf.alg` option):

| Algorithm | Key | Notes |
|-----------|-----|-------|
| Newton-Raphson (power, polar) | `NR` or `NR-SP` | Default |
| Newton (power, cartesian) | `NR-SC` | |
| Newton (power, hybrid) | `NR-SH` | |
| Newton (current, polar) | `NR-IP` | |
| Newton (current, cartesian) | `NR-IC` | |
| Newton (current, hybrid) | `NR-IH` | |
| Fast-Decoupled XB | `FDXB` | |
| Fast-Decoupled BX | `FDBX` | |
| Gauss-Seidel | `GS` | |
| Implicit Z-bus Gauss | `ZG` | |
| Power summation (radial) | `PQSUM` | Distribution networks only |
| Current summation (radial) | `ISUM` | Distribution networks only |
| Admittance summation (radial) | `YSUM` | Distribution networks only |

**AC OPF solvers** (`opf.ac.solver`):

| Solver | Built-in? | Notes |
|--------|-----------|-------|
| MIPS | Yes | Default; pure MATLAB/Octave interior point |
| FMINCON | No | Requires MATLAB Optimization Toolbox |
| IPOPT | No | Requires MEX interface to COIN-OR Ipopt |
| KNITRO | No | Requires Artelys Knitro license |
| MINOPF | No | MINOS-based, PSERC package |
| PDIPM | No | Requires TSPOPF package |
| SDPOPF | No | SDP relaxation; requires YALMIP + SDP solver |
| TRALM | No | Trust-region augmented Lagrangian; requires TSPOPF |

**DC OPF solvers** (`opf.dc.solver`):

| Solver | Built-in? | Notes |
|--------|-----------|-------|
| MIPS | Yes | Fallback default |
| GUROBI | No | Preferred when available |
| CPLEX | No | IBM CPLEX |
| MOSEK | No | |
| OSQP | No | Open-source QP solver |
| OT | No | MATLAB `quadprog`/`linprog` |
| GLPK | No | Linear costs only |
| CLP | No | COIN-OR LP solver |
| BPMPD | No | PSERC package |
| IPOPT | No | COIN-OR NLP solver |

Default DC OPF solver selection order: GUROBI > CPLEX > MOSEK > OT > GLPK > BPMPD > MIPS.

Source: [`mpoption.m`](https://github.com/MATPOWER/matpower/blob/master/lib/mpoption.m) (confirmed locally at `/workspace/evaluations/matpower/matpower8.1/lib/mpoption.m`)

### OPF Formulation Options

| Option | Values | Default | Effect |
|--------|--------|---------|--------|
| `opf.current_balance` | 0, 1 | 0 | Power vs. current balance equations |
| `opf.v_cartesian` | 0, 1 | 0 | Polar vs. cartesian voltage representation |
| `opf.flow_lim` | `'S'`, `'P'`, `'2'`, `'I'` | `'S'` | Branch flow constraint type |
| `opf.use_vg` | 0-1 | 0 | Use generator voltage setpoint vs bus limits |
| `opf.ignore_angle_lim` | 0, 1 | 0 | Ignore branch angle difference limits |
| `opf.start` | 0-3 | 0 | Starting point strategy |
| `model` | `'AC'`, `'DC'` | `'AC'` | AC vs DC formulation |

Source: [`mpoption.m`](https://github.com/MATPOWER/matpower/blob/master/lib/mpoption.m), [MATPOWER Options](https://matpower.app/manual/matpower/matpowerOptions.html)

### Network Analysis Utilities

| Function | Returns | Dimensions |
|----------|---------|------------|
| `makeYbus(mpc)` | Bus admittance matrix (Ybus), branch admittance matrices (Yf, Yt) | nb x nb, nbr x nb |
| `makeBdc(mpc)` | DC B matrices (Bbus, Bf) and injection vectors (Pbusinj, Pfinj) | nb x nb, nbr x nb |
| `makePTDF(mpc, slack)` | DC power transfer distribution factors | nbr x nb |
| `makeLODF(mpc, PTDF)` | Line outage distribution factors | nbr x nbr |
| `makeJac(mpc)` | Power flow Jacobian matrix | 2(nb-1) x 2(nb-1) |
| `makeB(mpc)` | Fast-decoupled PF B-prime matrices | nb x nb |
| `makeSbus(baseMVA, bus, gen)` | Complex bus power injection vector | nb x 1 |

`makePTDF` supports distributed slack via weight vector argument. All require internal bus ordering (consecutive from 1); use `ext2int(mpc)` to convert first.

Source: [makePTDF docs](https://matpower.org/documentation/ref-manual/legacy/functions/makePTDF.html), [makeLODF docs](https://matpower.org/documentation/ref-manual/legacy/functions/makeLODF.html), [System Matrices](https://matpower.app/manual/matpower/FormingStandardPowerSystemsMatrices.html)

### Input/Output Formats

| Function | Direction | Format |
|----------|-----------|--------|
| `loadcase(file)` | Import | MATPOWER `.m` or `.mat` files |
| `savecase(file, mpc)` | Export | MATPOWER `.m` or `.mat` files |
| `psse2mpc(file)` | Import | PSS/E RAW format |
| `save2psse(file, mpc)` | Export | PSS/E RAW format |
| `cdf2mpc(file)` | Import | IEEE Common Data Format |

PSS/E import reads: bus, branch, fixed shunt, generator, transformer, switched shunt, area, and HVDC line data. CDF import lacks OPF data (voltage limits, gen limits, costs) -- these are synthesized with defaults.

Source: [I/O Functions](https://matpower.app/manual/matpower/InputOutputFunctions.html), [save2psse](https://matpower.org/docs/ref/matpower7.1/lib/save2psse.html), [psse2mpc](https://matpower.org/docs/ref/matpower5.0/psse2mpc.html)

### MOST (Multiperiod Stochastic UC/OPF)

MOST (`most(mdi, mpopt)`) solves multiperiod, stochastic, contingency-constrained optimal power flow with optional unit commitment. It formulates the problem as a mixed-integer quadratic program (MIQP) using DC power flow constraints.

**Capabilities (combinable):**
- Single-period or multiperiod scheduling
- Deterministic or stochastic (scenario-based with probabilities)
- With or without contingency (security) constraints
- With or without unit commitment (binary variables, min up/down times)
- Fixed zonal reserves
- Storage resources (with terminal targets or cyclic constraints)
- Ramping costs and constraints
- Deferrable (curtailable) demands

**Key options:**
- `most.dc_model` -- use DC network model (1) vs simple P-balance (0)
- `most.security_constraints` -- include contingency constraints (-1=if present, 0=never, 1=always)
- `most.uc.run` -- perform unit commitment (-1=auto, 0=no, 1=yes)
- `most.uc.cyclic` -- wrap commitment constraints around horizon
- `most.storage.cyclic` -- initial storage = final expected storage
- `most.solver` -- underlying QP/MIQP solver selection

Input is a MOST data struct (`mdi`) built via helper functions; output (`mdo`) contains solved dispatch, prices, and commitment schedules.

Source: [MOST GitHub](https://github.com/MATPOWER/most), [MOST Manual (PDF)](https://matpower.org/docs/MOST-manual.pdf), local `/workspace/evaluations/matpower/matpower8.1/most/lib/most.m`

### Extension Mechanisms

MATPOWER provides four built-in toggle-based extensions and a general extension API:

| Extension | Toggle Function | Purpose |
|-----------|----------------|---------|
| Fixed Zonal Reserves | `toggle_reserves` | Co-optimize energy and reserves |
| Interface Flow Limits | `toggle_iflims` | Aggregate flow limits across interfaces |
| DC Transmission Lines | `toggle_dcline` | Model HVDC lines as linked generators |
| OPF Soft Limits | `toggle_softlims` | Relaxable constraints with penalty costs |

The new flexible framework (v8+) supports full custom extensions via MATPOWER Extension API -- user-defined element types, formulations, and constraints bundled as extension classes.

Source: [Example Extensions](https://matpower.app/manual/matpower/ExampleExtensions.html)

### SCOPF (Security-Constrained OPF)

MATPOWER does **not** include a standalone `runscopf` function. Security-constrained OPF can be achieved via:

1. **MOST** -- set `most.security_constraints = 1` with a contingency table; solves a DC SCOPF as part of the multiperiod framework.
2. **Manual construction** -- use `makePTDF`/`makeLODF` to build post-contingency constraints, then add them to an `opt_model` object or iterate with `runopf` per contingency (Benders-style).

There is no AC SCOPF capability built-in. The MATPOWER mailing list confirms this is a frequently requested but unsupported feature in the core package.

Source: [MATPOWER mailing list](https://www.mail-archive.com/matpower-l@cornell.edu/msg06055.html), MOST documentation

### Continuation Power Flow (CPF)

`runcpf(mpcbase, mpctarget, mpopt)` traces voltage stability (P-V) curves from a base case to a target loading level.

Key options:
- `cpf.parameterization`: 1=natural, 2=arc length, 3=pseudo arc length (default)
- `cpf.stop_at`: `'NOSE'` (default), `'FULL'`, or target lambda value
- Event detection for: flow limits, nose point, P/Q/V limits
- Callback system for custom event handling and plotting

Source: [MATPOWER Options](https://matpower.app/manual/matpower/matpowerOptions.html), `mpoption.m`

### Cost Curve Support

Both polynomial and piecewise-linear cost functions are supported:

- **Polynomial** (MODEL=2): arbitrary degree; `f(p) = c_n*p^n + ... + c_1*p + c_0`
- **Piecewise linear** (MODEL=1): arbitrary number of breakpoints; `(p_1,f_1), (p_2,f_2), ...`

Utility functions: `totcost(gencost, Pg)` computes total cost, `margcost(gencost, Pg)` computes marginal cost.

Startup and shutdown costs are stored in `gencost` columns 2-3 but are only used by MOST for unit commitment problems; the standard OPF ignores them.

Source: [Data File Format](https://matpower.app/manual/matpower/DataFileFormat.html)

### Version and License

- **Version evaluated:** MATPOWER 8.1 (downloaded via `setup.sh` from GitHub releases)
- **License:** 3-clause BSD
- **GitHub:** [MATPOWER/matpower](https://github.com/MATPOWER/matpower) -- ~524 stars, ~171 forks
- **Primary author:** Ray D. Zimmerman, PSERC Cornell
- **Platforms:** MATLAB and GNU Octave
- **Bundled sub-packages:** MIPS (interior point solver), MP-Opt-Model (optimization modeling), MOST (scheduling), MPTest (testing framework)

Source: [GitHub repo](https://github.com/MATPOWER/matpower), local `LICENSE` file

## Sources

1. [MATPOWER Reference Manual (8.0)](https://matpower.org/doc/ref-manual/index.html)
2. [MATPOWER Functions List](https://matpower.app/manual/matpower/matpowerFunctions.html)
3. [MATPOWER Options Reference](https://matpower.app/manual/matpower/matpowerOptions.html)
4. [MATPOWER Data File Format](https://matpower.app/manual/matpower/DataFileFormat.html)
5. [MATPOWER Architecture Overview (8.0)](https://matpower.org/documentation/dev-manual/architecture.html)
6. [makePTDF Documentation](https://matpower.org/documentation/ref-manual/legacy/functions/makePTDF.html)
7. [makeLODF Documentation](https://matpower.org/documentation/ref-manual/legacy/functions/makeLODF.html)
8. [runpf Documentation (8.1)](https://matpower.org/documentation/ref-manual/legacy/functions/runpf.html)
9. [runopf Documentation (8.1)](https://matpower.org/documentation/ref-manual/legacy/functions/runopf.html)
10. [opf Documentation (8.1)](https://matpower.org/documentation/ref-manual/legacy/functions/opf.html)
11. [MOST GitHub README](https://github.com/MATPOWER/most)
12. [MOST User's Manual (PDF)](https://matpower.org/docs/MOST-manual.pdf)
13. [MATPOWER GitHub Repository](https://github.com/MATPOWER/matpower)
14. [Example Extensions](https://matpower.app/manual/matpower/ExampleExtensions.html)
15. [I/O Functions](https://matpower.app/manual/matpower/InputOutputFunctions.html)
16. [System Matrices](https://matpower.app/manual/matpower/FormingStandardPowerSystemsMatrices.html)
17. [MATPOWER 8.0 Release Announcement](https://matpower.org/2024/05/17/matpower-8-0-released/)
18. Local source: `/workspace/evaluations/matpower/matpower8.1/lib/runpf.m`
19. Local source: `/workspace/evaluations/matpower/matpower8.1/lib/runopf.m`
20. Local source: `/workspace/evaluations/matpower/matpower8.1/lib/mpoption.m`
21. Local source: `/workspace/evaluations/matpower/matpower8.1/lib/run_pf.m`
22. Local source: `/workspace/evaluations/matpower/matpower8.1/most/lib/most.m`
23. Local source: `/workspace/evaluations/matpower/matpower8.1/lib/makePTDF.m`

## Gaps and Uncertainties

- **No native AC SCOPF:** Confirmed absent from core MATPOWER. MOST provides DC SCOPF only. Need to verify whether the new flexible framework extensions enable AC SCOPF in v8.1.
- **Distributed slack in OPF:** `makePTDF` supports distributed slack weights, but it is unclear whether `runopf`/`rundcopf` natively support distributed slack formulation or only single-slack.
- **Loss approximation in DC OPF:** MATPOWER's DC OPF uses a sparse angle-based formulation (not PTDF-based), so it does not include loss approximation by default. The `toggle_dcline` extension includes loss coefficients for DC lines specifically. Need to test whether any built-in option enables lossy DC power flow.
- **MOST solver compatibility with Octave:** MOST requires an MIQP solver for UC problems. On Octave (no MATLAB Optimization Toolbox), this likely requires GLPK or Gurobi. Need to verify which solvers are available in the devcontainer.
- **New flexible framework maturity:** The `run_pf`/`run_opf` API is new in v8.0. Need to verify whether all features (extensions, CPF, etc.) work equivalently through both old and new APIs.
- **Three-phase/unbalanced support:** The architecture documentation mentions "unbalanced multiphase elements" as a capability of MP-Core, but this appears to be prototype-stage. Need to verify actual availability.
- **OPF result struct details:** The OPF results struct includes additional fields beyond the standard case struct (e.g., `raw`, `var`, `lin`, `nle`, `nli`, `qdc` for detailed solver output). These need testing to confirm availability and content under Octave.

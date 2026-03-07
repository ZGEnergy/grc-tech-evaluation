# MATPOWER — Research Context

Merged from three parallel research agents. Generated 2026-03-06.

---

## Section 1: API Surface, Formulations & Data Model

### Key Findings

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

**New flexible framework (MATPOWER 8+):**

```matlab
task = run_pf('case9');
task = run_opf('case9', mpopt);
```

Returns a `task` object with `task.dm` (data model), `task.nm` (network model), `task.mm` (math model).

### Data Model (MPC Struct)

- `mpc.bus` -- nb x 13+ matrix (input columns 1-13, output adds cols 14-17 for LMPs/duals)
- `mpc.branch` -- nbr x 13+ matrix (input columns 1-13, output adds cols 14-21 for flows/duals)
- `mpc.gen` -- ng x 21+ matrix (input columns 1-21, output adds cols 22-25 for duals)
- `mpc.gencost` -- ng (or 2*ng) x (5+N) matrix for cost curves

Named column constants accessed via `idx_bus`, `idx_brch`, `idx_gen`, `idx_cost`, or `define_constants`.

### Solver Interfaces

On Octave, available solvers: MIPS (built-in), GLPK (bundled w/ Octave), IPOPT (requires MEX), CLP, OSQP, HiGHS (new in v8.1). Default DC OPF solver selection order: GUROBI > CPLEX > MOSEK > OT > GLPK > BPMPD > MIPS.

### MOST (Multiperiod Stochastic UC/OPF)

MOST (`most(mdi, mpopt)`) solves multiperiod, stochastic, contingency-constrained optimal power flow with optional unit commitment. It formulates the problem as a mixed-integer quadratic program (MIQP) using DC power flow constraints. DC-only — no AC implementation released.

### Cost Curve Support

Both polynomial (MODEL=2, arbitrary degree) and piecewise-linear (MODEL=1, arbitrary breakpoints) cost functions supported. Startup/shutdown costs stored in gencost but only used by MOST for UC problems.

### Network Analysis Utilities

| Function | Returns | Dimensions |
|----------|---------|------------|
| `makeYbus(mpc)` | Bus admittance matrix | nb x nb |
| `makeBdc(mpc)` | DC B matrices | nb x nb, nbr x nb |
| `makePTDF(mpc, slack)` | DC power transfer distribution factors | nbr x nb |
| `makeLODF(mpc, PTDF)` | Line outage distribution factors | nbr x nbr |
| `makeJac(mpc)` | Power flow Jacobian | 2(nb-1) x 2(nb-1) |

`makePTDF` supports distributed slack via weight vector argument.

---

## Section 2: Extensions & Architecture

### Key Findings

- MATPOWER 8 introduced a complete architectural rewrite (MP-Core) with an explicit three-layer modeling structure: data model, network model, and mathematical model, each composed of modular element objects.
- Two extension mechanisms coexist: the legacy `userfcn` callback system (five stages: `ext2int`, `formulation`, `int2ext`, `printpf`, `savecase`) and the new MATPOWER 8 Extension API based on the `mp.extension` class with subclassing and element class modifiers.
- Network graph access is excellent via sparse matrix construction functions. No built-in NetworkX-style graph object, but the incidence/adjacency structure is directly accessible as sparse matrices.
- MP-Opt-Model is a standalone optimization modeling package providing `opt_model` class with `add_var`, `add_lin_constraint`, `add_nln_constraint`, and `add_quad_cost`/`add_nln_cost` methods plus a unified solver interface across LP/QP/MILP/MIQP/NLP.
- Interoperability with Python/DataFrames is indirect: the `matpower` PyPI package wraps via oct2py; the third-party `matpowercaseframes` package parses `.m` case files into pandas DataFrames.
- Built-in userfcn extensions: `toggle_softlims`, `toggle_reserves`, `toggle_iflims`, `toggle_dcline`.
- MOST does not yet support the MATPOWER 8 Extension API (tracked in Issue #8).

### Legacy Extension Mechanism: userfcn Callbacks

Registration: `mpc = add_userfcn(mpc, 'stagename', @callback_function);`

The `formulation` stage receives the OPF Model (`om`) object where users call `om.add_var()`, `om.add_lin_constraint()`, `om.add_nln_constraint()`, and cost methods.

### MATPOWER 8 Extension API (mp.extension)

New object-oriented extension mechanism through the `mp.extension` base class. Extensions are subclasses that override methods to inject custom element classes into the three-layer architecture.

```matlab
run_opf('case9', mpopt, 'mpx', mp.xt_my_extension)
```

### MP-Opt-Model: Optimization Modeling Layer

```matlab
om = opt_model;
om.add_var('Pg', ng, Pg0, Pgmin, Pgmax);
om.add_lin_constraint('Pmis', A, l, u);
om.add_quad_cost('cost', Q, c);
opt = om.solve();
```

### Three-Layer Architecture (MP-Core)

1. **Data Model** — User-facing element parameters and quantities
2. **Network Model** — Physical network connections, formulation-specific (AC/DC)
3. **Mathematical Model** — Optimization/simulation problem, uses MP-Opt-Model

### Codebase Organization

```
matpower/
  lib/              # Core functions (opf.m, runpf.m, etc.)
    +mp/            # MATPOWER 8 OO classes
  mp-opt-model/     # Standalone optimization modeling
  most/             # MATPOWER Optimal Scheduling Tool
  mips/             # Built-in interior point solver
  mptest/           # Test framework
  data/             # Standard test cases
```

Legacy OPF call chain: `runopf` -> `opf` -> `opf_setup` -> `opf_execute` -> `dcopf_solver` or `nlpopf_solver`

---

## Section 3: Limitations & Ecosystem

### Key Findings

- **MOST is DC-only.** The scheduling tool supports stochastic, security-constrained UC but is limited to DC power flow network modeling.
- **No native SCOPF.** Users must implement SCOPF by manually enumerating contingency constraints using the extensible OPF framework.
- **No native distributed slack bus in power flow.** GitHub issues #136 and #63 confirm this is not implemented.
- **Bus factor of 1.** Ray Zimmerman accounts for 98%+ of commits. He left Cornell for private industry in mid-2024. NSF funding has ended.
- **Octave solver gap partially closed.** HiGHS support in v8.1 fills the critical MILP gap on Octave.
- **Installation is non-scriptable.** The interactive `install_matpower.m` requires input() prompts. Manual addpath of 5+ subdirectories required.
- **No package manager distribution.** Distributed as GitHub release zip file (46 MB). No checksums.
- **Lossy DC OPF exists but LMP decomposition requires manual work.**
- **PTDF matrix computation available and recently enhanced.** `makePTDF()` updated in v8.0 to support per-bus slack distributions.
- **Massive academic use but no evidence of production/operational deployment.** 750+ citations/year, 22,000+ downloads/year, but exclusively research/education.

### Release History

| Version | Date | Key Changes |
|---------|------|-------------|
| 8.1 | Jul 13, 2025 | HiGHS solver support, three-phase POC enhancements |
| 8.0 | May 17, 2024 | Major redesign: MP-Core OO architecture |
| 7.1 | Oct 8, 2020 | MP-Opt-Model 3.0, OSQP support |
| 7.0 | Jun 20, 2019 | PSS/E RAW export, user-defined nonlinear constraints |

### Community Statistics

- Stars: 534, Forks: 172, Contributors: 17
- Ray Zimmerman: 2,556 commits (98%+)
- **Bus factor: 1**
- Mailing lists at Cornell; no modern community platform

### Funding & Sustainability

- NSF funding through Cornell is closed
- Limited MathWorks support for three-phase features only
- Plans to expand contributors and explore fee-based model are aspirational
- **High sustainability risk**

### Solver Ecosystem on Octave

| Solver | Type | Open-Source | Octave Support |
|--------|------|-------------|----------------|
| MIPS | NLP | Yes (bundled) | Yes |
| GLPK | LP | Yes (bundled w/ Octave) | Yes |
| IPOPT | NLP | Yes | Yes (requires MEX) |
| HiGHS | LP/QP/MILP | Yes | Yes (new in v8.1) |
| OSQP | QP | Yes | Yes |

### Open Issues Relevant to Evaluation

| Issue | Status | Relevance |
|-------|--------|-----------|
| #136 -- Distributed slack PF | Open (Jan 2022) | Tests A-11, B-8 |
| #63 -- Slack distribution at slack bus | Open (Mar 2019) | Tests A-11, B-8 |
| #127 -- makePTDF ext2int error | Open (Sep 2021) | Tests B-9, C-9 |
| #54 -- PSS/E RAW v34 support | Open (Dec 2018) | Test P2-1 |

### MATLAB vs Octave

MATPOWER is BSD-3-Clause but runs on MATLAB (proprietary) or GNU Octave (GPLv3). Octave is 2-3x slower (no JIT), fewer solver bindings, but MATPOWER explicitly tests on Octave as first-class platform. All evaluation testing runs on Octave.

---

## Key Gaps and Uncertainties (to verify during testing)

1. **HiGHS on Octave** — Does the HiGHS MEX interface actually work in the devcontainer?
2. **MOST learning curve** — Effort to set up `mdi` data structures for SCUC/stochastic tests
3. **Octave large-scale performance** — No benchmarks for 10k-bus systems on Octave
4. **Lossy DC OPF specifics** — Exact mechanism for enabling loss approximation and extracting decomposed LMPs
5. **SCOPF implementation effort** — No turnkey SCOPF; effort to build via userfcn callbacks unknown
6. **Distributed slack OPF** — May be partially achievable through DC OPF formulation manipulation, but native support absent
7. **MP-Core Extension API maturity** — User's Manual not updated for v8.0 flexible framework
8. **Issue #127 (makePTDF ext2int)** — May affect PTDF computation on non-internally-ordered networks

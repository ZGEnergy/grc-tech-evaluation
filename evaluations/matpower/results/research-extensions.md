# MATPOWER — Research: Extensions & Architecture

## Key Findings

- **MATPOWER 8 introduced a complete architectural rewrite** (MP-Core) with an explicit three-layer modeling structure: data model, network model, and mathematical model, each composed of modular element objects. This is a major improvement over the monolithic legacy architecture. ([Architecture Overview](https://matpower.org/documentation/dev-manual/architecture.html))
- **Two extension mechanisms coexist**: the legacy `userfcn` callback system (five stages: `ext2int`, `formulation`, `int2ext`, `printpf`, `savecase`) and the new MATPOWER 8 Extension API based on the `mp.extension` class with subclassing and element class modifiers. ([Extending the OPF](https://matpower.app/manual/matpower/ExtendingtheOPF.html), [Customizing MATPOWER](https://matpower.org/documentation/dev-manual/customizing.html))
- **Network graph access is excellent** via sparse matrix construction functions: `makeYbus` (admittance), `makeBdc` (DC B matrices), `makePTDF` (power transfer distribution factors), `makeLODF` (line outage distribution factors), `makeJac` (Jacobian), and `connected_components`. No built-in NetworkX-style graph object, but the incidence/adjacency structure is directly accessible as sparse matrices. ([Forming Standard Power Systems Matrices](https://matpower.app/manual/matpower/FormingStandardPowerSystemsMatrices.html))
- **MP-Opt-Model** is a standalone optimization modeling package (extracted from MATPOWER core) providing `opt_model` class with `add_var`, `add_lin_constraint`, `add_nln_constraint`, and `add_quad_cost`/`add_nln_cost` methods plus a unified solver interface across LP/QP/MILP/MIQP/NLP. ([MP-Opt-Model GitHub](https://github.com/MATPOWER/mp-opt-model))
- **Interoperability with Python/DataFrames is indirect**: the `matpower` PyPI package wraps MATPOWER via oct2py (Octave bridge), but has serialization limitations (e.g., `opf_model` objects fail to transfer). The third-party `matpowercaseframes` package parses `.m` case files into pandas DataFrames without requiring Octave. ([matpower PyPI](https://pypi.org/project/matpower/), [matpowercaseframes GitHub](https://github.com/UGM-EPSLab/matpowercaseframes))
- **Built-in userfcn extensions** demonstrate the callback pattern: `toggle_softlims`, `toggle_reserves`, `toggle_iflims`, `toggle_dcline` — each implementing all five callback stages. ([toggle_softlims](https://matpower.org/docs/ref/matpower7.0/lib/toggle_softlims.html), [toggle_reserves](https://matpower.org/docs/ref/matpower6.0b1/toggle_reserves.html))
- **MOST** (MATPOWER Optimal Scheduling Tool) extends MATPOWER for multi-period, stochastic, security-constrained unit commitment and OPF, built as a separate package on top of MATPOWER's OPF engine. ([MOST GitHub](https://github.com/MATPOWER/most))
- **The MATPOWER case struct (`mpc`)** is the universal data container: fields `bus`, `branch`, `gen`, `gencost` as numeric matrices with named column index constants (`IDX_BUS`, `IDX_BRCH`, `IDX_GEN`). `savecase`/`loadcase` handle M-file and MAT-file serialization. ([Case Format](https://matpower.app/manual/matpower/DataFileFormat.html))

## Detailed Notes

### Legacy Extension Mechanism: userfcn Callbacks

MATPOWER's original (pre-8.0) extension mechanism uses callback functions registered at five stages of an OPF simulation. This remains fully supported in MATPOWER 8.1 under the "legacy framework."

**Registration:**

```matlab
mpc = add_userfcn(mpc, 'stagename', @callback_function);
```

**The five callback stages and their signatures:**

| Stage | Signature | Purpose |
|-------|-----------|---------|
| `ext2int` | `mpc = userfcn(mpc, mpopt, args)` | Reorder custom data to internal bus numbering |
| `formulation` | `om = userfcn(om, mpopt, args)` | Add variables, constraints, costs to the OPF model object |
| `int2ext` | `results = userfcn(results, mpopt, args)` | Convert results back to external numbering |
| `printpf` | `results = userfcn(results, fd, mpopt, args)` | Print custom results |
| `savecase` | `mpc = userfcn(mpc, fd, prefix, args)` | Save custom data to case file |

The `formulation` stage is the primary extension point, receiving the OPF Model (`om`) object where users call `om.add_var()`, `om.add_lin_constraint()`, `om.add_nln_constraint()`, and cost methods.

**Built-in toggle functions** using this mechanism:
- `toggle_reserves` — co-optimizes energy and fixed zonal reserves
- `toggle_iflims` — enforces DC interface flow limits
- `toggle_softlims` — relaxes hard limits (VMIN, VMAX, RATE_A, PMIN, PMAX, QMIN, QMAX, ANGMAX, ANGMIN) with penalty costs
- `toggle_dcline` — adds DC transmission line modeling

Each toggle function implements all five stages, serving as canonical examples of the pattern.

**Sources:**
- [Callback Stages and Example](https://matpower.app/manual/matpower/CallbackStagesandExample.html)
- [Extending the OPF](https://matpower.app/manual/matpower/ExtendingtheOPF.html)
- [add_userfcn reference](https://matpower.org/docs/ref/matpower5.1/add_userfcn.html)
- [toggle_softlims reference](https://matpower.org/docs/ref/matpower7.0/lib/toggle_softlims.html)

### MATPOWER 8 Extension API (mp.extension)

MATPOWER 8 introduced a new object-oriented extension mechanism through the `mp.extension` base class. Extensions are subclasses that override methods to inject custom element classes into the three-layer architecture.

**Key methods to override in an extension:**

1. Five methods for replacing top-level model/converter classes:
   - Task class, data model converter class, data model class, network model class, math model class

2. Four methods for modifying element classes within each container:
   - `dmc_element_classes()` — data model converter elements
   - `dm_element_classes()` — data model elements (varies by task: PF/CPF/OPF)
   - `nm_element_classes()` — network model elements (varies by formulation: AC/DC)
   - `mm_element_classes()` — math model elements (varies by task and formulation)

**Using an extension:**

```matlab
run_opf('case9', mpopt, 'mpx', mp.xt_my_extension)
```

**Built-in extensions (MATPOWER 8):**
- `mp.xt_legacy_dcline` — DC line support
- `mp.xt_reserves` — fixed zonal reserves (new-style equivalent of toggle_reserves)
- Three-phase extension (prototype)

**Creating a new element type** requires implementing classes across four layers:
1. **Data model element** (`mp.dme_*`) — defines data columns, connectivity, parameter building
2. **Data model converter** (`mp.dmc_*`) — import/export between formats
3. **Network model element** (`mp.nme_*`) — port/state variables, network equation contributions
4. **Math model element** (`mp.mme_*`) — optimization variables, constraints, costs

All element classes return the same `name()` string to link across layers (e.g., all return `'legacy_dcline'`).

**Customization via MATPOWER options** (alternative to extensions):

```matlab
mpopt.exp.mm_element_classes = {{@mp.mme_gen_opf_ac_oval, 'mp.mme_gen_opf_ac'}};
```

**Sources:**
- [How to Create an Extension](https://matpower.org/documentation/howto/extension.html)
- [How to Create a New Element Type](https://matpower.org/documentation/howto/element.html)
- [mp.extension class reference](https://matpower.org/documentation/ref-manual/classes/mp/extension.html)
- [Customizing MATPOWER](https://matpower.org/documentation/dev-manual/customizing.html)
- [How to Add an OPF Constraint](https://matpower.org/documentation/howto/add-constraint.html)

### Three-Layer Architecture (MP-Core)

MATPOWER 8's MP-Core decouples three modeling concerns:

**Layer 1 — Data Model (`mp.data_model`)**
- User-facing element parameters and quantities
- Organized as a container of `mp.dm_element` objects (bus, gen, branch, load, shunt)
- Handles data validation, parameter extraction, per-unit conversion
- Decoupled from file format via data model converter layer

**Layer 2 — Network Model (`mp.network_model`)**
- Physical network connections, states, and power flows
- Formulation-specific subclasses: AC (polar/cartesian), DC
- Builds system admittance matrices, incidence structure
- Elements implement `np()` (ports), `nz()` (non-voltage state variables)

**Layer 3 — Mathematical Model (`mp.math_model`)**
- Optimization/simulation problem formulation
- Task-specific: PF, CPF, OPF
- Uses MP-Opt-Model (`opt_model`) for variable/constraint/cost management
- Solver dispatch based on problem type and available solvers

**Task object** (`mp.task`) orchestrates the three layers:
1. Constructs data model from input case
2. Builds network model from data model
3. Constructs math model from network model
4. Solves
5. Propagates solution back through layers

**Data Model Converter** (`mp.dm_converter`) decouples the data model from file formats (legacy `mpc` struct, PSS/E RAW, etc.).

**Sources:**
- [Architecture Overview](https://matpower.org/documentation/dev-manual/architecture.html)
- [Classes Reference](https://matpower.org/documentation/ref-manual/classes/index.html)

### MP-Opt-Model: Optimization Modeling Layer

Originally part of MATPOWER, extracted as a standalone package for reuse. Provides the `opt_model` class that serves as the mathematical backbone.

**Key API:**

```matlab
om = opt_model;
om.add_var('Pg', ng, Pg0, Pgmin, Pgmax);      % optimization variables
om.add_lin_constraint('Pmis', A, l, u);         % linear constraints: l <= A*x <= u
om.add_nln_constraint('Qmis', N, 1, @fcn, @hess);  % nonlinear constraints
om.add_quad_cost('cost', Q, c);                 % quadratic cost: 0.5*x'*Q*x + c'*x
om.add_nln_cost('fuel', 1, @cost_fcn);          % general nonlinear cost
opt = om.solve();                               % unified solver dispatch
```

**Solver support** (unified interface — switch by changing an option):
- LP/MILP: GLPK, CPLEX, Gurobi, MOSEK, linprog
- QP/MIQP: CPLEX, Gurobi, MOSEK, quadprog, BPMPD
- NLP: MIPS (built-in), IPOPT, fmincon, Knitro

**Sources:**
- [MP-Opt-Model GitHub](https://github.com/MATPOWER/mp-opt-model)
- [opt_model class reference](https://matpower.org/doc/mpom/classes/opt_model.html)
- [MP-Opt-Model Manual 2.0](https://matpower.org/docs/MP-Opt-Model-manual-2.0.pdf)

### Network Graph Access and Matrix Construction

MATPOWER provides direct access to power system network topology through sparse matrix construction functions. There is no graph object abstraction — the network is represented as sparse MATLAB/Octave matrices.

**Core matrix-forming functions:**

| Function | Signature | Returns |
|----------|-----------|---------|
| `makeYbus` | `[Ybus, Yf, Yt] = makeYbus(mpc)` | Bus admittance matrix (complex, nb x nb), branch-from/to matrices |
| `makeBdc` | `[Bbus, Bf, Pbusinj, Pfinj] = makeBdc(mpc)` | DC power flow B matrices and injection vectors |
| `makeB` | `[Bp, Bpp] = makeB(mpc, alg)` | Fast-decoupled power flow matrices (XB or BX) |
| `makePTDF` | `H = makePTDF(mpc, slack)` | Power transfer distribution factor matrix (nbr x nb) |
| `makeLODF` | `LODF = makeLODF(branch, PTDF)` | Line outage distribution factors (nbr x nbr) |
| `makeJac` | `J = makeJac(mpc)` | Power flow Jacobian matrix |

**Topology utilities:**
- `connected_components(C)` — finds connected components from incidence matrix
- `bustypes(bus, gen)` — classifies buses as REF, PV, or PQ

**Adjacency/incidence:**
- The bus-branch incidence matrix can be constructed from `mpc.branch(:, [F_BUS T_BUS])` columns
- `Ybus` itself serves as a weighted adjacency matrix (non-zero entries = connected buses)
- `makeIncidence` (in extras/sdp_pf) builds an explicit node-branch incidence matrix

**Requirement:** All functions require internal bus numbering (consecutive from 1). Use `ext2int(mpc)` to convert.

**Sources:**
- [Forming Standard Power Systems Matrices](https://matpower.app/manual/matpower/FormingStandardPowerSystemsMatrices.html)
- [makePTDF reference](https://matpower.org/documentation/ref-manual/legacy/functions/makePTDF.html)
- [makeLODF reference](https://matpower.org/documentation/ref-manual/legacy/functions/makeLODF.html)
- [connected_components reference](https://matpower.org/doc/ref-manual/legacy/functions/connected_components.html)

### MOST (MATPOWER Optimal Scheduling Tool)

MOST extends MATPOWER for temporal, stochastic, and security-constrained problems. It is a separate package bundled with MATPOWER.

**Capabilities:**
- Deterministic or stochastic formulations
- Single or multi-period scheduling
- Unit commitment (MILP) with min up/down time constraints
- Ramping costs and constraints
- Locational contingency and load-following reserves
- Deferrable demands and lossy storage resources
- Uncertain renewable generation (scenario-based)

**Architecture:** MOST builds on top of MATPOWER's OPF engine, constructing a large-scale optimization problem that links multiple OPF snapshots across time periods and scenarios. It uses MP-Opt-Model for problem assembly.

**Solver requirements:** Requires a high-performance LP/MILP or QP/MIQP solver (Gurobi, CPLEX, MOSEK, or GLPK for Octave).

**Limitation (as of v1.3.1):** MOST does not yet support the MATPOWER 8 Extension API for user-defined variables, constraints, and costs ([Issue #8](https://github.com/MATPOWER/most/issues/8)).

**Sources:**
- [MOST GitHub](https://github.com/MATPOWER/most)
- [MOST Manual 1.3.1](https://matpower.org/docs/MOST-manual.pdf)

### Interoperability: Python, DataFrames, External Formats

MATPOWER's native data format is MATLAB/Octave structs and matrices. Interoperability with Python and DataFrame-based workflows requires bridging tools.

**Python bridges:**

1. **matpower PyPI package** (`pip install matpower[octave]`): Wraps MATPOWER via oct2py, launching an Octave subprocess. Results are transferred as MAT files. Known limitation: `opf_model` and other complex Octave objects fail serialization — workaround is to strip those fields before pulling results to Python. ([matpower PyPI](https://pypi.org/project/matpower/), [GitHub Issue #134](https://github.com/MATPOWER/matpower/issues/134))

2. **matpowercaseframes** (`pip install matpowercaseframes`): Pure Python parser (regex-based, no Octave needed) that converts MATPOWER `.m` case files into pandas DataFrames. Supports export to Excel and back to `mpc` dict. ([matpowercaseframes GitHub](https://github.com/UGM-EPSLab/matpowercaseframes))

3. **PYPOWER**: A pure Python port of MATPOWER (older version ~5.x), using NumPy arrays. Not maintained to track MATPOWER 8 features. ([PYPOWER GitHub](https://github.com/rwl/PYPOWER))

**Native export:**
- `savecase('file.m', mpc)` — saves to M-file (tab-delimited, text-editable)
- `savecase('file.mat', mpc)` — saves to MAT-file (binary, loadable in Python via scipy.io)
- Manual CSV export: `csvwrite('bus.csv', mpc.bus)` in Octave

**No built-in NetworkX, pandas, or JSON export.** All interop requires external tooling or manual matrix extraction.

### Reference Bus and Internal Indexing

MATPOWER uses an internal consecutive bus numbering system (1 to nb) for all computations. The `ext2int` / `int2ext` conversion functions handle mapping between external (user-defined, potentially non-consecutive) and internal numbering.

**Reference bus:** A single generator bus designated as type 3 (`REF`) in `mpc.bus(:, BUS_TYPE)`. It provides voltage angle reference and absorbs real power slack. The `bustypes` function classifies all buses. For `makePTDF`, if no slack is specified, the reference bus is used by default. Distributed slack is supported via an nb x 1 weight vector.

**Sources:**
- [bustypes reference](https://matpower.org/docs/ref/matpower5.0/bustypes.html)
- [DC Power Flow](https://matpower.app/manual/matpower/DCPowerFlow.html)

### Codebase Organization

The MATPOWER repository is organized into modular sub-packages:

```
matpower/
  lib/              # Core MATPOWER functions (opf.m, runpf.m, etc.)
    +mp/            # MATPOWER 8 OO classes (mp.task, mp.data_model, etc.)
  mp-opt-model/     # Standalone optimization modeling (opt_model class)
  most/             # MATPOWER Optimal Scheduling Tool
  mips/             # MATPOWER Interior Point Solver
  mptest/           # Test framework
  data/             # Standard IEEE/Polish/RTE test cases
  examples/         # Tutorial scripts
  docs/             # Manuals and release notes
```

**Legacy OPF call chain (still functional in 8.1):**
`runopf` -> `opf` -> `opf_setup` (builds OM object) -> `opf_execute` -> `dcopf_solver` or `nlpopf_solver`

**Flexible framework call chain (MATPOWER 8):**
`run_opf` -> `run_mp` (with task class) -> task constructs data model -> network model -> math model -> solve

**Sources:**
- [MATPOWER GitHub](https://github.com/MATPOWER/matpower)
- [opf reference](https://matpower.org/documentation/ref-manual/legacy/functions/opf.html)

## Sources

1. [Architecture Overview — MATPOWER 8.0 Dev Manual](https://matpower.org/documentation/dev-manual/architecture.html)
2. [Extending the OPF — MATPOWER Manual](https://matpower.app/manual/matpower/ExtendingtheOPF.html)
3. [Callback Stages and Example — MATPOWER Manual](https://matpower.app/manual/matpower/CallbackStagesandExample.html)
4. [Customizing MATPOWER — MATPOWER 8.1 Dev Manual](https://matpower.org/documentation/dev-manual/customizing.html)
5. [How to Create an Extension — MATPOWER 8.0](https://matpower.org/documentation/howto/extension.html)
6. [How to Create a New Element Type — MATPOWER 8.0](https://matpower.org/documentation/howto/element.html)
7. [How to Add an OPF Constraint — MATPOWER 8.1](https://matpower.org/documentation/howto/add-constraint.html)
8. [mp.extension class reference — MATPOWER 8.1](https://matpower.org/documentation/ref-manual/classes/mp/extension.html)
9. [Forming Standard Power Systems Matrices — MATPOWER Manual](https://matpower.app/manual/matpower/FormingStandardPowerSystemsMatrices.html)
10. [makePTDF — MATPOWER 8.1](https://matpower.org/doc/ref-manual/legacy/functions/makePTDF.html)
11. [makeLODF — MATPOWER 8.0](https://matpower.org/documentation/ref-manual/legacy/functions/makeLODF.html)
12. [opt_model class — MATPOWER 8.0](https://matpower.org/doc/mpom/classes/opt_model.html)
13. [MP-Opt-Model GitHub](https://github.com/MATPOWER/mp-opt-model)
14. [MOST GitHub](https://github.com/MATPOWER/most)
15. [MOST Manual 1.3.1](https://matpower.org/docs/MOST-manual.pdf)
16. [MATPOWER GitHub Repository](https://github.com/MATPOWER/matpower)
17. [matpower PyPI package](https://pypi.org/project/matpower/)
18. [matpowercaseframes GitHub](https://github.com/UGM-EPSLab/matpowercaseframes)
19. [MATPOWER/matpower Issue #134 — Python interop discussion](https://github.com/MATPOWER/matpower/issues/134)
20. [toggle_softlims reference](https://matpower.org/docs/ref/matpower7.0/lib/toggle_softlims.html)
21. [toggle_reserves reference](https://matpower.org/docs/ref/matpower6.0b1/toggle_reserves.html)
22. [MATPOWER OPF Architecture Slides (PDF)](https://matpower.org/docs/MATPOWER-OPF-slides.pdf)
23. [Data File Format — MATPOWER Manual](https://matpower.app/manual/matpower/DataFileFormat.html)
24. [MATPOWER 8 Class Hierarchy](https://matpower.org/documentation/ref-manual/classes/index.html)
25. [NSF Award #1642341 — Foundations for MATPOWER as an Extensible Tool](https://www.nsf.gov/awardsearch/showAward?AWD_ID=1642341)

## Gaps and Uncertainties

- **MOST + Extension API integration**: MOST 1.3.1 does not support the MATPOWER 8 Extension API for user-defined variables/constraints/costs (tracked in [MOST Issue #8](https://github.com/MATPOWER/most/issues/8)). This means multi-period/stochastic problems cannot use the new element-based extension mechanism — only the legacy userfcn approach is available for MOST.
- **Three-phase extension maturity**: The three-phase extension (`mp.xt_3p`) is described as a "prototype" in the class listing. Its completeness and production-readiness are unclear.
- **Flexible framework feature parity**: It is not documented whether all legacy features (e.g., all toggle functions, PSS/E import) are fully available in the flexible framework, or if some still require the legacy framework path.
- **Performance of Python bridge**: The oct2py bridge launches a separate Octave process and transfers data via MAT files. The performance overhead for large-scale cases (e.g., Polish 3000+ bus systems) has not been benchmarked in the sources found.
- **No native graph abstraction**: MATPOWER provides sparse matrices but no graph object (like NetworkX or igraph). Users must construct graph representations manually from the bus/branch data or Ybus matrix. This is a potential friction point for users coming from Python graph analysis workflows.
- **DataFrame interop quality**: `matpowercaseframes` appears to be a community project (UGM-EPSLab) with limited maintenance signals. Its reliability for MATPOWER 8-specific features (new element types, extended case fields) needs verification during testing.
- **Extension composability**: The documentation states that independently developed extensions can coexist, but the practical limits of composing multiple extensions (e.g., reserves + soft limits + custom elements simultaneously) in the new framework need testing.

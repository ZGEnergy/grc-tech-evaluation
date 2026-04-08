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

**Approach 1: Legacy direct specification.** The `mpc` struct can contain fields `A`, `l`, `u` for linear constraints (A \* x >= l, A \* x <= u), and `N`, `H`, `Cw`, `fparm` for generalized costs.

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

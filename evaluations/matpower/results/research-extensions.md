# MATPOWER: Extension Mechanisms, Architecture, and Interoperability

Research compiled 2026-03-13 for contract FA714626C0006.

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
  environments may vary; Octave's `table` support is relatively recent.

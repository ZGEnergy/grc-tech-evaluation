---
test_id: B-6
tool: matpower
dimension: extensibility
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T12:30:00Z"
---

# B-6: Code Architecture

## Result: INFORMATIONAL

## Finding

MATPOWER 8.1 has **strong separation of concerns** through two coexisting architectural paths: a well-structured legacy call chain and a new three-layer OO framework (MP-Core). The architecture is designed for extensibility, with clean internal interfaces and a documented extension API.

## Evidence

### Legacy Framework Call Chain (DCPF → DC OPF)

The legacy OPF path traces through 4 clearly separated layers:

1. **Entry point** (`rundcopf.m`): Thin wrapper that sets `mpopt.model = 'DC'` and calls `runopf`.
2. **Orchestrator** (`opf.m`, lines 232-261): Handles data conversion (`ext2int`), constructs the optimization model (`opf_setup`), solves it (`opf_execute`), and converts results back (`int2ext`). Also invokes user callbacks at each stage.
3. **Model builder** (`opf_setup.m`): Constructs an `opf_model` (subclass of `opt_model`) with:
   - Decision variables (`add_var`)
   - Linear constraints (`add_lin_constraint`) for power balance, branch flow limits
   - Cost functions (`add_quad_cost` for quadratic gen costs)
   - User-defined extensions via `userfcn` callbacks
4. **Solver dispatch** (`dcopf_solver.m`): Extracts problem matrices from the model object, dispatches to the selected QP/LP solver via `opt_model.solve()`, maps solution back to power system quantities.

**Key observation:** The `opt_model` class (from MP-Opt-Model package) provides a clean abstraction boundary between problem formulation and solver invocation. The same `opt_model.solve()` interface dispatches to MIPS, GLPK, HiGHS, Gurobi, etc. — the solver swap is a single option change, not a reformulation.

### New Flexible Framework (MP-Core, MATPOWER 8+)

The new framework has explicit three-layer separation:

1. **Data Model** (`mp.data_model`): Container of element objects (`mp.dme_bus`, `mp.dme_gen`, `mp.dme_branch`). Handles data validation, per-unit conversion, and import/export via converters.
2. **Network Model** (`mp.network_model`): Physical network representation. Formulation-specific subclasses (AC polar, AC cartesian, DC). Builds admittance matrices, incidence structure.
3. **Mathematical Model** (`mp.math_model`): Optimization formulation. Task-specific (PF, CPF, OPF). Uses `opt_model` for variable/constraint/cost management.

Entry: `run_opf` → `run_mp` → `mp.task_opf` constructs all three layers → solve → propagate solution back.

Extensions use `mp.extension` base class with element class modifiers across all three layers.

### Abstraction Layer Count

| Path | Layers | Separation Quality |
|------|--------|-------------------|
| Legacy DC OPF | 4 (entry → orchestrator → model builder → solver) | Good — each layer has a clear responsibility |
| New framework OPF | 5 (entry → task → data model → network model → math model) | Excellent — explicit three-layer architecture with documented interfaces |

### Separation of Concerns Assessment

| Concern | Separated? | Evidence |
|---------|-----------|---------|
| Network data model | Yes | `mpc` struct (legacy) / `mp.data_model` (new) |
| Problem formulation | Yes | `opf_setup.m` (legacy) / `mp.math_model` (new) |
| Solver interface | Yes | `opt_model.solve()` — unified across all solvers |
| Results extraction | Yes | `opf_execute` maps solver output back to `mpc` struct |
| Extension points | Yes | `userfcn` callbacks (legacy) / `mp.extension` class (new) |
| Data I/O | Yes | `loadcase`/`savecase`, `psse2mpc`/`save2psse` — separate from solve logic |

### Internal Interface Documentation

- Legacy interfaces: **Well documented** via function headers (MATLAB help format), the User's Manual, and the Reference Manual.
- New MP-Core interfaces: **Partially documented** — the Developer's Manual provides class reference, and "How to" guides exist for creating extensions and elements. However, the User's Manual has **not been updated** for the flexible framework as of v8.0 release.
- `opt_model` API: **Well documented** — separate MP-Opt-Model manual with class reference.

## Implications

MATPOWER's architecture is a strength:
- The legacy framework is mature, stable, and well-documented — a competent analyst can trace from API call to solver invocation in under an hour.
- The new framework adds principled extensibility through element composition and three-layer decoupling.
- The `opt_model` extraction as a standalone package demonstrates genuine separation of concerns.
- The main gap is documentation lag: the flexible framework's User's Manual update is incomplete, making the new extension API harder to discover than the legacy `userfcn` path.

This supports a **B+ to A-** range on the architecture sub-question of Extensibility.

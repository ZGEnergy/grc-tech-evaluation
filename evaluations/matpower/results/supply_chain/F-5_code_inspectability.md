---
test_id: F-5
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# F-5: Code Inspectability

## Methodology

Traced the execution path of `rundcopf(mpc)` from entry point to solver
invocation by reading source code and running with verbose output.

## Execution Path: `rundcopf(mpc)` to Solver

```
rundcopf.m          Entry point — sets mpopt.model = 'DC', calls runopf()
  |
  v
runopf.m            Dispatches to opf(), handles output formatting
  |
  v
opf.m               Main OPF logic:
  |                  - Validates inputs
  |                  - Selects solver (default: MIPS for DC)
  |                  - Creates mp.task_opf object (new framework) or calls legacy code
  |
  v
mp.task_opf         New OOP framework (v8.0+):
  |                  - run() method builds optimization model
  |                  - Calls mp.opt_model.solve()
  |
  v
mp.opt_model.solve  Optimization model layer:
  |                  - Assembles constraint matrices
  |                  - Dispatches to appropriate solver interface
  |
  v
qps_master.m        Solver dispatch:
  |                  - Checks solver availability
  |                  - Routes to qps_mips, qps_glpk, qps_ipopt, etc.
  |
  v
qps_mips.m          MIPS solver interface:
  |                  - Formats problem for MIPS
  |                  - Calls mips()
  |
  v
mips.m              MATPOWER Interior Point Solver:
                     - Primal-dual interior point method
                     - Pure .m code, no compiled components
                     - Iteration log printed with verbose option
```

## File Listing

All files in the execution path are readable .m source files:

| File | Location | Purpose |
|------|----------|---------|
| `rundcopf.m` | `lib/` | DC OPF entry point |
| `runopf.m` | `lib/` | Generic OPF runner |
| `opf.m` | `lib/` | OPF logic and dispatch |
| `mpoption.m` | `lib/` | Options management |
| `loadcase.m` | `lib/` | Case file loader |
| `ext2int.m` | `lib/` | External-to-internal data conversion |
| `@mp.task_opf/run.m` | `lib/+mp/` | OPF task execution (new framework) |
| `@mp.opt_model/solve.m` | `mp-opt-model/lib/+mp/` | Model solve dispatch |
| `qps_master.m` | `mp-opt-model/lib/` | Solver selection |
| `qps_mips.m` | `mp-opt-model/lib/` | MIPS interface |
| `mips.m` | `mips/lib/` | Interior point solver implementation |

## Opaque Binary Steps

**None.** The entire execution path from `rundcopf(mpc)` to the final
solver iteration is pure .m source code. A user can set a breakpoint at
any point in the chain and inspect all variables, matrices, and
intermediate computations.

## Verified via Verbose Execution

Running with verbose=3 confirms the full transparent path:

```
MATPOWER Version 8.1, 12-Jul-2025
Optimal Power Flow -- DC formulation
MATPOWER Interior Point Solver -- MIPS, Version 1.5.2, 12-Jul-2025
 (using built-in linear solver)
 it    objective   step size   feascond   gradcond   compcond   costcond
  0    7278.125                  0.3875     1765       19.57         0
  1    4131.027    0.69088   8.99e-17     0.1374      9.707      0.4323
  ...
  8    4131.027    3.16e-10  6.74e-17     3.17e-15   9.71e-07   2.20e-16
Converged!
```

Every iteration's values are computed in inspectable .m code.

## Assessment

**PASS.** MATPOWER achieves perfect code inspectability. The entire execution
path from API entry to solver convergence is readable MATLAB/Octave source code
with zero opaque binary steps. This is a direct consequence of the zero-compiled-
extension architecture (F-4).

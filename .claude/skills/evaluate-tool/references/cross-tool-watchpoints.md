# Cross-Tool Watchpoints

Generic cross-tool guidance for evaluators. No test-specific details — those come from
the protocol and eval-config.

## Solver Compatibility Matrix

| Solver | LP | MILP | QP | NLP | Notes |
|--------|:--:|:----:|:--:|:---:|-------|
| HiGHS | Y | Y | Y | N | Primary for LP/MILP/QP. QP support varies by tool binding. |
| SCIP | Y | Y | N | N | Secondary MILP. Some tools lack SCIP bindings. |
| Ipopt | Y | N | Y | Y | Primary for NLP (AC PF/OPF). Requires MUMPS linear solver. |
| GLPK | Y | Y | N | N | Lightweight baseline. Slower than HiGHS on large problems. |

Known ecosystem limitations (solver facts, not test-specific):
- **QP support:** HiGHS supports QP but some tool bindings may not expose it. If quadratic
  cost curves are present and the tool passes them to the solver, verify the solver handles
  them correctly. If the solver rejects them, document the limitation.
- **MILP performance:** HiGHS and SCIP have different branching heuristics. Large MILPs
  (SCUC at scale) may converge faster on one than the other. Test both where the protocol
  specifies it.
- **NLP convergence:** Ipopt convergence depends heavily on the initial point. See
  `convergence-protocol.md` for the flat-start → DC-warm-start fallback sequence.

## Timing Methodology

- **Python:** Use `time.perf_counter()` for wall-clock timing. Wrap only the solve call,
  not the model construction or result extraction.
- **Julia:** Use `@elapsed` or `@timed` macros. First invocation includes JIT compilation
  time — always run a warm-up solve and discard its timing. Record the second invocation.
- **Octave:** Use `tic`/`toc` around the solve call.

Exclude network loading from solve time. Record per-unit metrics for repeated solves
(time per scenario, time per contingency) alongside totals.

For Julia tools: first invocation of any function triggers JIT compilation. Stay in the
REPL and `include()` scripts to avoid restart overhead. The first solve of any problem
type will be slower; use the second invocation for timing.

## Known Pitfalls by Tool

Brief, factual observations to help evaluators avoid common mistakes:

- **PyPSA:** `n.lpf()` is linear power flow (DCPF), `n.optimize()` is OPF — they are
  different operations. `n.pf()` is AC power flow. Shadow prices require
  `n.optimize()` with appropriate solver settings.
- **pandapower:** Uses internal Newton-Raphson for AC PF, not an external solver. OPF
  uses either internal or PowerModels.jl backend. Check which backend is active.
- **PowerModels.jl:** First Julia invocation includes compilation time; use REPL for
  accurate timing. The `result` dict structure varies by formulation type.
- **PowerSimulations.jl:** Uses PowerSystems.jl for data model, JuMP for optimization.
  System construction from raw data requires significant boilerplate.
- **GridCal:** API surface has changed significantly across versions. Verify examples
  against the installed version.
- **MATPOWER (Octave):** `rundcpf` vs `rundcopf` vs `runopf` — each is a distinct
  function with different formulations. Octave is slower than MATLAB; do not compare
  Octave timings directly against MATLAB benchmarks in literature.

## Resource Type Classification

For stochastic tests requiring independent perturbations by resource type, generators
are classified using cost curve slope as a proxy for fuel type:

- **Baseload:** Low marginal cost (bottom quartile of cost curve slopes)
- **Intermediate:** Mid-range marginal cost
- **Peaker:** High marginal cost (top quartile)
- **Wind/Solar:** Zero or near-zero marginal cost with capacity factor patterns. If the
  reference case does not include explicit renewable generators, this category may be
  empty — document accordingly.

This classification method is documented in the protocol and referenced here for
convenience.

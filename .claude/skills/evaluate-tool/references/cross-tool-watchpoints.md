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

## PTDF Phase-Shifter Correction

Networks containing phase-shifting transformers (nonzero SHIFT column in branch data)
require bus injection and branch flow correction terms when validating PTDF-based flow
predictions. The standard formula `flow = PTDF @ Pinj` omits these corrections.

The full equation is: `flow = PTDF @ (Pinj - Pbusinj) + Pfinj`

where `Pbusinj` and `Pfinj` are correction terms derived from the admittance matrix
construction for branches with nonzero shift angles. Without these corrections, errors
can reach hundreds of MW on networks like ACTIVSg10k (which has 5 phase-shifting
transformers).

When evaluating B-9/C-9 (PTDF extraction/validation):
- Check whether the network has phase-shifting transformers
- If present, either apply Pbusinj/Pfinj corrections or exclude phase-shifting
  branches from the accuracy comparison
- The PTDF matrix itself is typically correct; the error is in the flow reconstruction

## ACTIVSg10k Congestion Characteristics

The ACTIVSg10k network has no binding branch constraints in base-case DCOPF (maximum
loading ~84-85%). This means:
- LMPs are uniform across all buses (no congestion component)
- Tests targeting congestion-driven capabilities (LMP decomposition, SCOPF cost premium,
  distributed slack LMP differences) produce no discriminative signal at MEDIUM scale
- If the protocol specifies preprocessing to tighten branch limits, apply it uniformly

When evaluating tests that depend on congestion signal (A-3, A-9, A-11, B-8, C-3, C-10
at MEDIUM scale), verify that branch constraints are actually binding before interpreting
LMP results. Uniform LMPs may indicate an uncongested network rather than a tool limitation.

## SCUC Generator Cycling

The case39 network has a high capacity-to-load ratio (~7,367 MW vs ~6,254 MW peak) with
uniform generator costs. All tools capable of SCUC report all generators committed for
all 24 hours with zero startups. This makes A-5 a formulation existence test rather than
a UC correctness test.

When evaluating A-5 (SCUC) on case39:
- Do not interpret "all generators on for all hours" as a test failure — it is the
  economically optimal solution for this network
- Verify that the tool can express UC binary variables, min up/down times, and startup
  costs even if they are not exercised
- If the protocol modifies case39 parameters to force cycling, verify that at least
  some generators cycle on/off during the horizon

## Convergence Verification

For AC power flow tests (A-2), verify convergence quality beyond the solver's
reported status:
- **Convergence residual** must be reported and below the tool's stated tolerance
- **Iteration count** must be reported (0 iterations indicates the solver did not
  actually run Newton-Raphson)
- **Voltage profile** must differ from flat-start defaults (1.0 pu) on >95% of buses
- If the tool cannot report iteration count or residual, document this as a diagnostic
  quality finding

A tool that reports "converged" but shows 0 NR iterations and flat-start voltages has
not actually solved the AC power flow.

## Measured vs Estimated Timing

All scalability grades must be based on measured wall-clock times, not estimates or
projections:
- Timings must come from actual execution (via `time.perf_counter()`, `@elapsed`,
  `tic`/`toc`)
- Estimated or projected timings must be clearly labeled as "estimated" and cannot
  support pass or qualified_pass on scalability tests
- If a test cannot be executed within the time budget, record fail with the projected
  timing as supplementary context
- JIT compilation overhead (Julia) must be excluded by using warm-up runs

## Unit Consistency (MW vs Per-Unit)

When transferring results between analyses (e.g., DC OPF dispatch to AC feasibility
check), verify unit consistency:
- Print and log `base_power` (base MVA) at each transfer point
- Log dispatch units and limit units before transfer
- Verify that the sending and receiving analyses use the same unit convention
- A mismatch between MW and per-unit values can produce apparent errors of 100x that
  are actually labeling errors, not solver failures

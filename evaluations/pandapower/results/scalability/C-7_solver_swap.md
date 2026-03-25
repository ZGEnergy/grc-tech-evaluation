---
test_id: C-7
tool: pandapower
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: "v2"
test_hash: "933c522e"
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 0.831
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 124
solver: "PYPOWER PIPS (internal)"
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T00:00:00Z
---

# C-7: Solver Swap (Repeat C-3 with each available open-source solver)

## Result: FAIL

## Approach

Inspected `pp.rundcopp()` and `pp.runopp()` function signatures for solver-selection
parameters. Neither function exposes a solver parameter. pandapower's DC OPF
(`rundcopp`) exclusively uses PYPOWER's built-in PIPS (Primal-Dual Interior Point
Solver). There is no mechanism to swap to HiGHS, GLPK, SCIP, or any other solver
via parameter change.

### API Inspection

`rundcopp` parameters: `net, verbose, check_connectivity, suppress_warnings,
switch_rx_ratio, delta, trafo3w_losses, **kwargs`. No solver-related parameter exists.

`runopp` parameters (AC OPF): Similarly no solver parameter. Both OPF functions use
PYPOWER's internal solver exclusively.

### Alternative Approach (Requires Reformulation)

Test A-9 demonstrated that DCOPF can be achieved via manual PTDF construction +
`scipy.optimize.linprog` (HiGHS backend). However, this requires **complete
reformulation** of the OPF problem outside pandapower's OPF framework -- pandapower
is used only as a data container and PTDF calculator. This does not satisfy the pass
condition, which requires solver swap via parameter change only.

## Output

| Aspect | Finding |
|--------|---------|
| Solver swap parameter | Not present |
| Available solvers | PYPOWER PIPS only |
| Swap mechanism | None [tool-specific] |
| Alternative path | scipy linprog (requires full reformulation) |
| `failure_reason` | `unsupported_in_installed_version` |

## Workarounds

- **What:** No workaround can satisfy the pass condition. The only alternative (scipy linprog via manual PTDF construction) requires complete problem reformulation.
- **Why:** pandapower's OPF is tightly coupled to PYPOWER's PIPS solver. The solver interface is hardcoded with no swap mechanism.
- **Durability:** blocking -- solver swap requires forking or complete external reformulation [tool-specific: hardcoded solver binding].
- **Grade impact:** Blocking limitation for solver flexibility at scale.

## Timing

- **Wall-clock:** 0.831 s (API inspection only, no solve)
- **Timing source:** measured
- **Peak memory:** not measured (no solve performed)
- **CPU threads used:** 1
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/pandapower/tests/scalability/test_c7_solver_swap.py`

---
test_id: B-1
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v11
skill_version: v2
test_hash: fececf15
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 3.931
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 309
solver: HiGHS
timestamp: 2026-03-24T12:00:00Z
---

# B-1: Add a flow gate limit to the DC OPF formulation from A-3

## Result: PASS

## Approach

Used PyPSA's documented `extra_functionality` callback mechanism to inject
a custom flow gate constraint into the DC OPF formulation. The callback
receives `(n, snapshots)` where `n.model` is the linopy `Model` object,
providing full access to add variables, constraints, and modify the
objective.

The flow gate FG spans two branches: line L1 and line L2. The callback
accesses the `Line-s` linopy variable, selects the gate branches, sums
their flows, and constrains the sum to be <= threshold via
`n.model.add_constraints()`.

Two cases were tested per the methodology guardrail:

1. **Non-binding case**: Threshold = 10,000 MW (unreachable). Verifies
   that the dual value is ~0.
2. **Binding case**: Threshold = 95% of unconstrained flow (~358.66 MW).
   Verifies that the dual is nonzero and objective increases.

Network setup mirrors A-3: differentiated generator costs (hydro $5,
nuclear $10, coal $25, gas $40) and 70% branch derating for congestion.

Solver: HiGHS with single-thread, 300s time limit, presolve on.

## Output

| Case | Threshold (MW) | Objective ($) | FlowGate Dual | Gate Flow (MW) |
|------|----------------|---------------|---------------|----------------|
| Non-binding | 10,000 | 370,208.16 | -0.0 | 377.53 |
| Binding | 358.66 | 385,881.87 | -830.32 | 358.66 |

**Pass condition checks:**

| Check | Result |
|-------|--------|
| Dual extractable (non-binding) | Yes |
| Dual extractable (binding) | Yes |
| Dual ~0 when non-binding | Yes (\|-0.0\| < 1e-4) |
| Dual nonzero when binding | Yes (\|-830.32\| > 1e-6) |
| Objective increases when binding | Yes (385,882 > 370,208) |

The binding flow gate constraint forces the optimizer to reroute power,
increasing total generation cost by $15,674 (4.2% increase). The negative
dual (-830.32 $/MWh) correctly reflects the shadow price of the constraint:
each additional MW of flow gate capacity would reduce cost by $830.32.

Note: the 75% and 90% threshold fractions were infeasible due to the already-
tight 70% branch derating. The 95% threshold (358.66 MW) was the tightest
feasible binding case. The infeasibility at tighter thresholds is expected
given the constrained network topology.

## Workarounds

None required. The `extra_functionality` callback is the documented public
API for custom constraint injection in PyPSA v1.1.2. The callback provides
full access to the linopy model (`n.model`) for adding constraints. Dual
values are extracted via `n.model.constraints["FlowGate"].dual`, which is
part of the linopy public API.

## Timing

- **Wall-clock:** 3.931s (non-binding + binding solves)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b1_custom_constraints_tiny.py`

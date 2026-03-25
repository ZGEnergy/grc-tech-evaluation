---
test_id: P2-2
tool: pypsa
dimension: p2_readiness
network: TINY
protocol_version: v11
skill_version: v2
test_hash: e6aab840
status: informational
workaround_class: null
timestamp: 2026-03-24T16:00:00Z
---

# P2-2: Piecewise-Linear Cost Curve Support

## Result: INFORMATIONAL — No native support; tranche workaround works

## Capability Assessment

**Native piecewise-linear cost curves: No.**

PyPSA v1.1.2 does not support multi-segment piecewise-linear cost curves as a
generator attribute. The cost-related generator attributes are:

| Attribute | Type | Description |
|-----------|------|-------------|
| `marginal_cost` | static or series | Single linear cost ($/MWh) |
| `marginal_cost_quadratic` | static or series | Quadratic cost term ($/MWh^2) |
| `start_up_cost` | float | Startup cost (requires `committable=True`) |
| `shut_down_cost` | float | Shutdown cost (requires `committable=True`) |
| `stand_by_cost` | static or series | Standby cost |

The `marginal_cost` attribute accepts a single scalar or a time-varying series,
but not a piecewise function of output level. There is no `offer_curve`,
`cost_segments`, or equivalent attribute. This is a tracked gap:

- Issue #1020 ("Add Option for Marginal Cost Offer Curve") — labeled `high priority`, open
- Issue #1473 ("Piecewise costs and constraints") — open

**Formulation type: N/A** (no native implementation, so no SOS2/lambda/incremental choice).

**Quadratic costs:** The `marginal_cost_quadratic` attribute enables quadratic
cost functions (cost = mc×P + mc_q×P^2), which is useful for smooth
approximations but does not represent true piecewise-linear offer curves.

## Workaround: Generator Tranche Decomposition

The standard workaround is to decompose a single generator with a piecewise-linear
cost curve into multiple "tranche" generators at the same bus, each representing
one segment.

### Test: 3-segment piecewise-linear cost curve

A generator with 150 MW capacity and three cost segments was modeled:

| Segment | MW Range | Marginal Cost |
|---------|----------|---------------|
| 1 | 0–50 MW | $20/MWh |
| 2 | 50–100 MW | $35/MWh |
| 3 | 100–150 MW | $50/MWh |

This was implemented as three separate generators at the same bus:

```python
n.add('Generator', 'gen_s1', bus='bus0', p_nom=50, marginal_cost=20)
n.add('Generator', 'gen_s2', bus='bus0', p_nom=50, marginal_cost=35)
n.add('Generator', 'gen_s3', bus='bus0', p_nom=50, marginal_cost=50)
```

With a 150 MW load and a 50 MW cheap generator ($10/MWh) on another bus, the
solver dispatched in correct merit order:

- gen_cheap: 50 MW (at capacity)
- gen_s1: 50 MW (at capacity, cheapest tranche)
- gen_s2: 50 MW (at capacity, fills remaining load)
- gen_s3: 0 MW (not needed)

**Objective: $3,250** = 50*10 + 50*20 + 50*35 = correct.

### Solver Compatibility

The tranche approach produces a standard LP (no SOS2 or special ordered sets),
so it is compatible with all solvers supported by linopy: HiGHS, GLPK, CBC,
Gurobi, CPLEX, MOSEK, Xpress, COPT.

### Limitations of the Tranche Workaround

1. **No automatic segment ordering guarantee:** The LP solver dispatches
   tranches in merit order because each has a distinct marginal cost, but this
   relies on convexity of the cost curve (increasing marginal costs). Non-convex
   cost curves (decreasing marginal costs in some segments) would require binary
   variables or SOS2 constraints that PyPSA does not natively support for cost
   curves.

2. **Generator count inflation:** A system with N generators and K segments each
   produces N*K generator objects. For a 500-generator system with 10-segment
   offer curves, this means 5,000 generator objects. PyPSA handles this without
   architectural issues but it increases model size.

3. **UC interaction:** If a generator with piecewise costs is also committable,
   the tranche decomposition requires additional manual logic to ensure all
   tranches share a single commitment decision (e.g., using `Link` components
   or custom constraints via `extra_functionality`).

4. **Post-processing burden:** Aggregating dispatch across tranches back to the
   original generator for reporting requires user code.

## Summary

| Aspect | Assessment |
|--------|-----------|
| Native piecewise-linear costs | No |
| Tracked for addition | Yes (issue #1020, high priority) |
| Workaround available | Yes — tranche decomposition |
| Workaround formulation | Standard LP (no SOS2 needed for convex curves) |
| Solver compatibility | All linopy-supported solvers |
| Key limitation | Non-convex cost curves require manual binary constraints |

## Sources

1. PyPSA v1.1.2 generator component attribute inspection (devcontainer)
2. Tranche decomposition test (devcontainer, HiGHS solver)
3. PyPSA issue #1020 — marginal cost offer curve (open, high priority)
4. PyPSA issue #1473 — piecewise costs and constraints (open)
5. research-limitations.md (this repository) — piecewise cost gap documented

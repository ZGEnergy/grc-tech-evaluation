---
test_id: B-1
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.108
peak_memory_mb: null
loc: 2
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# B-1: Custom Constraints

## Result: PASS

## Approach

Added a flow gate constraint (sum of signed flows on lines L15, L16, L17) to the DC OPF
using PyPSA's documented `create_model()` / `solve_model()` split API. The workflow:

1. Loaded the case39 network and set differentiated marginal costs (case39 generators all
   have identical c1=0.3, requiring small perturbations to break LP degeneracy).
2. Ran unconstrained DCOPF to determine baseline flows. The unconstrained gate flow was
   ~1123 MW.
3. Set the flow gate limit to 80% of unconstrained flow (~898 MW).
4. Called `n.optimize.create_model()` to build the Linopy model, then accessed line flow
   variables via `m["Line-s"]` and added the constraint with `m.add_constraints()`.
5. Solved with `assign_all_duals=True` and extracted the custom constraint dual from
   `m.dual["flow_gate"]`.

Key API calls:

```python
n.optimize.create_model()
m = n.model
line_s = m["Line-s"]
gate_expr = sum(line_s.sel(name=line) for line in FLOW_GATE_LINES)
m.add_constraints(gate_expr <= flow_gate_limit, name="flow_gate")
n.optimize.solve_model(solver_name="highs", assign_all_duals=True)
dual_value = m.dual["flow_gate"].values.item()
```

The custom constraint required **2 lines of code** (expression construction + constraint
addition). No source patching, forking, or undocumented API access was required.

## Output

| Metric | Value |
|--------|-------|
| Unconstrained gate flow | 1122.92 MW |
| Flow gate limit | 898.33 MW |
| Constrained gate flow | 898.33 MW |
| Dual value | -0.00443 |
| Is binding | Yes |
| Baseline objective | 1893.42 |
| Constrained objective | 1894.42 |
| Objective increase | 0.995 (0.053%) |

Per-line flow changes:

| Line | Unconstrained (MW) | Constrained (MW) |
|------|-------------------|------------------|
| L15  | 326.37 | 272.51 |
| L16  | 398.63 | 314.02 |
| L17  | 397.92 | 311.80 |

The dual value is non-zero (-0.00443), confirming the constraint is binding. The constrained
gate flow equals the limit within solver tolerance. The objective increased, confirming
redispatch occurred.

## Workarounds

None required for the custom constraint mechanism itself. The `create_model()` /
`m.add_constraints()` / `solve_model()` workflow is fully documented.

Note: Marginal costs required manual assignment due to the PPC importer not importing
gencost. This is a pre-existing issue (documented in A-3 result), not specific to B-1.

## Timing

- **Wall-clock:** 0.108s (constrained solve only)
- **Peak memory:** not measured
- **Solver iterations:** 26 (HiGHS simplex)

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b1_custom_constraints.py`

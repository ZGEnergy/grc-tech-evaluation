---
test_id: B-1
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v10"
skill_version: v1
test_hash: "fececf15"
status: qualified_pass
workaround_class: fragile
blocked_by: null
wall_clock_seconds: 1.41
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 268
solver: HiGHS
timestamp: "2026-03-13T00:00:00Z"
---

# B-1: Add flow gate limit to DC OPF, read dual value

## Result: QUALIFIED PASS

## Approach

GridCal (VeraGridEngine 5.6.28) has **no public API for custom constraint injection** into the OPF formulation. The OPF is formulated internally using PuLP as the LP modeling framework, and the `run_linear_opf_ts` function builds, solves, and returns `(OpfVars, LpModel)` in one call.

The workaround intercepts the PuLP model **before** the solve step by monkey-patching `PulpLpModel.solve`:

1. **Extract branch flow expressions** from existing internal constraints (named `br_flow_upper_lim_0_<branch_idx>`) by filtering out slack variables from the constraint's variable dictionary.
2. **Construct the flowgate constraint** as a weighted sum of flow expressions: `flow_br2 + flow_br4 <= limit_pu`.
3. **Inject the constraint** via `self.model.addConstraint()` before delegating to the original `solve`.
4. **Extract the dual value** via PuLP's `constraint.pi` attribute after solve completes.

Both binding and non-binding flowgate tests were executed:

- **Binding test:** Flowgate FG_01 (branches 2-3 and 2-30) with 400 MW limit
- **Non-binding test:** Same flowgate with 900 MW limit

## Output

| Metric | Base Case | Binding (400 MW) | Non-Binding (900 MW) |
|--------|-----------|-------------------|----------------------|
| Objective (pu) | 1256.22 | 1265.66 | 1256.22 |
| FG flow (MW) | 487.00 | 400.00 | 487.00 |
| FG dual | N/A | -60.11 | -0.0 |
| FG slack | N/A | -0.0 | 4.13 |
| Converged | Yes | Yes | Yes |

The binding constraint:
- Enforces the 400 MW limit exactly
- Increases objective by 9.44 (cost of re-dispatch)
- Has non-zero dual value (-60.1, indicating $60.1/MWh marginal cost of tightening)
- Dual correctly reflects binding status

The non-binding constraint:
- Does not alter the optimal solution
- Has zero dual value (as expected)

## Workarounds

- **What:** Monkey-patched `PulpLpModel.solve` to inject a PuLP constraint before the LP solve. Extracted branch flow LP expressions from internal constraint naming convention (`br_flow_upper_lim_0_<idx>`).
- **Why:** GridCal has no public API for adding user-defined constraints to the OPF. The OPF formulation is monolithic -- `run_linear_opf_ts` builds and solves in one call with no hook points.
- **Durability:** fragile -- Relies on: (1) internal constraint naming convention `br_flow_upper_lim_0_<idx>`, (2) internal `PulpLpModel` class in `VeraGridEngine.Utils.MIP.pulp_interface`, (3) constraint LHS structure containing flow expression + slack variables. Any refactoring of the OPF formulation would break this.
- **Grade impact:** The workaround is achievable without source patching, but depends entirely on undocumented internals. This limits the extensibility grade.

## Timing

- **Wall-clock:** 1.41 seconds (three solves: base, binding, non-binding)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver:** HiGHS via PuLP

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b1_custom_constraints.py`

Key code for constraint injection:

```python
def patched_solve(self, robust=False, show_logs=False, progress_text=None):
    var_dict = {v.name: v for v in self.model.variables()}
    fg_expr = pulp.LpAffineExpression()
    for br_idx, weight in zip(fg_branch_indices, fg_weights):
        cst = self.model.constraints[f"br_flow_upper_lim_0_{br_idx}"]
        for var, coeff in cst.items():
            if var.name not in (f"flow_slack_pos_0_{br_idx}", f"flow_slack_neg_0_{br_idx}"):
                fg_expr += var * coeff * weight
    self.model.addConstraint(fg_expr <= fg_limit_pu, fg_name)
    return original_solve(self, ...)
```

# B-1: Custom Constraints — Flow Gate Limit on DC OPF (TINY)

- **Test ID:** B-1
- **Slug:** custom_constraints
- **Tool:** PyPSA 1.1.2 + linopy 0.6.4
- **Network:** IEEE 39-bus (case39.m)
- **Solver:** HiGHS 1.13.1
- **Status:** PASS
- **Workaround durability:** N/A (no workaround needed)

## Pass Condition

Achievable through documented API, no source patching.

## Results

| Metric | Value |
|--------|-------|
| Wall clock | 0.37 s |
| Base objective (unconstrained) | 41261.94 |
| Constrained objective | 42957.28 |
| Objective increase | 1695.34 (+4.1%) |
| Gate flow total | 200.0 MW (binding) |
| Gate threshold | 200.0 MW |
| LOC (custom constraint) | 6 lines |

### Flow Gate Definition

Lines L0, L1, L2: sum of flows <= 200 MW.

### Dispatch Comparison

The flow gate constraint shifts generation away from the constrained corridor, redistributing dispatch to generators G2 (725 MW, up from 661), G5 (687, up from 661), G8 (840, up from 661), G9 (787, up from 661) while reducing G0 (365, down from 661) and G7 (465, down from 564).

## API

PyPSA provides a documented two-phase workflow for custom constraints:

```python
n.optimize.create_model()                          # build linopy model
line_s = n.model.variables["Line-s"]                # access flow variables
gate = line_s.sel(name=["L0", "L1", "L2"]).sum("name")
n.model.add_constraints(gate <= 200, name="gate_upper")
n.model.add_constraints(-gate <= 200, name="gate_lower")
n.model.solve(solver_name="highs")                  # solve
n.optimize.assign_solution()                         # write back to network
```

This uses the linopy algebraic modeling layer which provides xarray-style variable selection and constraint construction. The API is documented in PyPSA's optimization documentation.

## Observations

- LMPs (shadow prices on nodal balance) are not automatically assigned when using the manual `model.solve()` + `assign_solution()` path. Shadow prices are available via `n.model.constraints` duals but require manual extraction. This is a minor API friction point.
- The `create_model()` / `solve_model()` workflow is the recommended pattern (replacing the older `extra_functionality` callback).

## Test Script

`evaluations/pypsa/tests/extensibility/test_b1_custom_constraints_tiny.py`

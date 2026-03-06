# A-11: Distributed Slack OPF (TINY)

- **Test ID:** A-11
- **Slug:** distributed_slack_opf
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Solver:** HiGHS 1.13.1
- **Status:** FAIL

## Pass Condition

Tool supports distributed slack formulation in OPF. LMPs differ from single-slack A-3.

## Results

| Metric | Value |
|--------|-------|
| `distribute_slack` in `n.optimize()` | No |
| `distribute_slack` in `n.pf()` | Yes |
| LMP change when slack bus moved | None (0.0 max diff) |
| Cost change when slack bus moved | None (0.0) |
| PF dispatch differs with distributed slack | Yes (marginal, < 0.001 MW) |

### Finding

PyPSA's `n.optimize()` does not have a `distribute_slack` parameter. The optimization formulation uses implicit power balance constraints (Kirchhoff voltage law + nodal balance), making the dispatch and LMPs independent of which bus is designated as slack in the lossless DC OPF case.

**Key insight:** In lossless DC OPF, the slack bus choice is irrelevant to the optimization — it only affects how power flow is distributed in the non-optimization PF context. Changing the slack bus from bus 31 to bus 30 produced identical dispatch, cost, and LMPs.

`n.pf(distribute_slack=True)` is available for power flow analysis and does change how losses/mismatch are distributed across generators, but this is not an optimization feature.

### Relation to A-10

For loss-inclusive distributed reference, the `transmission_losses` parameter in A-10 naturally distributes loss components across buses, achieving a similar effect to distributed slack in the LMP decomposition.

## API

```python
# Power flow (works):
n.pf(distribute_slack=True)

# Optimization (no distributed slack parameter):
n.optimize(solver_name="highs")
# distribute_slack is NOT a parameter of n.optimize()
```

### Caution

Passing `distribute_slack=True` to `n.optimize()` does NOT cause an error. Due to `**kwargs`, the parameter is silently forwarded to solver_options and then to HiGHS, which logs an "unknown option" warning but continues solving. This means the parameter is silently ignored.

## LOC

N/A (feature not available).

## Workarounds

1. **Use transmission_losses (stable):** `n.optimize(transmission_losses=3)` provides bus-varying LMPs with loss components, achieving a similar effect to distributed slack.
2. **Custom formulation (stable):** Could implement distributed slack via `extra_functionality` callback or `create_model()` + manual constraint addition.

## Errors

- `n.optimize()` does not support distributed slack. The parameter exists only in `n.pf()`.

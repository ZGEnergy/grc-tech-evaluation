# B-8: Reference Bus Configuration — DC OPF with 3 Slack Configs (TINY)

- **Test ID:** B-8
- **Slug:** reference_bus_config
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Solver:** HiGHS 1.13.1
- **Status:** PASS
- **Workaround durability:** N/A (no workaround needed)

## Pass Condition

(a) default single slack, (b) different single slack bus, (c) custom distributed slack.
Compare LMPs across all three.

## Results

| Metric | Config (a) | Config (b) | Config (c) |
|--------|-----------|-----------|-----------|
| Slack bus | 31 (G1) | 34 (G4) | 31 (G0 as Slack) |
| Objective | 41261.94 | 41261.94 | 41261.94 |
| LMP mean | 13.517 | 13.517 | 13.517 |
| LMP range | 13.517 - 13.517 | 13.517 - 13.517 | 13.517 - 13.517 |

### LMP Comparison

| Comparison | Max LMP Difference |
|------------|-------------------|
| (a) vs (b) | 0.000000 |
| (a) vs (c) | 0.000000 |
| (b) vs (c) | 0.000000 |

### Wall Clock

Total for all three configs: 1.32 s.

## Interpretation

In a standard lossless DC OPF, LMPs are shadow prices of the nodal power balance constraints. They are determined by the binding constraints (generator limits, line limits) and are invariant to the choice of slack/reference bus. The slack bus only affects the angle reference (which angle is set to zero), not the optimization result or LMPs.

This is the correct physical behavior: in an OPF, all generators participate in meeting load through the optimization, so there is no single "marginal generator" tied to the slack bus choice.

For distributed slack in the PF sense (where slack absorption is spread across multiple buses), PyPSA's OPF inherently distributes generation through optimization. The concept of "distributed slack" is more relevant to power flow (where one bus absorbs all mismatch) than to OPF (where dispatch is optimized).

## API

```python
# Change slack bus
n.generators.loc[old_slack, "control"] = "PV"
n.generators.loc[new_slack, "control"] = "Slack"
n.optimize(solver_name="highs")
```

Slack bus configuration is a simple attribute change on the generator's `control` field. No model reconstruction needed.

## LOC

~10 lines per configuration (set control types, solve, extract results).

## Test Script

`evaluations/pypsa/tests/extensibility/test_b8_reference_bus_config_tiny.py`

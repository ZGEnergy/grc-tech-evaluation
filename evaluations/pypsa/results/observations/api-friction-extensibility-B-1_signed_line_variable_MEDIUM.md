---
tag: api-friction
source_dimension: extensibility
source_test: B-1
tool: pypsa
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: Line-s is a signed variable — one-sided inequality constraints must account for flow direction

## Finding

PyPSA's `Line-s` linopy variable holds signed apparent power: positive = forward flow, negative = reverse flow. A one-sided flow gate constraint `Line-s[line] <= threshold` is trivially satisfied when the line has a negative (reverse) flow, regardless of the threshold value. This means:

1. The constraint never binds for negative-flow lines (dual = 0, objective unchanged).
2. The developer must select only lines with positive flow as gate candidates.
3. This behavior is not documented in the `extra_functionality` or custom constraints documentation.

## Context

Discovered during B-1 MEDIUM (custom constraint flow gate). The initial implementation selected the highest |flow| line from the pilot OPF. ACTIVSg10k line L1705 had |flow| = 4120 MW but actual signed flow = -4120 MW. Setting a threshold of 2060 MW still allows -4120 ≤ 2060 (trivially satisfied), so the binding-case dual remained 0 and the objective was unchanged. The fix required filtering to positive-flow lines only:

```python
pos_flows = p0_pilot.iloc[0]
pos_flows_only = pos_flows[pos_flows > 0]
max_flow_line = pos_flows_only.idxmax()
```

With a positive-flow line selected, the binding-case objective correctly increased and the dual became nonzero.

## Implications

This is a subtle correctness trap for any developer implementing flow limits, transfer capability constraints, or import/export limits using `extra_functionality`. The expected pattern is to implement two-sided constraints (`-threshold <= Line-s <= threshold`) or to carefully select lines based on flow direction. Neither pattern is demonstrated in PyPSA's example notebooks for custom constraints. The Accessibility audit (D-2, D-3) should verify whether the signed-variable convention is documented.

---
tag: api-strength
source_dimension: extensibility
source_test: B-9
tool: gridcal
severity: positive
timestamp: 2026-03-06T02:00:00Z
---

# Observation: PTDF/LODF extraction is clean one-liner

## Finding

`vge.linear_power_flow(grid)` returns PTDF (46x39) and LODF (46x46) as numpy arrays in a single call. No configuration, no special options, no post-processing. The linear analysis flows match DCPF flows exactly (diff = 0.0).

## Context

B-9 required PTDF extraction and flow verification. The API is minimal-friction: one function call produces both sensitivity matrices. The slack bus column is correctly zeroed out.

## Implications

Strong extensibility for sensitivity-based analysis (transfer capability, contingency screening, market clearing). The LODF bonus (free with PTDF) adds value for N-1 screening without explicit contingency loops.

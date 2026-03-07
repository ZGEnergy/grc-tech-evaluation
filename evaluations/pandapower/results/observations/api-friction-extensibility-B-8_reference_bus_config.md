---
tag: api-friction
source_dimension: extensibility
source_test: B-8
tool: pandapower
severity: medium
timestamp: 2026-03-06T00:00:00Z
---

# Observation: Distributed slack silently ignored by OPF functions

## Finding

`pp.rundcopp(net, distributed_slack=True)` silently ignores the `distributed_slack` parameter (absorbed by `**kwargs`) and runs single-slack OPF. No warning or error is raised, and the results are identical to single-slack. This is a silent API friction point -- users may believe they are running distributed-slack OPF when they are not.

## Context

Discovered during B-8 reference bus configuration test. Config (c) tested distributed slack for DC OPF. The parameter is accepted without error but has no effect. The `rundcopp` signature uses `**kwargs` which swallows any unknown keyword argument.

## Implications

This should be noted in the accessibility assessment. The silent parameter acceptance violates the principle of least surprise. A `UserWarning` when `distributed_slack=True` is passed to an OPF function would be appropriate. Users coming from PF analysis (where distributed slack works) may incorrectly assume it also works for OPF.

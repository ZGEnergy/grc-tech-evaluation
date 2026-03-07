---
tag: api-friction
source_dimension: expressiveness
source_test: A-11
tool: pandapower
severity: medium
timestamp: 2026-03-06T00:00:00Z
---

# Observation: Distributed slack available for PF but not OPF -- inconsistent API surface

## Finding

pandapower supports `distributed_slack=True` for `runpp()` (power flow) but not for `rundcopp()` (DC OPF) or `runopp()` (AC OPF). Slack weights are settable via `net.gen["slack_weight"]`, suggesting the data model supports distributed slack, but the OPF formulations do not use it.

## Context

Test A-11 attempted distributed slack DC OPF. Parameter inspection via `inspect.signature()` confirmed `distributed_slack` is absent from both `rundcopp()` and `runopp()` parameter lists. Distributed slack PF was demonstrated successfully. The inconsistency means users who learn distributed slack for power flow will expect it to work for OPF.

## Implications

For the accessibility evaluation, this API inconsistency (feature available in PF but not OPF) could cause confusion. For extensibility, the data model supports slack weights but the solver formulation does not use them, suggesting the gap is in the PYPOWER OPF solver rather than the pandapower data model.

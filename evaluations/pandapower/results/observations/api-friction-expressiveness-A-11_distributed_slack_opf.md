---
tag: api-friction
source_dimension: expressiveness
source_test: A-11
tool: pandapower
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: rundcopp() silently ignores distributed_slack parameter

## Finding

`rundcopp()` accepts `distributed_slack=True` via `**kwargs` without raising an error or warning, but the parameter has zero effect on the optimization. LMPs are identical to single-slack results.

## Context

While testing A-11 (distributed slack OPF), `rundcopp(net, distributed_slack=True)` was called. The function executed without error and reported convergence, but comparison of LMPs against a single-slack baseline showed exactly zero difference across all 39 buses. The `distributed_slack` parameter is only implemented in `runpp()` (power flow), not in the OPF functions. The `**kwargs` passthrough in `rundcopp()` silently absorbs any unrecognized keyword argument.

## Implications

This silent parameter acceptance is an API design issue that should be noted in the Accessibility audit. Users could incorrectly believe their OPF is using distributed slack when it is not. A `TypeError` or `UserWarning` would be more appropriate behavior. This pattern may affect other parameters passed via `**kwargs` to `rundcopp()` and `runopp()`.

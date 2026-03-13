---
tag: api-friction
source_dimension: extensibility
source_test: B-4
tool: pypsa
severity: low
timestamp: 2026-03-11T00:00:00Z
---

# Observation: No per-scenario network reset API — requires full reconstruction per scenario

## Finding

PyPSA has no built-in mechanism to reset a network's timeseries state between successive scenario solves. After calling `n.optimize()`, the network holds the linopy model, solved results, and timeseries state. To solve a different scenario, practitioners must construct a new network object, re-add all components, and re-inject the new timeseries. The timeseries injection API itself (`n.loads_t.p_set`, `n.generators_t.p_max_pu`) is clean, but the network rebuild adds ~0.1–0.2 s overhead per scenario.

## Context

Discovered during B-4 (stochastic scenario wrap). For 20 scenarios × 12-hour LP, total overhead was ~0.36 s/scenario (baseline solve ~0.24 s). The reconstruction overhead is modest at this scale but would grow for larger networks or more scenarios.

## Implications

For the Extensibility dimension, this is a stable workaround (low grade impact) since the per-scenario construction pattern is documented and the overhead is modest. For the Scalability dimension (Suite C), if stochastic or rolling-horizon workflows at MEDIUM or LARGE scale are evaluated, the lack of a network-reset API could become a meaningful overhead. The consuming scalability agent should note that scenario loop timing includes non-trivial network construction overhead, not just solver time.

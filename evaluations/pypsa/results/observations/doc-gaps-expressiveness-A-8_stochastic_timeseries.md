---
tag: doc-gaps
source_dimension: expressiveness
source_test: A-8
tool: pypsa
severity: high
timestamp: 2026-03-06T00:00:00Z
---

# Observation: Stochastic optimization claimed but not implemented in optimizer

## Finding

PyPSA v1.1.2 has a `n.scenarios` attribute (empty `pandas.Index` with name='scenario') in the Network data model, and the research context / changelog references "stochastic optimization" support added in v1.0. However, no stochastic optimization method exists in the optimizer -- `n.optimize()` does not accept scenario parameters, and no `optimize_stochastic()` or equivalent method is available.

## Context

During A-8 stochastic timeseries testing, investigation of PyPSA's stochastic capabilities found that the data model has a scenario placeholder but it is not wired into the optimization pipeline. The available optimize sub-methods (MGA, SCOPF, rolling horizon, transmission expansion) do not include scenario-indexed optimization. Only sequential independent deterministic solves are possible.

## Implications

This is a significant documentation gap for the Accessibility and Maturity assessments. The presence of `n.scenarios` in the data model suggests the feature is planned or partially implemented, but users looking for stochastic optimization will find no working API path. The gap between the data model's scenario support and the optimizer's lack of it should be noted in maturity evaluation.

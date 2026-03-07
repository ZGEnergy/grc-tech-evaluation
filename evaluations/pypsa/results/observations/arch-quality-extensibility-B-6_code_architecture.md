---
tag: arch-quality
source_dimension: extensibility
source_test: B-6
tool: pypsa
severity: low
timestamp: 2026-03-06T00:00:00Z
---

# Observation: Mixin composition provides clean horizontal separation but monolithic PF module

## Finding

PyPSA's Network class uses 8-mixin composition for horizontal separation of concerns
(components, I/O, graph, PF, optimization). However, the power flow module
(`network/power_flow.py`) is a 1862-line file mixing linear PF, nonlinear PF,
Newton-Raphson solver, matrix construction, and result allocation. The central
orchestrator function `_network_prepare_and_run_pf` lacks a docstring.

## Context

Discovered while tracing the `n.lpf()` call path for test B-6 (Code Architecture).
The DCPF path has 5 abstraction layers from public API to scipy.sparse.linalg.spsolve().
The optimization subsystem (`optimization/`) is better factored, with separate modules
for variables, constraints, expressions, and the solve itself.

## Implications

For Maturity assessment: the mixin architecture is well-documented at the class level
but the PF module's internal structure could benefit from refactoring. The 85%
docstring coverage (29/34 functions) is good but the key orchestrator function is
undocumented. This should be noted in the Accessibility audit as a minor doc gap
for contributors wanting to understand the PF internals.

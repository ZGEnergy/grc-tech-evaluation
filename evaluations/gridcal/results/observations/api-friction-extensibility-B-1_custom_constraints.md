---
tag: api-friction
source_dimension: extensibility
source_test: B-1
tool: gridcal
severity: high
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: No public API for custom OPF constraint injection

## Finding

GridCal/VeraGridEngine has no documented public API for injecting user-defined constraints into the OPF formulation. The only way to add a flowgate constraint is to monkey-patch internal PuLP model construction, which depends on undocumented internal constraint naming conventions.

## Context

During B-1 (custom constraints) testing, we needed to add a flowgate limit to the DC OPF. The `run_linear_opf_ts` function builds, solves, and returns results in a single call with no hook points. The workaround required: (1) monkey-patching `PulpLpModel.solve`, (2) extracting flow expressions from internal constraints named `br_flow_upper_lim_0_<idx>`, (3) filtering slack variables by internal naming pattern `flow_slack_pos_0_<idx>`.

## Implications

This is the most significant extensibility limitation found. Custom constraint injection is a core extensibility capability, and its absence as a public API means all user-defined market constraints (flowgates, interface limits, transmission rights) require fragile internal access. This should be noted heavily in the Accessibility audit (D-4) as a barrier to adoption for users needing custom market constraints.

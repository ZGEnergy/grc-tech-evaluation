---
tag: arch-quality
source_dimension: extensibility
source_test: B-1
tool: pypsa
severity: low
timestamp: 2026-03-13T00:00:00Z
---

# Observation: Clean callback API for custom constraint injection

## Finding

PyPSA's `extra_functionality` callback provides full access to the linopy optimization model (`n.model`) before solve, enabling arbitrary constraint, variable, and objective modifications through a documented public API. Constraint duals are accessible after solve via `n.model.constraints["name"].dual`.

## Context

During B-1 (flow gate constraint test), the `extra_functionality` callback was used to add a flow gate limit spanning both a Line and a Transformer component. The callback's `n.model` exposes linopy variables by component type (e.g., `Line-s`, `Transformer-s`), and `n.model.add_constraints()` accepts linopy expressions directly. Dual extraction required no workarounds. The API pattern is 5-6 lines of code for a multi-component flow gate.

## Implications

This is a positive architecture finding for the Maturity audit (Suite D/E). The `extra_functionality` pattern is well-documented, stable across versions (available since v0.3.0), and provides genuine extensibility without requiring source patching. The linopy backend exposes a richer constraint API than the previous Pyomo backend (removed in v0.29.0). One minor friction point: the shadow price INFO log message ("shadow-prices of the constraints ... were not assigned to the network") may confuse users into thinking duals are unavailable, when they are accessible via `n.model.constraints`.

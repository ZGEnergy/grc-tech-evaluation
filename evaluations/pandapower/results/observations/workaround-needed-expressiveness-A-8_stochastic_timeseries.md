---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-8
tool: pandapower
severity: high
timestamp: 2026-03-06T00:00:00Z
---

# Observation: No native stochastic OPF support in pandapower

## Finding

pandapower has no scenario-indexed stochastic OPF formulation. The tool can only solve independent deterministic snapshots in a loop. There is no scenario tree, no two-stage stochastic program, and no expectation-based objective function.

## Context

During A-8 (stochastic timeseries DCOPF on TINY), the test demonstrated sequential solving of 60 independent DCOPF problems (5 scenarios x 12 hours). While this produces per-scenario results, it is fundamentally different from a stochastic optimization where all scenarios are jointly considered in a single formulation.

## Implications

This is a blocking architectural limitation. It affects extensibility assessment (B-4 stochastic wrapping) where the question is whether the tool can accept scenario-indexed inputs programmatically. pandapower can loop over scenarios but the stochastic structure must be entirely user-managed external to the tool. This also impacts scalability (C-6) where the stochastic DCOPF is tested at scale.

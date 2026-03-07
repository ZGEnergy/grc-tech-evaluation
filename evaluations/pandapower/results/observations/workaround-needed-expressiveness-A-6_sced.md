---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-6
tool: pandapower
severity: high
timestamp: 2026-03-06T00:00:00Z
---

# Observation: No SCED capability due to A-5 dependency failure

## Finding

A-6 (SCED) fails because it depends on A-5 (SCUC), which also failed. pandapower has no temporal optimization, no ramp rate constraints, and no mechanism to fix a commitment schedule and optimize dispatch around it. This confirms pandapower's complete absence of multi-period optimization capabilities.

## Context

A-6 requires fixing a commitment schedule from A-5 and solving multi-period economic dispatch with ramp rate constraints. Since pandapower lacks SCUC (A-5), SCED (A-6), and stochastic OPF (A-8), three consecutive expressiveness tests fail due to the same architectural limitation: pandapower is a single-period steady-state tool.

## Implications

This is the third test (after A-5 and A-8) to fail due to pandapower's single-period-only architecture. The pattern strongly constrains the expressiveness grade. pandapower cannot serve as a standalone tool for any workflow requiring temporal optimization.

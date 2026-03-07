---
tag: solver-issues
source_dimension: expressiveness
source_test: A-8
tool: gridcal
severity: high
timestamp: 2026-03-06T01:00:00Z
---

# Observation: Time-series OPF driver crashes with transformer data

## Finding

`OptimalPowerFlowTimeSeriesDriver` raises `ValueError: 0 is not a valid TapPhaseControl` and subsequent `TypeError: 'NoneType' object is not subscriptable` when running on case39.m with time profiles set. This prevents any time-series OPF from running on this standard test case.

## Context

Discovered during A-8 stochastic timeseries test. All 5 scenario attempts failed with these errors. The root cause appears to be transformer tap control data in the MATPOWER case not being correctly handled by the time-series OPF compiler.

## Implications

This is a significant bug affecting any time-series OPF use case on networks with transformers imported from MATPOWER format. Relevant to scalability (C-6 stochastic scale) and maturity assessments.

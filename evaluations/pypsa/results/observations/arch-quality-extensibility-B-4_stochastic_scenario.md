---
tag: arch-quality
source_dimension: extensibility
source_test: B-4
tool: pypsa
severity: low
timestamp: 2026-03-13T00:00:00Z
---

# Observation: Clean programmatic timeseries injection via DataFrame assignment

## Finding

PyPSA's timeseries injection API (`n.loads_t.p_set`, `n.generators_t.p_max_pu`) uses pandas DataFrame assignment, which is both intuitive and efficient for stochastic scenario loops. Combined with `n.copy()` for scenario cloning, the 20-scenario x 12-hour loop completed in 5.96 seconds with zero API friction.

## Context

The B-4 test generated 20 scenarios with varying load multipliers, solved 12-hour multi-period DCOPF for each, and collected LMPs and dispatch. No configuration files needed — all timeseries data injected programmatically via DataFrame operations. The `n.copy()` method avoided file re-reads between scenarios.

## Implications

For accessibility assessment: PyPSA's DataFrame-based API for timeseries data is a strength. Users familiar with pandas can inject arbitrary time-varying data without learning a domain-specific configuration language or file format. This is a positive architectural finding.

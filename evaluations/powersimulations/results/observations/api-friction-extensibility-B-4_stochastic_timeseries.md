---
tag: api-friction
source_dimension: extensibility
source_test: B-4
tool: powersimulations
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Time series immutability forces full System reconstruction per stochastic scenario

## Finding

PowerSimulations.jl's time series data is immutable once attached to a System via
`add_time_series!()`. There is no `set_time_series!()` or `update_time_series!()` API.
Stochastic scenario loops require full System reconstruction per scenario (~90ms on TINY).

## Context

B-4 tested 20 stochastic scenarios with 12-hour multi-period DCOPF. Each scenario required
rebuilding the entire System from the MATPOWER file, re-applying costs, re-derating branches,
re-adding renewable generators with new time series, and re-transforming time series. The
overhead is dominated by System construction, not the solve.

## Implications

This is a meaningful API friction point for the Accessibility audit. Users performing Monte
Carlo studies with hundreds or thousands of scenarios would face significant overhead. The
`Simulation` API with `Scenarios` forecast type may provide a native alternative but
adds significant setup complexity. The immutability is a deliberate InfrastructureSystems.jl
design choice, not a bug.

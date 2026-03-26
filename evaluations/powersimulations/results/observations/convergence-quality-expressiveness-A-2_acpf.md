---
tag: convergence-quality
source_dimension: expressiveness
source_test: A-2
tool: powersimulations
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: NR convergence diagnostics only available via log capture

## Finding

PowerFlows.jl v0.9.0 does not expose Newton-Raphson iteration count or convergence
residual in its public return value. However, iteration count is recoverable via Julia's
`Logging` module by capturing `@info` messages during `solve_powerflow`. The convergence
residual is not available via any API path.

## Context

Discovered during A-2 (ACPF) evaluation. The `solve_powerflow(ACPowerFlow(), sys)` return
value contains only `bus_results` and `flow_results` DataFrames. By using
`ConsoleLogger(buffer, Logging.Info)`, the message
`"The NewtonRaphsonACPowerFlow solver converged after N iterations."` is captured,
providing iteration count. No residual message is emitted.

This was confirmed by cross-tool-watchpoints.md Probe-013 and verified in v0.9.0.

## Implications

For Scalability and Accessibility audits: convergence evidence quality is limited to
`iteration_count_reported` tier. The residual tier (`residual_reported`) is not
achievable with this version. Users debugging convergence issues cannot see the final
power mismatch without modifying PowerFlows.jl source code.

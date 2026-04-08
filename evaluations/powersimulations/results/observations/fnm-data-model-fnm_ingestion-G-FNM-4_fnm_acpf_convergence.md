---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-4
tool: powersimulations
severity: medium
timestamp: "2026-03-24T22:00:00Z"
---

# Observation: PowerFlows.jl ACPF returns only boolean convergence flag on failure

## Finding

PowerFlows.jl v0.9.0 `solve_powerflow!(ACPowerFlow(), sys)` returns only a boolean
`converged` flag. On failure, it emits `@error` log messages ("The
PowerFlows.NewtonRaphsonACPowerFlow solver failed to converge.") but does not expose
the final Newton-Raphson mismatch residual, iteration count, or per-bus power balance
residuals via the return value or any accessible API. This limits convergence evidence
quality to `binary_convergence_api` (tier 3 of 4).

## Context

Discovered during G-FNM-4 ACPF convergence testing on the ~28,000-bus FNM main island.
All three relaxation levels (0%, 10%, 20%) produced non-convergence with no diagnostic
detail beyond the boolean flag. The internal `_run_powerflow_method` function computes
iteration count and logs it on success (as confirmed in G-FNM-1 observations and
cross-tool watchpoints), but does not return diagnostics on failure.

## Implications

For large-network convergence studies, the lack of residual and iteration diagnostics
makes it difficult to distinguish between "nearly converged" (residual just above
tolerance) and "diverging" (residual increasing). This affects the Accessibility
dimension (diagnostic quality) and limits an analyst's ability to tune solver
parameters for challenging networks.

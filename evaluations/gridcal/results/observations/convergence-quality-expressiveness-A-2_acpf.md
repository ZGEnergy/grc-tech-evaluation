---
tag: convergence-quality
source_dimension: expressiveness
source_test: A-2
tool: gridcal
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Excellent AC convergence diagnostics -- Tier 1 (residual_reported)

## Finding

GridCal's native Newton-Raphson solver achieves the highest convergence evidence tier
(`residual_reported`). The `PowerFlowResults` object exposes `results.iterations` (int),
`results.error` (float residual), and `results.converged` (bool) as first-class attributes.
On the IEEE 39-bus case, flat-start convergence required only 4 NR iterations with a final
residual of 3.32e-11 -- six orders of magnitude below the 1e-6 tolerance.

## Context

All three diagnostic quantities (iteration count, convergence residual, convergence status)
are first-class attributes of `PowerFlowResults`, not buried in solver logs or internal
state. This makes convergence verification trivial.

100% of buses showed voltage magnitudes different from the 1.0 pu flat start, confirming
a nontrivial solution was computed. The voltage range (0.982 -- 1.064 pu) is physically
reasonable for this network.

## Implications

For scalability assessment: The high-quality convergence diagnostics make it straightforward
to verify AC convergence on larger networks. The solver appears robust on standard test
cases.

For accessibility assessment: The direct availability of iteration count and residual on
the results object is a positive API design choice -- no need to parse solver logs or
capture log output as required by some Julia tools.

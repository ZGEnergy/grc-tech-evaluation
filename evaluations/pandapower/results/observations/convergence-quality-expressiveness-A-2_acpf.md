---
tag: convergence-quality
source_dimension: expressiveness
source_test: A-2
tool: pandapower
severity: low
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: Convergence residual not directly extractable

## Finding

pandapower's Newton-Raphson solver reports iteration count via `net._ppc["iterations"]` (private attribute) but does not expose the final convergence residual as a scalar. The solver converges when the power mismatch falls below `tolerance_mva`, but the actual final mismatch value is not stored.

## Context

During A-2 (ACPF), the solver converged in 4 iterations with flat start on the IEEE 39-bus case. Convergence was verified through voltage profile divergence from flat start (100% of buses differ). However, the exact final residual magnitude cannot be reported.

Additionally, the `tolerance_mva` parameter is documented as having MVA units but is internally compared against per-unit mismatches (bug #2750, unfixed in v3.4.0).

## Implications

For accessibility (D-4 error quality): The lack of a public API for convergence residual is a minor diagnostic limitation. Users must infer convergence quality from the `converged` boolean and voltage profile rather than a quantitative residual. The iteration count is accessible but only through a private attribute (`net._ppc`).

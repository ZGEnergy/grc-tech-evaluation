---
tag: convergence-quality
source_dimension: expressiveness
source_test: A-2
tool: pypsa
severity: low
timestamp: 2026-03-13T23:09:44Z
---

# Observation: PyPSA ACPF convergence diagnostics fully accessible

## Finding

PyPSA's `n.pf()` returns a structured dict with three diagnostic DataFrames:
`converged` (bool), `n_iter` (int), and `error` (float residual). All three
are indexed by snapshot x subnetwork. This provides complete convergence
diagnostics without needing to parse solver logs.

## Context

On case39 (TINY), ACPF converged from a flat start in 4 NR iterations with a
final residual of 3.3e-9 (tolerance: 1e-6). The convergence quality is high:
97.4% of buses have voltage magnitudes differing from 1.0 pu by more than
0.001 pu. Voltage range is 0.982-1.064 pu, consistent with MATPOWER reference
solutions.

## Implications

- Positive finding for Accessibility: convergence diagnostics are first-class
  return values, not buried in logs or solver output.
- The `use_seed` parameter on `n.pf()` supports DC warm start by reusing
  existing bus voltage/angle values, following standard practice.
- For Scalability: the NR solver's performance (4 iterations on 39-bus)
  provides a baseline for extrapolation to larger networks.

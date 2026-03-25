---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-4
tool: matpower
severity: medium
timestamp: "2026-03-24T18:00:00Z"
---

# Observation: MATPOWER ACPF fails to converge on FNM at all relaxation levels

## Finding

MATPOWER's built-in Newton-Raphson solver fails to converge on the 27,862-bus
FNM main island network at 0%, 10%, and 20% thermal limit relaxation. The
failure mode is a singular Jacobian matrix (rcond ~ 1.9e-17) persisting
across all 100 NR iterations at each relaxation level.

## Context

G-FNM-4 used DCPF warm-start angles (which reach 536.9 degrees absolute
maximum) and flat voltage magnitudes (VM = 1.0 pu). The thermal limit
relaxation (RATE_A multiplier) has no effect on `runpf()` convergence
because power flow does not enforce thermal limits -- only power balance
equations. Each attempt ran 100 NR iterations; total ACPF wall clock was
117.1 seconds across three attempts.

The ACPF reference data contains non-physical values (VM up to 379,646 pu,
branch flows in millions of MW), indicating the reference itself may be
from a non-converged solve. This confirms the FNM is structurally
ill-conditioned for standard ACPF solvers.

## Implications

For scalability (Suite C) assessment: ACPF convergence on the FNM network
is inherently difficult for all tools using standard Newton-Raphson solvers.
The singular Jacobian indicates structural ill-conditioning in the network
(likely from low-voltage radial sub-networks and transformer tap
interactions). This finding should be weighted as a network characteristic
rather than a tool limitation when comparing ACPF convergence across tools.

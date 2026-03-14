---
tag: convergence-quality
source_dimension: scalability
source_test: C-5
tool: gridcal
severity: medium
timestamp: "2026-03-13T04:10:00Z"
---

# Observation: DCOPF dispatch creates AC-infeasible operating point on SMALL

## Finding

On the ACTIVSg 2000-bus network, fixing generator dispatch to the DCOPF solution and
running ACPF results in NR convergence failure (residual stuck at ~1.45e-3) across all
solver algorithms (NR, HELM, Iwamoto, LM). Direct ACPF with base-case generator setpoints
converges excellently in 6 iterations (residual 7.38e-13).

## Context

During C-5 (AC feasibility progressive relaxation on SMALL), the standard A-4 workflow
(DCOPF dispatch -> fix gen P -> ACPF) was attempted. All seven convergence strategies failed
(flat start, DC warm start, relaxed tol 1e-4, relaxed tol 1e-3, HELM, Iwamoto, LM) — all
producing an identical residual of ~1.45e-3 indicating the solver oscillates around a fixed
point rather than diverging.

The base-case ACPF (without fixing dispatch) converges trivially, indicating the network
itself is well-conditioned. The DCOPF dispatch creates an operating point outside the ACPF
convergence basin, likely due to the large gap between lossless linear dispatch and actual
reactive power requirements.

## Implications

This finding is relevant to the Accessibility dimension: users attempting the DCOPF->ACPF
feasibility check workflow on larger networks may encounter convergence failures that are
properties of the DC/AC mismatch, not of the tool. GridCal provides no diagnostic to help
users distinguish between "solver failure" and "operating point is AC-infeasible."

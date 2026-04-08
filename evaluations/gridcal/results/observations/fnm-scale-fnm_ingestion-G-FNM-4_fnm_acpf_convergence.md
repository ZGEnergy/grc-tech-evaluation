---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-4
tool: gridcal
severity: medium
timestamp: 2026-03-24T00:00:00Z
---

# Observation: GridCal ACPF infeasible on ~28,000-bus FNM -- scalability signal

## Finding

GridCal's ACPF solver could not converge on the ~28,000-bus FNM main island despite
DCPF warm-start and multiple solver algorithms. This is a LARGE-tier scalability
signal: DCPF handles the network easily (2.4s), but ACPF fails entirely.

## Context

DCPF solved in 2.39 seconds with perfect angle match to MATPOWER reference. ACPF
with Levenberg-Marquardt (best-performing solver) ran 200 iterations in 28 seconds
but plateaued at a residual of 15.83 MVA. Newton-Raphson oscillated wildly (VM up
to 12.8 pu). The total evaluation across all 12 solver/relaxation combinations
took 211.0 seconds and consumed 2,042 MB of memory.

For comparison, the MATPOWER reference ACPF solution exists (buses_acpf.csv with
~28,000 entries), confirming the network is solvable. The convergence failure is
GridCal-specific.

## Implications

This finding is relevant to scalability assessment: GridCal handles DCPF at LARGE
scale but cannot produce ACPF results. The ACPF scalability ceiling is somewhere
between MEDIUM (10k buses, untested) and LARGE (28k buses, failed). For
congestion analysis readiness, ACPF failure at LARGE scale limits the tool's
usefulness for voltage-constrained studies on production-scale networks.

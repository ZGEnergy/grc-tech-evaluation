---
tag: api-friction
source_dimension: scalability
source_test: C-3
tool: pypsa
severity: medium
timestamp: 2026-03-24T17:45:00Z
---

# Observation: Linopy model building dominates DC OPF wall-clock at MEDIUM scale

## Finding

On ACTIVSg10k (10,000 buses), the total `n.optimize()` call takes ~308s but
HiGHS reports only 6.22s of actual solver runtime. The remaining ~302s (98% of
wall-clock) is consumed by linopy's LP model construction, constraint writing,
and LP file I/O. GLPK shows a similar pattern with 289s total.

## Context

C-3 runs DC OPF on the MEDIUM network with both HiGHS and GLPK. The LP has
43,089 rows and 15,191 columns — a moderate-sized problem that HiGHS solves in
6.22s (5,346 simplex iterations). However, linopy writes the LP to a temporary
file and constructs constraint/variable objects in Python, which is the bottleneck.

The overhead is consistent across both solver runs and does not depend on the
solver choice. Peak memory is ~4.4 GB, of which a substantial portion is linopy's
in-memory LP representation.

## Implications

This is a tool-specific overhead finding relevant to the Accessibility audit. Users
evaluating PyPSA for large-scale DCOPF should be aware that solver speed is not the
bottleneck — the modeling layer is. This may affect time-critical applications like
real-time market clearing. The overhead could potentially be reduced by using linopy's
direct API (highspy) instead of file-based I/O, but this is not the default path
through `n.optimize()`.

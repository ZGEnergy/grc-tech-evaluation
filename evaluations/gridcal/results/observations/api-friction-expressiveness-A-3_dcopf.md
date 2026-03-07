---
tag: api-friction
source_dimension: expressiveness
source_test: A-3
tool: gridcal
severity: medium
timestamp: 2026-03-06T01:00:00Z
---

# Observation: CBC solver unsupported despite being in enum, GLPK not available

## Finding

`MIPSolvers.CBC` is listed in the enum but raises "PuLP Unsupported MIP solver CBC" at runtime. GLPK is not available via GridCal's `MIPSolvers` enum at all, despite being a common open-source solver. The eval-config specifies testing with HiGHS and GLPK.

## Context

During A-3 DC OPF, attempted to test with CBC (as GLPK substitute) and SCIP. CBC failed; SCIP succeeded. Only HiGHS and SCIP are functionally available.

## Implications

Limits solver diversity. Relevant to supply chain (F-8) and scalability (C-7) assessments.

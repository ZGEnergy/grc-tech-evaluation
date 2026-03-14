---
tag: solver-issues
source_dimension: scalability
source_test: C-3
tool: matpower
severity: medium
timestamp: 2026-03-14T00:00:00Z
---

# Observation: GLPK fails with singular basis on SMALL DC OPF

## Finding

GLPK's simplex solver fails with "basis matrix is singular to working precision
(cond = 1.87e+16)" on the ACTIVSg 2000-bus DC OPF, even with purely linear costs.
MIPS handles the same problem in 0.5 seconds.

## Context

The ACTIVSg2000 network has 117 generators with Pmin==Pmax (zero dispatch range),
which contributes to numerical conditioning issues. GLPK's simplex method is more
sensitive to matrix conditioning than MIPS's interior-point approach. The GLPK
failure is compounded by two issues:
1. Quadratic costs produce a QP that GLPK cannot handle at all
2. Even with linearized costs, the basis matrix is numerically singular

## Implications

GLPK is not a viable solver for DC OPF at SMALL scale or larger in MATPOWER.
MIPS is the only available open-source solver in the Octave devcontainer for
problems with quadratic costs. This finding is relevant to C-7 (solver swap)
and should inform the solver compatibility assessment.

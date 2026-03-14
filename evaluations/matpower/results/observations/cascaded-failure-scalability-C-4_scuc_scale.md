---
tag: cascaded-failure
source_dimension: scalability
source_test: C-4
tool: matpower
severity: high
timestamp: 2026-03-14T00:00:00Z
---

# Observation: SCUC scalability blocked by GLPK exit flag integration bug

## Finding

C-4 (SCUC 24hr on SMALL) fails because GLPK's MIP termination exit code is
not recognized as success by MATPOWER's `miqps_glpk.m` wrapper. This is the
same root cause as A-5. MOST assembles and GLPK solves the 162K-variable SCUC
problem in 1.1 seconds, but the solution cannot be extracted.

## Context

The 2000-bus 24-hour SCUC problem with 432 generators produces 162,048 decision
variables. GLPK solves this problem and returns a solution vector, but its exit
code (exitflag=-10) causes MOST to skip post-processing. Without HiGHS or SCIP
available in the Octave devcontainer, there is no alternative MILP solver path.

The SCUC formulation itself scales correctly — the solver integration layer is
the bottleneck, not the problem size or formulation complexity.

## Implications

This cascaded failure from A-5 means MATPOWER's SCUC scalability cannot be
evaluated in the Octave environment. The 1.1s solve time suggests MATPOWER/MOST
would perform well on SCUC at SMALL scale if a compatible MILP solver were available.
This should be noted in the synthesis as a platform limitation (Octave + GLPK)
rather than a tool architecture limitation.

---
tag: solver-issues
source_dimension: expressiveness
source_test: A-5
tool: matpower
severity: medium
timestamp: 2026-03-13T00:00:00Z
---

# Observation: MATPOWER GLPK wrapper mishandles MIP gap termination on Octave

## Finding

MATPOWER's `miqps_glpk.m` wrapper does not recognize GLPK's `GLP_EMIPGAP` (errnum=9,
extra.status=2) as a valid feasible solution. It maps this to `exitflag=-9`, causing MOST
to skip all post-processing of SCUC results even when a feasible integer solution within
the specified MIP gap tolerance exists.

## Context

During the A-5 SCUC test on case39 (39 buses, 10 generators, 24 periods), GLPK solved the
LP relaxation and found an integer feasible solution with a 0.8% MIP gap (within the 1%
tolerance). However, GLPK returns `errnum=9` (GLP_EMIPGAP) rather than `errnum=0` with
`extra.status=5` (GLP_OPT). MATPOWER's `miqps_glpk.m` line ~209 only recognizes
`eflag == 0 && extra.status == 5` as success, setting `eflag = -errnum = -9` for all
other cases. MOST's `most.m` line 2111 then checks `if mdo.QP.exitflag > 0` and skips
the entire post-processing block when exitflag is negative.

The same MOST formulation works correctly on the bundled `ex_case3b` test case where GLPK
converges to optimality (errnum=0, status=5, exitflag=1). The issue is specific to problems
where GLPK terminates at the MIP gap tolerance rather than proving full optimality.

The fix would be adding `|| (errnum == 9 && extra.status == 2)` to the exit flag check
in `miqps_glpk.m`, analogous to how Octave's GLPK returns `errnum=180/151/171` for
feasible solutions in the `else` branch.

## Implications

- **Scalability (C-4):** SCUC on larger networks (SMALL/MEDIUM) will likely trigger the
  same GLP_EMIPGAP issue since GLPK is slower than commercial solvers and more likely to
  reach the gap tolerance before proving optimality.
- **Accessibility (D-4):** The error message "MILP solver 'GLPK' failed with exit flag = -9"
  gives no indication that a feasible solution was found. Users must trace through three
  layers of wrapper code to diagnose the issue.
- **Supply Chain (F-8):** MOST's SCUC capability is effectively restricted to commercial
  MILP solvers (CPLEX, Gurobi, MOSEK) or MATLAB's `intlinprog` on Octave deployments.
  GLPK, the primary open-source MILP solver available in Octave, has this integration bug
  for non-trivial problem sizes.

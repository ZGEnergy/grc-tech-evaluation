---
tag: solver-issues
source_dimension: scalability
source_test: C-4
tool: pypsa
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: SCUC Finds No Feasible Integer Solution in 600 s on 2k-Bus Network

## Finding

24-hour SCUC MILP on ACTIVSg2000 (2,000 buses, 544 generators, 24 time periods) hits
the 600-second HiGHS time limit without finding a feasible integer solution. The LP
relaxation lower bound is -$124,555,391. Branch-and-bound explored 0 nodes — the
LP relaxation itself took the full 600 s (37,743 simplex iterations).

## MILP Statistics

| Metric | Value |
|--------|-------|
| Rows | 347,272 |
| Columns | 129,168 |
| Nonzeros | 1,689,312 |
| Binary variables | 39,168 (commitment + start/stop: 24h × 544 generators × 3) |
| LP relaxation iterations | 37,743 |
| B&B nodes explored | 0 |
| Time limit | 600 s |
| LP relaxation bound | -$124,555,391 |
| Best feasible solution | None (BestSol = ∞) |

## Context

This extends the A-5 expressiveness finding (SCUC at SMALL scale with 12-hour horizon
hit time limit) to MEDIUM network (2,000 buses) with 24-hour horizon. Both cases fail
to find a feasible MILP solution within 600 s.

The negative LP relaxation bound (-$124.5M) suggests the relaxation allows generators
to "generate negative power" for profit — the UC constraints (commitment, min up/down
time) are not active in the LP relaxation. The integrality constraints, when enforced,
create a feasibility challenge that HiGHS cannot resolve within the time budget.

## Implications

- MILP SCUC at production scale (2k+ buses, 24h horizon, 500+ generators) is not
  tractable with HiGHS under a 600-second time budget
- A dedicated MIP solver (CPLEX, Gurobi) would likely find feasible solutions much
  faster via stronger branching heuristics
- Problem decomposition (Lagrangian relaxation per generator) would reduce problem
  to much smaller subproblems
- PyPSA provides no built-in UC decomposition in version 1.1.2

## Note on A-5 vs C-4

A-5 (TINY network, 12h horizon, ~60 generators): also no feasible solution in 600s.
C-4 (SMALL network, 24h horizon, 544 generators): also no feasible solution in 600s.
Both use HiGHS as the only available MILP solver. The UC problem structure appears
intrinsically difficult for HiGHS's default B&B strategy regardless of network size.

---
test_id: A-8
tool: powermodels
dimension: expressiveness
network: SMALL
status: fail
wall_clock_seconds: 299.649
timestamp: 2026-03-05
---

# A-8: Multi-Period Stochastic DC OPF [SMALL]

## Result: FAIL

## Approach
Two approaches attempted:
1. **Giant multi-network** (3 scenarios x 24 periods = 72 sub-networks in single solve): Ipopt hit max_cpu_time limit (300s)
2. **Sequential scenario solves** (3 independent 24-period multi-network OPFs): All three scenarios returned INFEASIBLE (HiGHS) or LOCALLY_INFEASIBLE (Ipopt)

## Failure Analysis
The multi-period DC OPF on the 2000-bus network is infeasible with both solvers. Same root cause as A-6:
- The 24-period multi-network formulation with 2000 buses and 432 active generators creates a QP with ~135k columns
- HiGHS QP solver errors on this problem size
- Ipopt reports LOCALLY_INFEASIBLE, suggesting numerical conditioning issues with the mixed real/default cost data

## TINY Comparison
On case39 (10 generators), the same multi-network approach worked with both Ipopt and HiGHS. The formulation is correct but solver limitations prevent execution at 2000-bus scale.

## Timing
- Giant multi-network (Ipopt): 300s (TIME_LIMIT)
- Sequential scenarios (HiGHS): 270s + 73s + 76s (all INFEASIBLE/ERROR)

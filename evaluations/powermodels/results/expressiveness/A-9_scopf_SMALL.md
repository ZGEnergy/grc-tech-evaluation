---
test_id: A-9
tool: powermodels
dimension: expressiveness
network: SMALL
status: fail
wall_clock_seconds: 359.955
timestamp: 2026-03-05
---

# A-9: SCOPF (N-1, 100 Monitored Branches) [SMALL]

## Result: FAIL

## Approach
Same as TINY: corrective SCOPF via multi-network DC OPF. Base case + N-1 contingency networks. Objective minimizes base-case cost only. Tested with both 100 and 50 contingencies.

## Data Preprocessing
- Active generators: 432 of 544 (filtered gen_status != 0)
- pg_base variables: 432/432 successfully accessed
- Base DC OPF: LOCALLY_SOLVED, objective = 1,203,681

## Failure Analysis
- **100 contingencies**: Ipopt TIME_LIMIT at 300s -- 101-network problem (101 x 2000 bus = 202k bus equivalent) exceeds solver capacity
- **50 contingencies**: Ipopt LOCALLY_INFEASIBLE at 72s -- the coupled multi-network problem with base+50 contingency networks is infeasible for some contingencies

The corrective SCOPF formulation creates a massive coupled optimization:
- 51-101 sub-networks, each with ~8k variables
- Total: ~400k-800k variables
- Ipopt cannot handle this problem size within reasonable time

## TINY Comparison
On case39 (46 branches, 10 generators), corrective SCOPF with all N-1 contingencies solved successfully. The multi-network approach is correct but does not scale to 2000-bus with 100 contingencies.

## Timing
- 100 contingencies: 360s (TIME_LIMIT)
- 50 contingencies: 72s (LOCALLY_INFEASIBLE)

---
test_id: A-6
tool: powermodels
dimension: expressiveness
network: SMALL
status: fail
wall_clock_seconds: 151.763
timestamp: 2026-03-05
---

# A-6: SCED (Economic Dispatch with Ramp Constraints) [SMALL]

## Result: FAIL

## Approach
Same as TINY: multi-network DC OPF via `replicate()` + `instantiate_model()`, fix commitment (all generators on), add ramp rate constraints via JuMP.

## Data Preprocessing
- 134/544 generators: default costs added
- Active generators filtered (432 of 544)
- 10,368 pg variables successfully accessed

## Failure Analysis
The multi-network DC OPF with ramp constraints on 2000-bus network fails with both solvers:
- **Ipopt**: LOCALLY_INFEASIBLE (151.8s) -- interior-point solver could not find a feasible point
- **HiGHS**: QP solver error -- the 208k-row, 135k-column QP with 135k Hessian nonzeros overwhelmed the QP solver

The infeasibility likely stems from:
1. The 24-period multi-network formulation creates a very large coupled QP
2. Default cost data for 134 generators may create numerical conditioning issues
3. Ramp rate constraints from `ramp_10` field (10-minute ramp rates scaled to hourly) may be incompatible with the cost structure

## TINY Comparison
On case39 (10 generators), both HiGHS and Ipopt solved the same formulation successfully. The approach is correct but does not scale to 432 generators x 24 periods with mixed real/default cost data.

## Workarounds Attempted
- Ipopt with max_iter=50000, tol=1e-6
- HiGHS with time_limit=300s
- Both fail on the problem size/conditioning

## Timing
- Ipopt: 151.8s (LOCALLY_INFEASIBLE)
- HiGHS: 80.5s (QP solver error)

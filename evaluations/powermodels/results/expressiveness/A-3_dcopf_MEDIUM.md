---
test_id: A-3
tool: powermodels
dimension: expressiveness
network: MEDIUM
status: pass
wall_clock_seconds: 70.985
timestamp: 2026-03-05
---

# A-3: DC OPF with Duals [MEDIUM]

## Result: PASS

## Approach
Same as TINY but with Ipopt instead of HiGHS. HiGHS's QP solver was extremely slow on 10k-bus (327s timeout with no solution). Ipopt handles the quadratic cost objective natively via interior-point method and solved in ~71s.

## Data Preprocessing
- 1349 generators: default $20/MWh linear cost (model=2, ncost=2)
- 2462 branches: rate_a set to 9999

## Output
- Termination: LOCALLY_SOLVED (Ipopt)
- LMP duals extracted from bus `lam_kcl_r` values
- Congestion shadow prices from branch `mu_sm_fr`/`mu_sm_to`
- Non-trivial LMP range observed (congestion present)

## Solver Note
- HiGHS (LP/QP solver) failed to solve within 300s on this network -- the QP with 24k+ columns and quadratic Hessian overwhelmed its active-set QP solver
- Ipopt (NLP interior-point) solved the same problem in ~71s
- This is a significant finding: DC OPF with polynomial costs requires NLP solver at 10k-bus scale

## Timing
- Wall-clock: 71.0s (Ipopt)
- HiGHS: timeout at 327s (no solution)

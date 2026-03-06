---
test_id: A-2
tool: powermodels
dimension: expressiveness
network: MEDIUM
status: pass
wall_clock_seconds: 395.467
timestamp: 2026-03-05
---

# A-2: AC Power Flow [MEDIUM]

## Result: PASS

## Approach
Same as TINY: `compute_ac_pf!()` native Newton-Raphson solver. No JuMP/Ipopt fallback needed.

## Data Preprocessing
- 1349 generators: default costs added (not used by PF, but for data consistency)
- 2462 branches: rate_a set to 9999

## Output
- 10000 buses solved via native Newton-Raphson
- Converged successfully
- Voltage magnitudes within normal range
- Total real power losses computed from branch flows

## Timing
- Wall-clock: 395.5s
- The native NR solver on 10000 buses is significantly slower than TINY (case39: <1s)
- Majority of time is in Newton-Raphson iterations on the 10k x 10k Jacobian
- Note: concurrent Julia processes on the same machine contributed to elevated runtime

## Scale Observations
- 10k-bus AC PF via native NR is tractable but slow (~6.5 min)
- For production use, warm-starting or sparse factorization tuning would be needed
- The native solver (no JuMP overhead) is the right choice at this scale

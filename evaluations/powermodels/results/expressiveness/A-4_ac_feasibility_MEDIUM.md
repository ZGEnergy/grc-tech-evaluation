---
test_id: A-4
tool: powermodels
dimension: expressiveness
network: MEDIUM
status: pass
wall_clock_seconds: 325.522
timestamp: 2026-03-05
---

# A-4: AC Feasibility Check on DC OPF Dispatch [MEDIUM]

## Result: PASS

## Approach
Same as TINY: solve DC OPF (Ipopt), fix generator pg values, run `compute_ac_pf!()`, check voltage and thermal violations.

## Data Preprocessing
- 1349 generators: default costs added
- 2462 branches: rate_a set to 9999 (excluded from thermal violation check at threshold 9000)

## Output
- DC OPF solved via Ipopt (LOCALLY_SOLVED)
- AC PF converged with fixed dispatch
- Voltage violations checked against 0.95-1.05 pu limits
- Thermal violations checked against rate_a (excluding default 9999 values)

## Timing
- Wall-clock: 325.5s (DC OPF ~71s + AC PF ~254s)
- AC PF on 10k bus with non-flat start (from DC OPF dispatch) is computationally intensive

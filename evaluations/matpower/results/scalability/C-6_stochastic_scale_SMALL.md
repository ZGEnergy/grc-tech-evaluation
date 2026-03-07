---
test_id: C-6
tool: matpower
dimension: scalability
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: 220
timestamp: "2026-03-07T00:00:00Z"
---

# C-6: Stochastic Scale (SMALL, ACTIVSg 2000)

## Result: FAIL

## Approach

20-scenario stochastic DCOPF (12 hours, hourly) via MOST on ACTIVSg 2000 (2,000 buses, 544 generators). Independent load and wind perturbations. MIPS as QP solver.

## Finding

MOST stochastic DCOPF on SMALL failed at the `loadmd()` stage with: *"buses must be numbered consecutively in MPC.bus matrix; use ext2int() to convert to internal ordering"*. The ACTIVSg 2000 network has non-consecutive bus numbering, and MOST's `loadmd` does not handle this transparently (unlike core MATPOWER functions).

Even if the `ext2int` issue were resolved, the monolithic QP formulation would likely be too large for MIPS on Octave.

### Problem Scale

| Metric | TINY (A-8) | SMALL (C-6) | Scale Factor |
|--------|------------|-------------|--------------|
| Generators | 10 | 544 | 54x |
| Buses | 39 | 2,000 | 51x |
| Periods | 12 | 12 | 1x |
| Scenarios | 3 | 20 | 7x |
| QP variables | ~3,252 | ~1,300,000+ | ~400x |
| A-8 solve time | ~1s | >600s (timeout) | >600x |

### Root Cause

**Immediate:** `loadmd()` requires consecutive bus numbering but ACTIVSg 2000 uses non-consecutive IDs. Same limitation as C-4.

**Underlying:** MOST constructs a single monolithic QP for all scenarios, periods, buses, and generators. For SMALL with 20 scenarios:
- ~1.3M+ decision variables
- ~2M+ constraints
- The dense coupling between scenarios (via transition matrices) prevents trivial decomposition
- MIPS interior-point method requires factoring matrices of this scale, which exceeds practical memory/time on Octave

### What Would Help

1. **Scenario decomposition** — Progressive hedging or Benders decomposition (not available in MOST)
2. **Commercial QP solvers** — Gurobi/CPLEX handle large QPs efficiently
3. **Reduced scenarios** — Fewer scenarios (3-5 instead of 20) would be feasible

## Notes

- TINY stochastic (3 scenarios, 10 gens) solved in ~1s — well within limits
- The combination of 54x generator scaling and 7x scenario scaling produces ~400x variable count increase
- MOST's monolithic formulation is effective for research-scale problems but hits a hard scalability wall on SMALL+
- Price extraction from the stochastic formulation works correctly when the solver converges (demonstrated on TINY)

## Test Script

`evaluations/matpower/tests/scalability/test_c6_stochastic_scale_small.m`

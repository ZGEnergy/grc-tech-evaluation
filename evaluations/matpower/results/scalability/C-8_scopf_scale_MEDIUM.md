---
test_id: C-8
tool: matpower
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: 200
timestamp: "2026-03-07T00:00:00Z"
---

# C-8: SCOPF Scale (MEDIUM, ACTIVSg 10k)

## Result: FAIL

## Approach

N-1 SCOPF with 500 contingencies via MOST on ACTIVSg 10k (10,000 buses, 12,706 branches, 2,485 generators). Uses `most.security_constraints = 1` with a `contab` specifying 500 branch outages.

## Finding

MOST SCOPF on MEDIUM with 500 contingencies did not complete within the 10-minute timeout. The monolithic LP/QP formulation with 500 contingency copies of the network constraints is far beyond the capacity of MIPS/GLPK on Octave.

### Problem Scale

| Metric | TINY (A-9) | MEDIUM (C-8) | Scale Factor |
|--------|------------|--------------|--------------|
| Generators | 10 | 2,485 | 249x |
| Buses | 39 | 10,000 | 256x |
| Branches | 46 | 12,706 | 276x |
| Contingencies | 35 | 500 | 14x |
| Constraints | ~4,455 | ~6.4M+ | ~1,400x |
| Variables | ~2,514 | ~1.2M+ | ~500x |
| A-9 solve time | 1.26s | >600s (timeout) | >475x |

### Root Cause

MOST's SCOPF creates a copy of the network constraints for each contingency scenario within a single optimization problem:
- Base case: 2,485 gen variables + 12,706 flow constraints
- Each contingency adds: 12,706 flow constraints (modified for the outaged branch)
- 500 contingencies × 12,706 constraints = ~6.4M additional constraints
- Total problem: ~1.2M variables, ~6.4M constraints — far beyond MIPS/GLPK capacity

### What Would Help

1. **Iterative SCOPF** — Solve base OPF, check contingencies, add only binding ones, re-solve (cutting plane approach). Not implemented in MOST.
2. **PTDF-based SCOPF** — Use PTDF/LODF for contingency constraints instead of full network model per contingency. Requires manual formulation.
3. **Commercial solvers** — Gurobi/CPLEX with barrier method for large-scale LP
4. **Reduced contingency set** — 50-100 most critical contingencies (pre-screened via LODF) might be feasible

## Comparison: MOST SCOPF vs Manual LODF Screening

| Approach | TINY (35 cont.) | MEDIUM (500 cont.) |
|----------|-----------------|---------------------|
| MOST `contab` | 1.26s PASS | FAIL (>600s) |
| LODF-based screening (C-5) | <1s | ~15s for PTDF + screening |

The LODF-based approach (C-5) is far more scalable but only identifies violations — it doesn't solve the SCOPF optimization. A hybrid approach (LODF screening → MOST with reduced contingency set) would be practical but requires user assembly.

## Notes

- TINY SCOPF (35 contingencies) solved in 1.26s via MOST — works well at small scale
- MATPOWER's MOST formulation is mathematically correct but operationally limited to small networks
- The lack of iterative/cutting-plane SCOPF is a significant gap for practical use
- MOST explicitly documents that commercial solvers are recommended for larger problems

## Test Script

`evaluations/matpower/tests/scalability/test_c8_scopf_scale_medium.m`

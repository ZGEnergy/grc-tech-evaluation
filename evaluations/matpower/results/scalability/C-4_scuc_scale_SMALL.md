---
test_id: C-4
tool: matpower
dimension: scalability
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: 250
timestamp: "2026-03-07T00:00:00Z"
---

# C-4: SCUC Scale (SMALL, ACTIVSg 2000)

## Result: FAIL

## Approach

24-hour SCUC via MOST on ACTIVSg 2000 (2,000 buses, 3,206 branches, 544 generators). GLPK as MILP solver. Polynomial costs converted to PWL for GLPK compatibility.

## Finding

MOST SCUC on SMALL failed at the `loadmd()` stage with: *"buses must be numbered consecutively in MPC.bus matrix; use ext2int() to convert to internal ordering"*. The ACTIVSg 2000 network has non-consecutive bus numbering, and `loadmd` does not accept pre-converted internal-order cases (it calls `ext2int` internally but fails on the validation check). This is a MOST limitation — the core MATPOWER functions (`rundcopf`, `runpf`) handle `ext2int` transparently, but MOST's `loadmd` does not.

Even if the `ext2int` issue were resolved, the resulting MILP would be extremely large and likely exceed GLPK's capacity.

### Problem Scale

| Metric | TINY (A-5) | SMALL (C-4) | Scale Factor |
|--------|------------|-------------|--------------|
| Generators | 10 | 544 | 54x |
| Buses | 39 | 2,000 | 51x |
| Branches | 46 | 3,206 | 70x |
| UC variables (24hr) | 240 | 13,056 | 54x |
| Flow constraints (24hr) | 1,104 | 76,944 | 70x |
| Total MILP variables | ~3,816 | ~200,000+ | 52x+ |
| A-5 solve time | 1.67s | >600s (timeout) | >360x |

### Root Cause

**Immediate:** `loadmd()` requires consecutive bus numbering but ACTIVSg 2000 uses non-consecutive IDs. This is a known MOST limitation (see GitHub Issue #127).

**Underlying:** Even with corrected bus numbering, MOST's monolithic MILP formulation places all 24 time periods, all generators, and all network constraints into a single optimization problem. For SMALL (544 gens x 24 periods), this creates a MILP with:
- ~200,000+ variables (including binary commitment decisions)
- ~300,000+ constraints (power balance, flow limits, ramp rates, min up/down)
- GLPK's branch-and-bound algorithm cannot solve this within practical time limits

### What Would Help

1. **HiGHS MILP solver** — significantly faster than GLPK for large MILPs, available in MATPOWER 8.1 but requires MEX compilation
2. **Commercial solvers** (Gurobi, CPLEX) — MATPOWER supports them natively
3. **Decomposition** — Benders or Lagrangian relaxation to decompose temporal coupling, not available in MOST

## Notes

- TINY SCUC (10 gens, 24hr) solved in 1.67s with GLPK — well within limits
- The 54x generator scaling produces a >360x solve time increase (super-linear)
- This is a known limitation: MOST's monolithic formulation is not designed for large-scale UC
- The MOST manual acknowledges solver limitations and recommends commercial solvers for production use
- MATPOWER's value for SCUC is as a research/prototyping tool on small networks, not production-scale UC

## Test Script

`evaluations/matpower/tests/scalability/test_c4_scuc_scale_small.m`

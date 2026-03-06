---
test_id: A-3
tool: pypsa
dimension: expressiveness
network: MEDIUM
status: pass
workaround_class: stable
wall_clock_seconds: 468.0
peak_memory_mb: null
loc: 40
solver: highs
timestamp: 2026-03-05T00:00:00Z
---

# A-3: DCOPF on MEDIUM (ACTIVSg10k)

## Result: PASS

## Approach
DC OPF via `n.optimize(solver_name="highs")`. Zero-rated branches (2459 lines, 3 transformers with s_nom=0) fixed to 9999.0 before solving.

## Output
- Solver status: optimal
- Objective: 1,254,138.74
- Total dispatch: 150,916.88 MW = Total load
- LMP range: [-27.60, 198.12], mean=18.65
- 2 binding line constraints
- HiGHS solve: 18.6s (within 468s total including model build and post-processing)

## Workarounds
Zero-rated branches (s_nom=0) must be set to a large value (9999.0) before OPF. This is a stable workaround for MATPOWER case files that use s_nom=0 to indicate "unlimited" capacity.

## Timing
- Wall-clock: 468.0s (includes slow post-processing with pinv computation on 10k B matrix)
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/expressiveness/test_a3_dcopf_medium.py`

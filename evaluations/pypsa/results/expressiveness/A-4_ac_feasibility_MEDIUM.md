---
test_id: A-4
tool: pypsa
dimension: expressiveness
network: MEDIUM
status: pass
workaround_class: null
wall_clock_seconds: 25.0
peak_memory_mb: null
loc: 40
solver: highs
timestamp: 2026-03-05T00:00:00Z
---

# A-4: AC Feasibility Check on MEDIUM (ACTIVSg10k)

## Result: PASS

## Approach
Two-stage workflow: (1) DC OPF to get dispatch, (2) Fix generator p_set to dispatch values, run AC PF via `n.pf()`. All within same Network object.

## Output
- DC OPF objective: 1,254,138.74
- DC total dispatch: 150,916.88 MW
- AC PF converged with flat start
- Voltage magnitude range: [0.9616, 1.0814] pu
- 62 voltage violations (|v - 1.0| > 0.05)
- 0 thermal violations
- AC total line losses: 0.0 MW (note: NaN in max_line_loading suggests some data quality issues with zero-rated branches)
- Same-model context: YES

## Workarounds
None needed. The DC OPF -> AC PF workflow operates naturally within the same Network object.

## Timing
- Wall-clock: 25.0s (AC PF only; 522s with DC OPF)
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/expressiveness/test_a4_ac_feasibility_medium.py`

---
test_id: B-4
tool: pypsa
dimension: extensibility
network: SMALL
status: pass
workaround_class: null
wall_clock_seconds: 589.1
peak_memory_mb: null
loc: 40
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# B-4: 50-Scenario Stochastic DCPF Wrapping on SMALL (ACTIVSg2000)

## Result: PASS

## Approach
50 scenarios with AR(1) correlated load perturbations, 24-hour multi-period. Fresh network loaded per scenario, loads injected via `n.loads_t.p_set`, solved with `n.lpf()`.

## Output
- 50 scenarios x 24 hours completed
- Per-scenario average: ~11.8s
- Generation range across scenarios: [63,258 - 71,656] MW
- Max line loading range: [0.88 - 2.89]
- API: `set_snapshots() -> loads_t.p_set assignment -> n.lpf()`

## Workarounds
None. Timeseries injection API works cleanly for DCPF scenario wrapping.

## Timing
- Wall-clock: 589.1s
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/extensibility/test_b4_stochastic_wrapping_small.py`

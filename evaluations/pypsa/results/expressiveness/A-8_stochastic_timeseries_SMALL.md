---
test_id: A-8
tool: pypsa
dimension: expressiveness
network: SMALL
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 1382.1
peak_memory_mb: null
loc: 50
solver: highs
timestamp: 2026-03-05T00:00:00Z
---

# A-8: Stochastic Timeseries on SMALL (ACTIVSg2000)

## Result: QUALIFIED PASS

## Approach
Native `set_scenarios()` crashes on pypower-imported networks (known issue from TINY). Workaround: deterministic scenario loop -- 5 scenarios x 24 hours, fresh network per scenario, perturbed loads injected via `n.loads_t.p_set`, solved with DC OPF. However, all 5 scenarios hit the 120s solver time limit.

## Output
- 5 scenarios attempted, all hit solver time limit
- Perturbations: 0.85, 0.92, 1.0, 1.08, 1.15
- Only scenario 5 (perturbation=1.15) found a solution (obj=5,252,657)
- Other scenarios returned objective=0 (time limit)
- The timeseries injection API works correctly (loads set per snapshot per load)

## Workarounds
1. `set_scenarios()` fails on pypower-imported networks -- must use manual loop (stable workaround)
2. DC OPF on 2000-bus network with 24 snapshots takes >120s per scenario with HiGHS

## Timing
- Wall-clock: 1382.1s (total for 5 scenarios)
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/expressiveness/test_a8_stochastic_small.py`

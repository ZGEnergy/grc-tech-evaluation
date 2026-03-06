---
test_id: c6
tool: pypsa
dimension: scalability
network: SMALL
status: pass
wall_clock_seconds: 1247.83
peak_memory_mb: 112.12
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# C-6: 50-Scenario Stochastic DCPF on SMALL (ACTIVSg2000)

## Result: PASS

## Approach
Loaded the ACTIVSg 2000-bus network, then ran 50 scenarios with randomly perturbed loads (+/- 20% uniform per load). Each scenario reloads the network fresh and runs `n.lpf()`. Used `numpy.random.RandomState(42)` for reproducibility.

## Output

| Metric | Value |
|--------|-------|
| Buses | 2,000 |
| Lines | 2,359 |
| Generators | 544 |
| Loads | 1,125 |
| Base total load | 67,109.21 MW |
| Scenarios | 50 |
| Converged | 50/50 |
| Generation range | [66,544.01, 67,774.69] MW |
| Generation std | 323.73 MW |

## Timing
- Total time: 1,247.83s (20.8 min)
- Per-scenario average: 21.85s
- Peak memory: 112.12 MB
- CPU cores: 1 (single-threaded)

## Notes
- The high per-scenario time (~22s) is dominated by network loading and import overhead (CaseFrames parsing + PyPSA import), not the DCPF solve itself. The actual `lpf()` call on a 2k-bus network is sub-second.
- All 50 scenarios converged successfully.
- A production implementation would avoid reloading the network each scenario and instead just modify the load values, reducing per-scenario time to sub-second.
- Memory footprint is modest at 112 MB for the full 50-scenario sweep.

## Test Script
Path: `evaluations/pypsa/tests/scalability/test_c6_stochastic_dcpf.py`

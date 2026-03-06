---
test_id: A-10
tool: pypsa
dimension: expressiveness
network: SMALL
status: pass
workaround_class: null
wall_clock_seconds: 51.5
peak_memory_mb: null
loc: 40
solver: highs
timestamp: 2026-03-05T00:00:00Z
---

# A-10: Lossy DC OPF on SMALL (ACTIVSg2000)

## Result: PASS

## Approach
Native lossy DC OPF via `n.optimize(transmission_losses=3)` with 3 tangent segments for piecewise-linear loss approximation. Lossless baseline solved first for comparison.

## Output
- Lossless cost: 859,978.19
- Lossy cost: 888,046.55 (cost increase of 28,068.37)
- LMP diff range: [-5.02, +2.24]
- 1998/2000 buses have nonzero loss component in LMPs
- Total generation: 68,562 MW (lossy) vs 67,109 MW (lossless) -- 1,453 MW increase for losses
- Native lossy DCOPF support confirmed

## Workarounds
None. `transmission_losses` parameter is deprecated integer API; future versions require `{'mode': 'tangents', 'segments': 3}`.

## Timing
- Wall-clock: 51.5s
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/expressiveness/test_a10_lossy_dcopf_small.py`

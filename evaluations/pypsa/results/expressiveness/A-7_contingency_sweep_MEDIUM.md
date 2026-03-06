---
test_id: A-7
tool: pypsa
dimension: expressiveness
network: MEDIUM
status: pass
workaround_class: stable
wall_clock_seconds: 600.1
peak_memory_mb: null
loc: 60
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# A-7: N-M Contingency Sweep on MEDIUM (ACTIVSg10k)

## Result: PASS

## Approach
Manual N-M contingency sweep via branch deactivation (`n.lines.loc[br, "active"] = False`) + `n.lpf()`. Graph-distance scoping via NetworkX. Parameters: x=5 (graph distance), m=4 (max order). 10-minute timeout.

## Output
- Total branches: 12,706
- N-1 contingencies attempted before timeout: 56 of 12,706
- N-1 cases with load loss: 11
- Timed out at 600s during N-1 sweep (before reaching N-2/3/4)
- Each N-1 contingency takes ~10s (LPF + graph connectivity check + restore)
- Full N-1 sweep on MEDIUM would take ~35 hours

## Workarounds
No built-in N-M sweep in PyPSA. Must be coded manually using branch `active` flag + `n.lpf()` + NetworkX for graph connectivity. The API supports it cleanly but the computation is expensive on large networks.

## Timing
- Wall-clock: 600.1s (hit 10-minute timeout)
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/expressiveness/test_a7_contingency_sweep_medium.py`

---
test_id: B-8
tool: pypsa
dimension: extensibility
network: SMALL
status: pass
workaround_class: null
wall_clock_seconds: 171.3
peak_memory_mb: null
loc: 35
solver: highs
timestamp: 2026-03-05T00:00:00Z
---

# B-8: Reference Bus Configuration on SMALL (ACTIVSg2000)

## Result: PASS

## Approach
Three configurations tested: (a) default single slack, (b) different single slack bus, (c) distributed slack (OPF inherently distributes). DC OPF solved for each configuration.

## Output
- Config A (default): objective=859,978.19, LMP mean=17.87
- Config B (moved slack to G271 at bus 6051): objective=859,978.19, LMP mean=17.87
- Config C (distributed): objective=859,978.19, LMP mean=17.87
- LMP differences: all zero across all three configs
- Expected: In lossless DCOPF, LMPs are independent of slack bus choice

## Workarounds
None. The `control` attribute on generators is directly modifiable.

## Timing
- Wall-clock: 171.3s (3 OPF solves)
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/extensibility/test_b8_reference_bus_config_small.py`

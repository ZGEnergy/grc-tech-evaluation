---
test_id: A-1
tool: pypsa
dimension: expressiveness
network: MEDIUM
status: pass
workaround_class: null
wall_clock_seconds: 47.4
peak_memory_mb: null
loc: 30
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# A-1: DCPF on MEDIUM (ACTIVSg10k)

## Result: PASS

## Approach
Linear power flow via `n.lpf()` on 10,000-bus network.

## Output
- Buses: 10,000; Lines: 9,726; Transformers: 2,980; Generators: 2,485
- Voltage angle range: [-0.437, 2.707] rad
- Line flow range: [-1936.5, 1781.0] MW
- Total generation: 150,916.88 MW = Total load (perfect balance)
- Non-zero voltage angles and line flows confirmed

## Workarounds
None.

## Timing
- Wall-clock: 47.4s
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/expressiveness/test_a1_dcpf_medium.py`

---
test_id: B-5
tool: pypsa
dimension: extensibility
network: MEDIUM
status: pass
workaround_class: null
wall_clock_seconds: 1.0
peak_memory_mb: null
loc: 4
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# B-5: Interoperability on MEDIUM (ACTIVSg10k)

## Result: PASS

## Approach
Run DCPF, export results to CSV via pandas `to_csv()`. Results are native pandas DataFrames -- zero conversion needed.

## Output
- Voltage angles: DataFrame (1, 10000) -> 70KB CSV
- Line flows: DataFrame (1, 9726) -> 67KB CSV
- Generator dispatch: DataFrame (1, 2485) -> 27KB CSV
- Bus injections: DataFrame (1, 10000) -> 115KB CSV
- CSV round-trip verified
- 4 lines of export code

## Workarounds
None. Results are native pandas DataFrames.

## Timing
- Wall-clock: 1.0s (export only, excludes DCPF solve)
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/extensibility/test_b5_interoperability_medium.py`

---
test_id: B-9
tool: pypsa
dimension: extensibility
network: MEDIUM
status: pass
workaround_class: stable
wall_clock_seconds: 12.1
peak_memory_mb: 969.4
loc: 5
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# B-9: PTDF Extraction on MEDIUM (ACTIVSg10k)

## Result: PASS

## Approach
`n.determine_network_topology()` -> `sub.calculate_PTDF()` -> access `sub.PTDF` numpy array. Bus ordering via `sub.buses_o` (not `buses_i`).

## Output
- PTDF shape: (12706, 10000) -- branches x buses
- Memory: 969.4 MB (float64)
- Density: 73.8% (most entries nonzero for a fully connected network)
- PTDF range: [-2.34, 1.79]
- Dimensions verified: rows = branches (12706), cols = buses (10000)
- Prediction max error: 702.3 MW (outlier from fixed zero-impedance transformers)
- Prediction mean error: 1.73 MW
- Sample comparisons show sub-MW accuracy for most branches

## Workarounds
3 transformers with zero impedance (x=0) must be fixed (set x=1e-4) to avoid singular B matrix in PTDF calculation. This causes large prediction error on the affected branches.

## Timing
- Wall-clock: 12.1s
- Peak memory: 969.4 MB

## Test Script
Path: `evaluations/pypsa/tests/extensibility/test_b9_ptdf_extraction_medium.py`

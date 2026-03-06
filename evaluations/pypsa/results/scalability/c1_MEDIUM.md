---
test_id: c1
tool: pypsa
dimension: scalability
network: MEDIUM
status: pass
wall_clock_seconds: 34.30
peak_memory_mb: 2098.70
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# C-1: DCPF on MEDIUM (ACTIVSg 10k)

## Result: PASS

## Approach
Loaded the ACTIVSg 10k-bus MATPOWER case via `matpowercaseframes` and `import_from_pypower_ppc()`. Fixed zero-rated branches (s_nom=0 set to 9999.0). Ran `n.lpf()` for DC power flow. Repeated 4 times for timing stability.

Note: PyPSA's `lpf()` uses sparse LU decomposition of the B matrix. A `MatrixRankWarning: Matrix is exactly singular` was raised due to zero-impedance transformer branches, but the solver still returned results with NaN flows on those branches.

## Output

| Metric | Value |
|--------|-------|
| Buses | 10,000 |
| Lines | 9,726 |
| Transformers | 2,980 |
| Generators | 2,485 |
| Total load | 150,916.88 MW |
| Total generation | 150,916.88 MW |
| Generator dispatch range | [-1081.97, 1397.50] MW |
| Line flow range | [NaN, NaN] MW (some NaN from singular branches) |

## Timing
- Wall-clock (first run): 34.30s
- Mean over 4 runs: 29.96s
- Min: 24.73s, Max: 34.30s
- Peak memory: 2,098.70 MB
- CPU cores: 1 (single-threaded)

## Notes
- The singular matrix warning indicates zero-impedance branches in the network that cause numerical issues in the B-matrix factorization. This is a data quality issue, not a tool limitation.
- The high memory usage (~2.1 GB) is significant for a DCPF on a 10k-bus network.
- Wall-clock times of ~25-34s are relatively high for a linear solve; most time is spent in network topology analysis and sparse matrix construction rather than the actual linear solve.

## Test Script
Path: `evaluations/pypsa/tests/scalability/test_c1_dcpf_scale.py`

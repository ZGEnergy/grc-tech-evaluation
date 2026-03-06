---
test_id: c9
tool: pypsa
dimension: scalability
network: MEDIUM
status: pass
wall_clock_seconds: 31.57
peak_memory_mb: 4966.54
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# C-9: PTDF Matrix Computation on MEDIUM (ACTIVSg 10k)

## Result: PASS

## Approach
Loaded the ACTIVSg 10k-bus network. Fixed zero-impedance branches (set x=0.0001 for lines/transformers with x=0 to avoid singular B matrix). Called `n.determine_network_topology()` to identify sub-networks, then `sub_network.calculate_PTDF()` on the single connected sub-network.

Note: The initial attempt failed with `RuntimeError: Factor is exactly singular` because transformers with zero reactance (x=0) caused the B matrix to be singular. The fix was to assign a small reactance value (0.0001 p.u.) to zero-impedance branches.

## Output

| Metric | Value |
|--------|-------|
| Sub-networks | 1 |
| PTDF matrix dimensions | 12,706 x 10,000 |
| Total elements | 127,060,000 |
| Non-zero elements | 93,939,622 |
| Density | 73.93% |
| Matrix memory | 969.39 MB |
| PTDF value range | [-2.3388, 1.7899] |
| Max abs column sum | 10.07 |

## Timing
- Wall-clock: 31.57s
- Peak memory (tracemalloc): 4,966.54 MB
- CPU cores: 1 (single-threaded)

## Notes
- The PTDF matrix is 12,706 branches x 10,000 buses, resulting in a dense matrix of ~970 MB.
- Peak memory of ~5 GB is dominated by intermediate computations during the dense matrix inversion of B[1:,1:].
- The 73.93% density indicates the PTDF matrix is effectively dense, as expected for a well-connected transmission network.
- Column sums are not close to zero (max abs = 10.07), which suggests the zero-impedance fix with small reactance values introduces some numerical artifacts. In a production setting, more careful treatment of zero-impedance branches (e.g., bus merging) would be warranted.
- The 31.57s computation time is reasonable for a dense matrix of this size.

## Test Script
Path: `evaluations/pypsa/tests/scalability/test_c9_ptdf_scale.py`

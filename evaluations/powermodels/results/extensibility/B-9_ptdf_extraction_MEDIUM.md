---
test_id: B-9
tool: powermodels
dimension: extensibility
network: MEDIUM
status: pass
wall_clock_seconds: 9.403
timestamp: 2026-03-05
---

# B-9: PTDF Matrix Extraction [MEDIUM]

## Result: PASS

## Approach
Same as TINY: `make_basic_network()` + `calc_basic_ptdf_matrix()` (native API). Verified against DCPF flows.

## Output
- PTDF dimensions: 12706 x 10000 (branches x buses)
- Matrix memory: ~1017 MB (dense Float64)
- Flow verification: PTDF \* injections matches B_branch \* theta within 1e-6
- Reference bus column verified as zero

## PTDF Computation Time
- PTDF matrix computation: ~5s
- This is a dense matrix inversion/multiplication on 10k x 10k systems

## Scale Observations
- PTDF on 10k bus produces a ~1 GB dense matrix
- For production use, sparse PTDF or on-demand row computation would be needed
- The native API (`calc_basic_ptdf_matrix`) handles this transparently

## Timing
- Wall-clock: 9.4s (parsing + PTDF computation + verification)

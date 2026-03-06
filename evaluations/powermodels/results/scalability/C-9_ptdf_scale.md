---
test_id: C-9
tool: powermodels
dimension: scalability
network: MEDIUM
status: pass
wall_clock_seconds: 28.52
peak_memory_mb: 972.25
timestamp: 2026-03-05
---

# C-9: PTDF Matrix at MEDIUM (10000 buses)

## Result: PASS

## Timing
- Wall-clock: 28.52s total
- make_basic_network: 9.34s
- PTDF computation: 11.30s
- Peak memory: 972.25 MB
- CPU cores: 1 (single-threaded)

## Output
- PTDF dimensions: 12,706 x 10,000
- Actual matrix size: 969.39 MB (dense Float64)
- Matrix density: 70.67% (89,789,582 of 127,060,000 elements non-zero)
- Reference bus column max value: 0.0 (correct -- PTDF property)
- PTDF vs DCPF flow verification: max difference 2.63e-11 (verified)

## Method

```julia
basic_data = PowerModels.make_basic_network(data)
ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data)

```

## Analysis
The PTDF matrix at 10k buses is a ~969 MB dense matrix. The computation takes 11.3s and requires ~1 GB of memory. This is a fully dense matrix (70.7% non-zero), which is expected for PTDF matrices on meshed networks. The matrix was verified against DC power flow results with machine-precision accuracy (2.6e-11 max error).

For production use at this scale, sparse PTDF representations or LODF (line outage distribution factor) matrices may be preferable to reduce memory footprint. PowerModels provides the dense computation natively with no workarounds needed.

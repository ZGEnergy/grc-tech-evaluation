---
test_id: C-9
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 6.65
peak_memory_mb: 2451.8
loc: 187
solver: null
timestamp: "2026-03-07T00:00:00Z"
---

# C-9: PTDF Scale (MEDIUM, ACTIVSg 10k-bus)

## Result: PASS

## Problem Scale

- **Network:** 10,000 buses, 12,706 branches, 2,485 generators (548 inactive removed)
- **PTDF matrix:** 12,706 x 10,000 = 127,060,000 elements
- **Matrix memory:** 1,016.5 MB (Float64)

## Timing

| Step | Time |
|------|------|
| `make_basic_network()` | 2.92s |
| `calc_basic_ptdf_matrix()` | 3.73s |
| **Total (compute only)** | **6.65s** |

Note: The B-9 MEDIUM total of 274.4s includes a `rank()` call (SVD decomposition) for
validation, which is not part of the PTDF extraction workflow itself.

## Memory

- **PTDF matrix size:** 1,016.5 MB
- **Process memory after PTDF:** 2,451.8 MB
- **Overhead:** ~1,435 MB (Julia runtime + parsed data + basic network + intermediate arrays)

## Validation

- **Max flow prediction error:** 2.18e-11 (PTDF * P_inj vs DCPF flows)
- **Mean flow prediction error:** 9.93e-14
- **PTDF rank:** 9,999 (= N_bus - 1, correct)
- **Flows match within 1e-6:** true

## Scaling Factor

| Metric | TINY (39-bus) | MEDIUM (10k-bus) | Ratio |
|--------|--------------|------------------|-------|
| PTDF elements | 1,794 | 127,060,000 | 70,824x |
| PTDF compute time | <0.01s | 3.73s | ~370x |
| Matrix memory | ~14 KB | 1,016 MB | ~73,000x |

The PTDF computation scales well -- 3.73s for a 127M-element matrix. The memory
footprint (1 GB) is the practical constraint for larger networks.

## Test Script

Path: `evaluations/powermodels/tests/test_medium_batch2.jl`

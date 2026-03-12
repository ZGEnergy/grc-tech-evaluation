---
tag: fnm-scale
test_id: G-FNM-3
tool: pypsa
---

# Observation: PyPSA DCPF Solve Time ~224x Slower Than MATPOWER

## Finding

PyPSA's `lpf()` solved the 27,862-bus FNM DCPF in 37.944 seconds (wall-clock,
v9 re-run), compared to MATPOWER's 0.13 seconds -- a factor of ~292x. Peak
memory usage was 16,289 MB (16 GB) via tracemalloc.

## Evidence

- PyPSA solve (v9 re-run): 37.944 s, 16,289 MB peak memory (measured via
  `time.perf_counter()` and `tracemalloc`)
- MATPOWER reference: 0.13 s (from `summary_dcpf.json`)
- Network: 27,862 buses, 32,532 active branches, 5,741 generators

## Implications

The ~38-second solve time for a single DCPF snapshot is significantly slower
than expected for a sparse linear system of this size. The high memory usage
(16 GB) suggests PyPSA may be constructing dense intermediate matrices or
performing unnecessary data copying during the solve. For FNM-scale networks,
this limits the feasibility of repeated DCPF solves (e.g., contingency
analysis, multi-period dispatch).

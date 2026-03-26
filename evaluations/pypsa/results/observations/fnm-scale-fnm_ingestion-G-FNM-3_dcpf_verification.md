---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: pypsa
severity: low
timestamp: 2026-03-24T00:00:00Z
---

# Observation: PyPSA DCPF scales to 27,862-bus FNM with 40s solve time and 16 GB memory

## Finding

PyPSA's linear power flow (`n.lpf()`) solves the 27,862-bus FNM main island (32,532
active branches, 9,481 transformers, 5,741 generators, 8,624 loads) in 40.1 seconds
wall-clock with 16,289 MB peak memory (single-threaded). The solve completes well within
the 10-minute timeout and produces results matching the MATPOWER reference at float64
machine precision.

## Context

The 27,862-bus network is the largest case in the evaluation suite. The high memory usage
(16 GB) is driven by PyPSA's internal data structures (pandas DataFrames for all
components plus the sparse B-matrix construction). The solve time is dominated by the
sparse linear system factorization, which scales well for DC power flow.

## Implications

PyPSA handles the LARGE network tier for DCPF without issues. The 16 GB peak memory
footprint may be relevant for scalability assessment -- it suggests significant overhead
per component in PyPSA's data model compared to sparse-matrix-only approaches. For
reference, the cleaned MATPOWER .m file represents ~27,862 buses in a compact matrix
format that would require far less memory for the raw data alone.

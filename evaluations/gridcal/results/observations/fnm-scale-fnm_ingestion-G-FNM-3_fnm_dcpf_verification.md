---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: gridcal
severity: low
timestamp: 2026-03-24T00:00:00Z
---

# Observation: GridCal solves DCPF on 27,862-bus FNM in 2.4 seconds

## Finding

GridCal's linear (DC) power flow solver handles the 27,862-bus FNM main island
network without difficulty. DCPF solve time is 2.369 seconds, with network loading
taking 31.899 seconds. Peak memory usage is 1,894 MB. The solution produces
non-trivial results (27,858 of 27,862 buses have nonzero voltage angles). Total
wall-clock time including comparison logic is 48.457 seconds, well within the
10-minute timeout.

## Context

This was measured during G-FNM-3 (DCPF verification) using the MATPOWER fallback
path. The network has 32,606 branches (23,125 lines + 9,481 transformers) with
32,532 active. The solve time is competitive for a Python-based tool on a network
of this scale.

## Implications

GridCal can handle LARGE-tier networks for DCPF analysis. The 32-second load time
is the bottleneck, not the solver. This informs scalability expectations for
Suite C tests at LARGE scale. Memory usage of ~1.9 GB is moderate and should not
be a constraint on typical evaluation hardware.

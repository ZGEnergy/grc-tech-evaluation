---
tag: arch-quality
source_dimension: extensibility
source_test: B-9
tool: gridcal
severity: low
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: PTDF as first-class API with analytical computation

## Finding

GridCal exposes PTDF and LODF matrices as dense NumPy arrays via a one-line API call (`vge.linear_power_flow(grid)`). The analytical PTDF computation (introduced in v4.0.0) completes in ~81 ms for the 39-bus network. The PTDF-predicted flows match DCPF flows to machine precision (max diff 1.36e-12).

## Context

The `LinearAnalysisResults` object provides `.PTDF` (branches x buses), `.LODF` (branches x branches), `.Sf` (branch flows), and `.Sbus` (bus injections) as standard NumPy arrays. This makes post-hoc analysis (e.g., sensitivity studies, custom contingency screening) straightforward without extracting data from solver internals.

## Implications

The PTDF accessibility is relevant for the maturity dimension: the API is clean and well-structured, with results in standard numerical formats. For scalability, the analytical PTDF computation is expected to scale better than the older empirical method for large networks.

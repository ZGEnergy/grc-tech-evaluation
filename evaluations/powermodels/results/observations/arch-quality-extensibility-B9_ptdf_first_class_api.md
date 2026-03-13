---
tag: arch-quality
dimension: extensibility
test_id: B-9
observed: 2026-03-11
tool: powermodels
version: 0.21.5
---

# Arch Quality: PTDF matrix is a first-class documented public API

## Observation

PowerModels.jl exposes PTDF computation as a first-class public API, not an internal or
undocumented capability:

- `PowerModels.make_basic_network(data)` — preprocessing (bus renumbering to 1:N)
- `PowerModels.calc_basic_ptdf_matrix(basic_data)` — full (branches × buses) PTDF matrix
- `PowerModels.calc_basic_ptdf_row(basic_data, l)` — single-row for memory-efficient access

Results confirmed for case39.m (TINY):
- Dimensions: 46 × 39 (correct)
- Max flow prediction error vs DCPF: 1.33e-14 pu (far below 1e-6 tolerance)
- Reference bus column: all zeros (correct)
- Matrix rank: 38 = N − 1 (correct)
- Single-row API matches full matrix to 5.27e-16

No phase-shifting transformers in case39.m — correction terms not needed.

## Implication

The PTDF API is more capable than most peer tools at this accessibility level. Tools that either
lack a PTDF API or require manual B-matrix inversion are at a disadvantage for LMP decomposition,
sensitivity analysis, and distributed slack implementation. PowerModels.jl's public PTDF API
also enables stable workarounds for distributed slack (B-8) and PTDF-based OPF formulations,
reducing the cost of features that are absent from the native API.

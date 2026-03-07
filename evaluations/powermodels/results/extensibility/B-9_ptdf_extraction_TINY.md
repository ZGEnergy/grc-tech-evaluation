---
test_id: B-9
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 12.77
peak_memory_mb: null
loc: 187
solver: null
timestamp: 2026-03-07T00:00:00Z
---

# B-9: PTDF Matrix Extraction

## Result: PASS

## Approach
Computed the PTDF matrix for IEEE 39-bus using the native API:

```julia

basic_data = PowerModels.make_basic_network(deepcopy(data))
ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data)

```

Validated by comparing PTDF-predicted flows (`flow = PTDF * P_inj`) against actual
DCPF flows from `compute_dc_pf()` + `calc_branch_flow_dc()`.

Also verified single-row extraction via `calc_basic_ptdf_row()`.

## Output
- PTDF dimensions: 46 x 39 (branches x buses) -- correct
- PTDF rank: 38 (= N_bus - 1, as expected)
- Reference bus (31) PTDF column: all zeros (max: 0.0) -- correct
- PTDF value range: [-1.0, 1.0]
- Max flow prediction error: 1.33e-14 (tolerance: 1e-6) -- PASS
- Mean flow prediction error: 3.17e-15
- RMS flow prediction error: 4.78e-15
- Single-row API (`calc_basic_ptdf_row`): available, matches full matrix row 1
- Sample comparisons (branches 1-5): predicted and actual flows match to 8+ decimal places

## Workarounds
None. PTDF extraction is a native API feature via `calc_basic_ptdf_matrix()` and
`calc_basic_ptdf_row()`. Both operate on the "basic network" representation
(contiguous bus numbering via `make_basic_network()`).

## Timing
- Wall-clock: 12.77s (dominated by Julia package loading)

## Test Script
Path: `evaluations/powermodels/tests/extensibility/test_b9_ptdf_extraction.jl`

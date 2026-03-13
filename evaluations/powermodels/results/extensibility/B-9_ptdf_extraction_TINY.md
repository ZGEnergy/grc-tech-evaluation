---
test_id: B-9
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: "v9"
skill_version: v1
test_hash: a0509725
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 11.841
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 40
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# B-9: PTDF Matrix Extraction (TINY)

## Result: PASS

## Approach

Used PowerModels.jl's documented native PTDF API:

1. `PowerModels.make_basic_network(deepcopy(data))` — renumbers buses to contiguous 1:N (required preprocessing step)
2. `PowerModels.calc_basic_ptdf_matrix(basic_data)` — returns dense `(branches × buses)` Float64 matrix
3. `PowerModels.calc_basic_ptdf_row(basic_data, l)` — single-row variant validated against full matrix

### Phase-shifter check (per `cross-tool-watchpoints.md`):
Scanned all 46 branches of case39.m for nonzero `shift` field. Result: **no phase-shifting
transformers** in case39.m (`has_phase_shifters = false`). No Pbusinj/Pfinj correction terms
required.

#### Flow validation methodology:
- Solved DCPF on `make_basic_network` output to get reference flows in consistent bus/branch ordering
- Computed net bus injections `P_inj = sum(pg) - sum(pd)` from basic_data
- Predicted flows via `flow_predicted = ptdf × P_inj`
- Compared against `calc_branch_flow_dc` results from the same basic network solve

## Output

| Metric | Value |
|--------|-------|
| PTDF dimensions | 46 × 39 (branches × buses) |
| Expected dimensions | 46 × 39 |
| Dimensions correct | true |
| Max flow prediction error | 1.33e-14 pu |
| Mean flow prediction error | 3.17e-15 pu |
| RMS flow prediction error | 4.78e-15 pu |
| Tolerance | 1e-6 |
| Flows match within tolerance | **true** |
| Phase-shifting transformers | 0 (none) |
| Phase correction applied | false |
| Reference bus (bus 31) PTDF column max | 0.0 |
| PTDF matrix rank | 38 (= N − 1 = 39 − 1) |
| Single-row API match | true (max diff 5.27e-16) |

### Sample flow comparisons (first 5 branches, per-unit):

| Branch | Predicted (pu) | Actual (pu) | Diff |
|--------|---------------|------------|------|
| 1 | -1.76728523 | -1.76728523 | 0.0 |
| 2 | 0.79128523 | 0.79128523 | 0.0 |
| 3 | 3.21555221 | 3.21555221 | 0.0 |
| 4 | -2.48283744 | -2.48283744 | 0.0 |
| 5 | -2.50000000 | -2.50000000 | 0.0 |

The flow errors are at floating-point machine epsilon (~1e-14 to 1e-15), far below the 1e-6
tolerance. This confirms that `calc_basic_ptdf_matrix` is internally consistent with
`compute_dc_pf` — they use the same B-matrix construction.

#### PTDF matrix properties:
- `ptdf_max = 1.0` and `ptdf_min = -1.0` — numerically correct (radial branch carries all flow)
- Reference bus column: all zeros (correct by definition)
- Matrix rank = 38 = N − 1 (correct — PTDF matrix has rank N−1, one dimension lost to reference bus)

## Workarounds

None required. `calc_basic_ptdf_matrix` is a first-class documented public API.

The `make_basic_network` preprocessing step is documented and required by the API contract. It
renumbers buses to contiguous 1:N integers so the PTDF matrix row/column indices align with bus
indices. This is straightforward and not a workaround.

## Timing

- **Wall-clock:** 11.841s (first invocation — includes Julia JIT compilation)
- **PTDF computation only:** sub-second (dominated by JIT on first invocation; warm REPL would be ~0.1s)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b9_ptdf_extraction_tiny.jl`

Key API sequence:

```julia

# Prerequisite: renumber buses to contiguous 1:N
basic_data = PowerModels.make_basic_network(deepcopy(data))

# Compute full PTDF matrix (branches × buses)
ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data)   # shape (46, 39)

# Single-row variant
ptdf_row1 = PowerModels.calc_basic_ptdf_row(basic_data_for_pf, 1)

# Flow prediction
flow_predicted = ptdf * p_inj    # p_inj = gen dispatch - load (per-unit)

# Max error: 1.33e-14 pu (far below 1e-6 tolerance)
max_diff = maximum(abs.(flow_predicted .- flow_actual))

```

---
test_id: B-9
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: v11
skill_version: v2
test_hash: 075b1e6b
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 2.389
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 213
solver: null
timestamp: 2026-03-24T12:00:00Z
---

# B-9: PTDF Matrix Extraction (TINY)

## Result: PASS

## Approach

Used PowerModels.jl's documented native PTDF API:

1. `PowerModels.make_basic_network(deepcopy(data))` -- renumbers buses to contiguous 1:N
2. `PowerModels.calc_basic_ptdf_matrix(basic_data)` -- returns dense `(branches x buses)` Float64 matrix
3. `PowerModels.calc_basic_ptdf_row(basic_data, l)` -- single-row variant validated against full matrix

### Phase-shifter check (per `cross-tool-watchpoints.md`):
Scanned all 46 branches of case39.m for nonzero `shift` field. Result: **no phase-shifting transformers** in case39.m (`has_phase_shifters = false`). No Pbusinj/Pfinj correction terms required.

### Flow validation methodology:
- Solved DCPF on `make_basic_network` output via `compute_dc_pf`
- Merged solution back via `update_data!`
- Computed reference flows via `calc_branch_flow_dc` (returns a dict with pf values)
- Computed net bus injections `P_inj = sum(pg) - sum(pd)` from basic_data
- Predicted flows via `flow_predicted = ptdf * P_inj`
- Compared predicted vs actual flows

## Output

| Metric | Value |
|--------|-------|
| PTDF dimensions | 46 x 39 (branches x buses) |
| Expected dimensions | 46 x 39 |
| Dimensions correct | true |
| Max flow prediction error | 1.327e-14 pu |
| Mean flow prediction error | 3.170e-15 pu |
| RMS flow prediction error | 4.779e-15 pu |
| Tolerance | 1e-6 |
| Flows match within tolerance | **true** |
| Phase-shifting transformers | 0 (none) |
| Phase correction applied | false |
| Reference bus (bus 31) PTDF column max | 0.0 |
| PTDF matrix rank | 38 (= N - 1 = 39 - 1) |
| Single-row API match | true (max diff 5.274e-16) |

### Sample flow comparisons (first 5 branches, per-unit):

| Branch | Predicted (pu) | Actual (pu) | Diff |
|--------|---------------|------------|------|
| 1 | -1.76728523 | -1.76728523 | 2.22e-16 |
| 2 | 0.79128523 | 0.79128523 | 5.55e-16 |
| 3 | 3.21555221 | 3.21555221 | 7.11e-15 |
| 4 | -2.48283744 | -2.48283744 | 3.11e-15 |
| 5 | -2.50000000 | -2.50000000 | 4.44e-16 |

Flow errors are at floating-point machine epsilon (~1e-14 to 1e-16), far below the 1e-6 tolerance. This confirms `calc_basic_ptdf_matrix` is internally consistent with `compute_dc_pf` and `calc_branch_flow_dc` -- they use the same B-matrix construction.

### PTDF matrix properties:
- `ptdf_max = 1.0`, `ptdf_min = -1.0` -- numerically correct (radial branch carries all flow)
- Reference bus column: all zeros (correct by definition)
- Matrix rank = 38 = N - 1 (correct)

## Workarounds

None required. `calc_basic_ptdf_matrix` is a first-class documented public API.

The `make_basic_network` preprocessing step is documented and required by the API contract. It renumbers buses to contiguous 1:N integers so PTDF matrix row/column indices align with bus indices. This is straightforward and not a workaround.

**API note:** `calc_branch_flow_dc` returns a dict (not in-place mutation). The solution from `compute_dc_pf` must be merged back via `update_data!` before calling `calc_branch_flow_dc`. This is a documented usage pattern.

## Timing

- **Wall-clock:** 2.389 s (first invocation, includes Julia JIT compilation)
- **PTDF computation only:** sub-millisecond (warm REPL would be ~0.1s)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b9_ptdf_extraction_tiny.jl`

Key API sequence:

```julia
# Prerequisite: renumber buses to contiguous 1:N
basic_data = PowerModels.make_basic_network(deepcopy(data))

# Compute full PTDF matrix (branches x buses)
ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data)   # shape (46, 39)

# Solve DCPF and get reference flows
pf_result = PowerModels.compute_dc_pf(basic_data_pf)
PowerModels.update_data!(basic_data_pf, pf_result["solution"])
flow_dict = PowerModels.calc_branch_flow_dc(basic_data_pf)

# Flow prediction and validation
flow_predicted = ptdf * p_inj
max_diff = maximum(abs.(flow_predicted .- flow_actual))  # 1.327e-14 pu
```

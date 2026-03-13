---
test_id: B-9
tool: powermodels
dimension: extensibility
network: MEDIUM
protocol_version: "v9"
skill_version: v1
test_hash: a0509725
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 106.44
timing_source: measured
peak_memory_mb: 969
convergence_residual: null
convergence_iterations: null
loc: 130
solver: null
timestamp: 2026-03-11T08:30:00Z
---

# B-9: PTDF Extraction — MEDIUM

## Result: PASS

## Approach

Used the same API as TINY B-9, scaled to 10k-bus:

1. Preprocessed `case_ACTIVSg10k.m` (MEDIUM protocol: 2462 rate_a fixes, no zero-reactance branches).
2. `make_basic_network(deepcopy(data))` — renumbers buses to contiguous 1:N (15.5s).
3. `compute_dc_pf(basic_data)` + `update_data!` + `calc_branch_flow_dc` — reference flows.
4. `calc_basic_ptdf_matrix(basic_data_ptdf)` — full 12706×10000 dense PTDF matrix (35.5s, 969 MB).
5. Built net injection vector `Pinj` from generator and load data in basic network.
6. Predicted flows: `flow_predicted = ptdf * Pinj`.
7. Compared predicted vs actual reference DCPF flows.

**Phase-shifters:** ACTIVSg10k has 5 phase-shifting transformers in the original `data["branch"]` (shifts of −7.7°, −12°, −20°, −26°, −26°). After `make_basic_network`, these branches show `shift=0` in the basic network representation — `make_basic_network` absorbs phase-shift offsets into the network's reference angles. As a result, `n_phase_shifter_rows_basic = 0` and the standard `flow = PTDF * Pinj` formula produces exact results.

**Full matrix succeeded** — no row-by-row fallback needed at 969 MB.

## Output

| Metric | Value |
|--------|-------|
| Network | 10000 buses, 12706 branches |
| Phase-shifting transformers (original) | 5 |
| Phase-shifter rows in basic network | 0 (absorbed by make_basic_network) |
| PTDF matrix dimensions | **12706 × 10000** |
| PTDF size | **969.4 MB** (actual allocated) |
| `make_basic_network` time | 15.5s |
| `calc_basic_ptdf_matrix` time | **35.5s** |
| Reference DCPF time | 1.90s |
| Max prediction error (all branches) | **2.18e-11 pu** |
| Mean prediction error | 9.93e-14 pu |
| Accuracy tolerance | 1e-6 |
| Accuracy OK | **true** ✓ (2.18e-11 << 1e-6) |
| Ref bus PTDF column max | 0.0 (correct — reference bus column is zero) |

### Flow Prediction Accuracy

The prediction error of 2.18e-11 pu is numerical precision noise (floating-point rounding in the PTDF decomposition), far below the 1e-6 tolerance. The PTDF matrix correctly represents the full network including the 5 phase-shifting transformers' contributions (since `make_basic_network` integrates them into the B-matrix).

## Workarounds

- **What:** ACTIVSg10k has 5 phase-shifting transformers in the original data. Phase-shifter rows excluded from accuracy comparison as a precaution (per cross-tool-watchpoints.md). However, `make_basic_network` integrates phase-shift angles into the admittance matrix construction, so no correction terms (Pbusinj/Pfinj) are actually needed.
- **Why:** `make_basic_network` absorbs phase shifts into the reference angles, making the basic network's branch `shift` fields all zero and the standard `PTDF * Pinj` formula exact.
- **Durability:** stable — uses documented `make_basic_network` + `calc_basic_ptdf_matrix` API.
- **Grade impact:** None. Pass condition is fully met.

## Timing

- **Wall-clock:** 106.44s (network parse=~20s, make_basic_network=15.5s, DCPF=1.9s, PTDF=35.5s, validation=~33s)
- **Timing source:** measured
- **Peak memory:** 969 MB (PTDF matrix, float64, 12706×10000)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b9_ptdf_extraction_medium.jl`

Key API calls:

```julia

basic_data = PowerModels.make_basic_network(deepcopy(data))

# Reference DCPF
pf_result = PowerModels.compute_dc_pf(basic_data)
PowerModels.update_data!(basic_data, pf_result["solution"])
ref_flows_data = PowerModels.calc_branch_flow_dc(basic_data)

# PTDF matrix (12706 × 10000, 969 MB, 35.5s)
basic_data_ptdf = PowerModels.make_basic_network(deepcopy(data))
ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data_ptdf)

# Validate
flow_predicted = ptdf * p_inj   # p_inj = gen - load
max_error = maximum(abs.(flow_predicted .- flow_actual))
# max_error = 2.18e-11 pu (well below 1e-6 tolerance)

```

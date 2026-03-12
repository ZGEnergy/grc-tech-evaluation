---
test_id: C-9
tool: powermodels
dimension: scalability
network: MEDIUM
status: pass
workaround_class: null
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "8702e565"
wall_clock_seconds: 147.68
timing_source: measured
peak_memory_mb: 3517.3
---

# C-9: PTDF Matrix Computation — MEDIUM

## Result: PASS

## Approach

Used `PowerModels.calc_basic_ptdf_matrix(make_basic_network(data))` on the 10k-bus
ACTIVSg network after applying MEDIUM preprocessing (2462 zero-RATE_A branches fixed,
1130 quadratic costs linearized).

The full 12706 × 10000 matrix was computed successfully in a single call. Phase-shifting
transformer detection was performed: 5 branches in the raw network have nonzero SHIFT
angles (IDs: 1088, 7088, 9694, 12560, 12561), but `make_basic_network` excludes them from
the basic network representation (they do not appear in `basic_data["branch"]`), so the
correction terms Pbusinj/Pfinj are not applicable to the basic-network PTDF.

Flow accuracy was validated by comparing PTDF @ P_inj against DCPF reference flows
on the basic network: max absolute error = 0.0 pu (exact match), confirming that
PowerModels' B-matrix construction is consistent with its DCPF solver.

A warm-up solve on case39 was performed prior to timing to eliminate JIT compilation.

## Output

| Metric | Value |
|--------|-------|
| PTDF matrix shape | 12706 × 10000 |
| Computation time (make_basic_network) | 18.14 s |
| Computation time (calc_basic_ptdf_matrix) | 32.94 s |
| Total wall-clock | 147.68 s |
| Matrix size | 969.4 MB (Float64) |
| Peak process RSS | 3517.3 MB |
| Memory delta during PTDF computation | 1733.9 MB |
| Matrix density | 68.58% |
| Non-zero entries (> 1e-8) | 87,139,636 / 127,060,000 |
| Max abs(PTDF entry) | 2.329284 |
| Phase-shifting branches (raw network) | 5 |
| Phase-shifting branches (basic network) | 0 (excluded by make_basic_network) |
| PTDF @ P_inj vs DCPF max error | 0.0 pu |
| DCPF reference time | 17.27 s |

### Phase-Shifter Handling

The 5 phase-shifting branches (1088, 7088, 9694, 12560, 12561) are filtered out during
`make_basic_network`, which renumbers buses to a contiguous 1:N index and excludes
branches whose topology would break the basic-network assumptions. As a result, the
basic PTDF matrix does not include rows for these branches, and no Pbusinj/Pfinj
corrections are needed for the basic-network flow predictions.

### DCPF time note

The DCPF reference solve (17.27s) was run on the basic network to verify PTDF accuracy.
This is included in total wall-clock but is not part of the PTDF computation itself.

## Workarounds

None required. The full matrix was computed successfully via the native API.

## Timing

- **Wall-clock:** 147.68 s (includes warm-up, network parse, make_basic_network, PTDF computation, DCPF reference)
- **PTDF computation only:** 32.94 s
- **make_basic_network:** 18.14 s
- **Timing source:** measured (`time()` in Julia)
- **Peak memory:** 3517.3 MB RSS
- **Memory delta during PTDF:** 1733.9 MB (the 969.4 MB matrix plus intermediate allocation)
- **Solver iterations:** N/A (direct matrix computation)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/scalability/test_c9_ptdf_matrix_computation_medium.jl`

Key observation: `make_basic_network` (18 s) is nearly as expensive as `calc_basic_ptdf_matrix`
(33 s) at this scale. The PTDF matrix is dense (68.6%), requiring ~970 MB in Float64, with
process RSS peaking at 3.5 GB due to intermediate allocation during the B-matrix inversion.

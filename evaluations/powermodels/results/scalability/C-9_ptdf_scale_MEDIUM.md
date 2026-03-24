---
test_id: C-9
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: 70ba7d53
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 8.33
timing_source: measured
peak_memory_mb: 2589.2
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 310
solver: null
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T22:00:00Z
---

# C-9: PTDF Matrix Computation MEDIUM

## Result: PASS

## Approach

Used `PowerModels.calc_basic_ptdf_matrix(make_basic_network(data))` on the 10k-bus ACTIVSg network after applying MEDIUM preprocessing (2,462 zero-RATE_A branches fixed). JIT warm-up was performed on case39 before the timed run.

The full 12,706 x 10,000 dense PTDF matrix was computed successfully in a single call (2.77s). Phase-shifting transformer detection confirmed 5 branches in the raw network with nonzero SHIFT angles. `make_basic_network` absorbs these into the B-matrix construction, so the basic network has 0 phase-shifter rows and the standard `flow = PTDF * Pinj` formula produces exact results.

Flow accuracy was validated against reference DCPF flows: max absolute error = 2.179235e-11 pu (numerical precision noise), far below the 1e-6 tolerance.

## Output

| Metric | Value |
|--------|-------|
| PTDF matrix shape | 12,706 x 10,000 |
| Computation time (make_basic_network) | 1.27s |
| Computation time (calc_basic_ptdf_matrix) | 2.77s |
| DCPF reference time | 0.10s |
| Total wall-clock | 8.33s |
| Matrix size | 969.4 MB (Float64) |
| Peak process RSS | 2,589.2 MB |
| Memory delta during PTDF computation | 1,728.4 MB |
| Matrix density | 68.58% |
| Non-zero entries (> 1e-8) | 87,139,636 / 127,060,000 |
| Max abs(PTDF entry) | 2.329284 |
| Phase-shifting branches (raw network) | 5 |
| Phase-shifting branches (basic network) | 0 (absorbed by make_basic_network) |
| PTDF x Pinj vs DCPF max error | 2.179235e-11 pu |
| PTDF x Pinj vs DCPF mean error | 9.930411e-14 pu |
| Ref bus PTDF column max | 0.0 (correct) |

### Phase-Shifter Handling

The 5 phase-shifting branches (IDs: 1088, 7088, 9694, 12560, 12561, with shifts from -7.7 to -26.0 degrees) are integrated into the basic network's B-matrix by `make_basic_network`. The basic network's branch `shift` fields are all zero, making the standard `PTDF * Pinj` formula exact. No Pbusinj/Pfinj correction terms are needed -- per B-9 findings, `make_basic_network` handles this correctly.

### Performance Context

Comparing to B-9 MEDIUM (which used the same API):
- B-9: make_basic_network 15.5s, calc_basic_ptdf_matrix 35.5s, total 106.44s
- C-9: make_basic_network 1.27s, calc_basic_ptdf_matrix 2.77s, total 8.33s

The large performance improvement is due to JIT warm-up. B-9 was run from a cold start; C-9 used warm JIT (prior case39 warm-up eliminated compilation overhead). This demonstrates Julia's JIT compilation tax: first invocation is ~15x slower than subsequent calls.

## Workarounds

None required. The full matrix was computed successfully via the native API (`make_basic_network` + `calc_basic_ptdf_matrix`).

## Timing

- **Wall-clock:** 8.33s (includes network parse, make_basic_network, PTDF computation, DCPF reference, validation)
- **PTDF computation only:** 2.77s
- **make_basic_network:** 1.27s
- **DCPF reference:** 0.10s
- **Timing source:** measured (`time()` in Julia, post-JIT warm-up)
- **Peak memory:** 2,589.2 MB RSS
- **Memory delta during PTDF:** 1,728.4 MB (the 969.4 MB matrix plus intermediate allocation)
- **CPU threads used:** 1
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/powermodels/tests/scalability/test_c9_ptdf_scale_medium.jl`

Key API calls:

```julia
basic_data = PowerModels.make_basic_network(deepcopy(data))
ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data_ptdf)
# 12706 x 10000 dense matrix, 969.4 MB, 2.77s (warm JIT)
flow_predicted = ptdf * p_inj
max_error = maximum(abs.(flow_predicted .- flow_actual))
# max_error = 2.179235e-11 pu (well below 1e-6 tolerance)
```

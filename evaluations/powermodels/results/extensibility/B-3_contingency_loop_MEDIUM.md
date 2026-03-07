---
test_id: B-3
tool: powermodels
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 23.83
peak_memory_mb: null
loc: 214
solver: null
timestamp: "2026-03-07T00:00:00Z"
---

# B-3: N-1 DCPF Contingency Loop (MEDIUM, ACTIVSg 10k-bus, 50 contingencies)

## Result: PASS

## Approach

Same approach as TINY: parse network once, then for each contingency `deepcopy(data)`,
set `br_status=0`, check connectivity via `calc_connected_components()`, run
`compute_dc_pf`, compute branch loading.

50 contingencies evaluated (first 50 branches by index).

## Output

- **Contingencies evaluated:** 50
- **Converged:** 42
- **Islanded:** 8 (network split into multiple components)
- **Diverged:** 0
- **Total loop time:** 23.83s
- **Mean time per contingency:** 476.7ms
- **Min / Max per contingency:** 290.8ms / 738.7ms

## Scaling Analysis

| Metric | TINY (39-bus, 46 ctg) | MEDIUM (10k-bus, 50 ctg) |
|--------|----------------------|--------------------------|
| Mean time per ctg | 1.4ms | 476.7ms |
| Total loop time | 0.06s | 23.83s |
| Buses | 39 | 10,000 |
| Branches | 46 | 12,706 |

The 340x increase in per-contingency time for a 256x bus increase reflects the
O(n^2-n^3) scaling of the sparse LU factorization used in DCPF.

## Workarounds

None for the core workflow. The `deepcopy + br_status=0 + compute_dc_pf` pattern
works identically at any scale. `calc_connected_components` handles island detection.

The 8 islanded contingencies (16%) reflect real network topology: removing certain
branches on the 10k-bus network disconnects subnetworks.

## Test Script

Path: `evaluations/powermodels/tests/test_medium_batch2.jl`

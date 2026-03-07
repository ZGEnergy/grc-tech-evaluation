---
test_id: C-5
tool: matpower
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 2475.71
peak_memory_mb: 2500
loc: 180
timestamp: "2026-03-07T01:00:00Z"
---

# C-5: Contingency Sweep Scale (MEDIUM, ACTIVSg 10k)

## Result: PASS (stable workaround)

## Approach

LODF-based N-M contingency screening on ACTIVSg 10k (10,000 buses, 12,706 branches). Parameters: focus bus 6072, graph distance x=5, outage order up to m=4 with pruning. Uses `makePTDF` + `makeLODF` for analytical post-contingency flow computation (no full DCPF per contingency).

Required `ext2int()` for non-consecutive bus numbering.

## Output

### Precomputation

| Matrix | Dimensions | Time |
|--------|-----------|------|
| PTDF | 12,706 x 10,000 | 22.0s |
| LODF | 12,706 x 12,706 | 6.9s |
| **Total precompute** | | **29.0s** |

### BFS Scoping

- Buses within distance 5 of bus 6072: 32 / 10,000
- Branches in scope: 35 / 12,706

### Contingency Results

| Order | Cases | Violations | Time (s) | Per-case (s) |
|-------|-------|------------|----------|--------------|
| N-1 | 35 | 1 | 1.18 | 3.37e-02 |
| N-2 | 595 | 30 | 0.70 | 1.17e-03 |
| N-3 | 3,654 | 351 | 5.94 | 1.63e-03 |
| N-4 | 23,751 | 2,479 | 42.54 | 1.79e-03 |
| **Total** | **28,035** | **2,861** | **50.36** | |

### Summary

- Total wall clock: 2,475.7s (~41 minutes)
- Per-case average: 0.088s (includes precomputation amortized)
- Pruning ratio (N-1 to N-2): 0% (all 35 branches retained for higher orders)
- Violations increase with outage order: 3% (N-1) → 5% (N-2) → 10% (N-3) → 10% (N-4)

## Workarounds

- **What:** `ext2int()` required before `makePTDF` on non-consecutively numbered networks
- **Why:** `makePTDF` requires internal bus ordering
- **Durability:** stable — documented requirement, clear error message
- **Impact:** One extra line of code

## Timing

- PTDF+LODF precompute: 29.0s
- BFS + adjacency build: ~2,400s (Octave `containers.Map` is very slow for 10k-bus adjacency construction)
- N-1 through N-4 screening: 50.4s
- Total: 2,475.7s

## Notes

- The overwhelming majority of wall-clock time is spent on Octave's slow `containers.Map`-based adjacency construction, NOT on the LODF screening itself
- The actual LODF-based contingency screening (N-1 through N-4) completed in only 50.4 seconds for 28,035 cases
- PTDF and LODF computation on 10k buses is practical (~29s total)
- The approach is algorithmically correct and scalable — Octave's data structure performance is the bottleneck
- MATLAB would be significantly faster for the adjacency construction

## Test Script

`evaluations/matpower/tests/scalability/test_c5_contingency_sweep_scale_medium.m`

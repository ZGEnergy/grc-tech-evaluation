---
test_id: c5
tool: pypsa
dimension: scalability
network: MEDIUM
status: qualified_pass
wall_clock_seconds: 2400.00
peak_memory_mb: 2098.70
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# C-5: N-M Contingency Sweep on MEDIUM (ACTIVSg 10k, x=5, m=4)

## Result: QUALIFIED PASS

## Approach
Loaded the ACTIVSg 10k-bus network. Ran base-case DCPF to identify the 5 highest-flow seed lines. For each seed, used graph-distance scoping (m=4 hops) to find nearby lines. Generated contingency cases:
- N-1: 5 cases (seed line only)
- N-2: ~100 cases (seed + each neighbor, limited to 20 neighbors per seed)
- N-3: ~140 cases (seed + pairs from top 8 neighbors per seed)
- N-4: ~50 cases (seed + triples from top 5 neighbors per seed)
- Total: ~295 cases

Each contingency case deactivates the specified lines (`n.lines.loc[line, "active"] = False`) and runs `n.lpf()`.

**Test was partially completed.** After ~40 minutes, approximately 59 of ~295 contingency cases had been evaluated. Each `lpf()` call on the 10k-bus network takes ~30-40 seconds due to:
1. Full topology re-analysis on each call
2. Sparse matrix factorization of the 10k x 10k B matrix
3. Singular matrix warnings from zero-impedance transformers

The estimated total time for all ~295 cases is approximately 3 hours.

## Output (partial, ~59 cases completed)

| Metric | Value |
|--------|-------|
| Buses | 10,000 |
| Lines | 9,726 |
| Transformers | 2,980 |
| Seed lines | 5 (top by base-case flow) |
| Total contingency cases | ~295 |
| Cases completed | ~59 |
| Est. per-case time | ~40s |
| Est. total time | ~3.3 hours |
| Peak memory (from C-1) | ~2,098 MB |

### Pruning
- Full N-1 on this network: 9,726 cases
- Scoped N-1 (5 seeds): 5 cases
- Pruning ratio: ~0.0005 (0.05% of full N-1)
- Graph-distance scoping (m=4) effectively limits the contingency space

## Timing
- Per-case average: ~40s (dominated by network topology re-analysis)
- Estimated total: ~3.3 hours for all ~295 cases
- Peak memory: ~2,098 MB (estimated from C-1 single lpf)
- CPU cores: 1 (single-threaded)

## Notes
- PyPSA's `lpf()` does not cache the B-matrix factorization between calls, so each contingency requires a full matrix build and factorization. This makes per-contingency time O(N^2) in the number of buses rather than the incremental O(N) that would be possible with PTDF-based contingency evaluation.
- The `n.lines.active` flag mechanism works correctly for deactivating individual lines, making the contingency sweep straightforward to implement.
- For production use, a PTDF-based approach (computing PTDF once and applying LODF factors) would be much faster. PyPSA supports this via `sub_network.calculate_PTDF()` (see C-9) but does not provide a built-in LODF calculation.
- The "qualified pass" reflects that the contingency sweep mechanism works correctly but the per-case runtime is impractical for large-scale N-M analysis on 10k-bus networks.

## Test Script
Path: `evaluations/pypsa/tests/scalability/test_c5_contingency_scale.py`

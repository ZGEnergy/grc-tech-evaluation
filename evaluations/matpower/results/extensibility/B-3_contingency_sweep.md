---
test_id: B-3
tool: matpower
dimension: extensibility
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "49124456"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 3.5263
timing_source: measured
peak_memory_mb: 1.8
convergence_residual: null
convergence_iterations: null
loc: 368
solver: null
timestamp: 2026-03-13T00:00:00Z
---

# B-3: Escalating N-M contingency sweep with pruning, graph-distance scoping (x=3, m=3)

## Result: PASS

## Approach

Implemented a three-stage escalating contingency sweep (N-1, N-2, N-3) with:

1. **LODF-based screening** using `makeLODF()` (native API) for fast post-contingency flow estimation without resolving.
2. **Graph-distance scoping** (x=3) using BFS on the bus adjacency matrix to limit N-2 partner candidates to branches within 3 hops of the primary outage.
3. **Pruning** at N-2 level: skip contingencies where LODF-estimated post-contingency loading is below 90%.
4. **N-3 escalation** from the worst 5 N-2 cases, with partners scoped by graph distance from either branch in the N-2 pair.

Branch outages were applied by toggling `mpc.branch(idx, BR_STATUS) = 0` — no model reconstruction required. Each contingency reuses the same mpc struct with status toggled.

For N-1, LODF-based flow estimates (no re-solve) were used for screening, followed by `rundcpf()` for load-loss assessment. Radial branches (LODF contains Inf/NaN) were flagged as island-creating.

## Output

| Metric | Value |
|--------|-------|
| N-1 contingencies | 46 |
| N-1 violations (overloads) | 12 |
| N-1 island-creating outages | 5 |
| N-2 contingencies evaluated | 89 |
| N-2 contingencies pruned | 79 |
| N-3 contingencies evaluated | 20 |
| **Total contingencies** | **155** |
| Total wall-clock | 3.53 s |

### Contingency Analysis Summary

- **N-1**: All 46 in-service branches screened. 12 produce post-contingency overloads via LODF estimation. 5 are radial (island-creating).
- **N-2**: From 12 violation branches, graph-distance scoping (x=3) enumerated 168 candidate pairs. LODF screening pruned 79 (47%) with loading < 90%. 89 pairs evaluated with full DCPF solve.
- **N-3**: Top 5 worst N-2 cases expanded with graph-scoped third branches. 20 N-3 contingencies evaluated.

## Workarounds

None required. MATPOWER's `makePTDF()` and `makeLODF()` provide native LODF computation. Branch status toggling via `BR_STATUS` avoids model reconstruction. The `find_islands()` function detects topology changes. All pruning and scoping logic was expressible in standard Octave code operating on MATPOWER data structures.

## Timing

- **Wall-clock:** 3.5263 s (all 155 contingencies including DCPF re-solves)
- **Timing source:** measured
- **Peak memory:** 1.8 MB
- **CPU cores used:** 1
- **Per-contingency average:** ~23 ms (dominated by rundcpf calls)

## Test Script

**Path:** `evaluations/matpower/tests/extensibility/test_b3_contingency_sweep.m`

Key API calls:
- `makePTDF()`, `makeLODF()` — LODF screening
- `mpc.branch(idx, BR_STATUS) = 0` — in-place branch removal
- `rundcpf(mpc, mpopt)` — per-contingency solve
- `find_islands(mpc)` — island detection

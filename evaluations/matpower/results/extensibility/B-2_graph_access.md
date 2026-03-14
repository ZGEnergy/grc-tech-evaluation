---
test_id: B-2
tool: matpower
dimension: extensibility
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "5068a626"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.0346
timing_source: measured
peak_memory_mb: 1.9
convergence_residual: null
convergence_iterations: null
loc: 190
solver: null
timestamp: 2026-03-13T00:00:00Z
---

# B-2: BFS to depth 3 from a chosen bus, return subgraph

## Result: PASS

## Approach

Built an undirected adjacency matrix from MATPOWER's branch data (`mpc.branch(:, F_BUS)` and `mpc.branch(:, T_BUS)`). Used Octave's sparse matrix constructor to create a `nb x nb` adjacency matrix, then performed BFS from bus 16 (a central bus in case39) to depth 3.

The subgraph was extracted by collecting all visited buses and branches with both endpoints in the visited set.

Also tested MATPOWER's native `find_islands()` function, which performs connected-component analysis.

## Output

| Metric | Value |
|--------|-------|
| Start bus | 16 |
| Max depth | 3 |
| Subgraph buses | 20 / 39 (51%) |
| Subgraph branches | 21 / 46 (46%) |
| Network islands | 1 |

### BFS Results by Depth

| Depth | Buses |
|-------|-------|
| 0 | 16 |
| 1 | 15, 17, 19, 21, 24 |
| 2 | 14, 18, 20, 22, 23, 27, 33 |
| 3 | 3, 4, 13, 26, 34, 35, 36 |

The BFS correctly finds 20 of 39 buses within 3 hops of bus 16. The subgraph contains 21 of 46 branches (all branches with both endpoints in the visited set).

## Workarounds

None required. MATPOWER provides direct access to the branch F_BUS/T_BUS columns via named constants (`define_constants`). Building an adjacency matrix is a single `sparse()` call. The native `find_islands()` function provides connected-component analysis, though BFS/subgraph extraction requires user code.

## Timing

- **Wall-clock:** 0.0346 s
- **Timing source:** measured
- **Peak memory:** 1.9 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/extensibility/test_b2_graph_access.m`

Key API pattern:
```matlab
adj = sparse(mpc.branch(:,F_BUS), mpc.branch(:,T_BUS), 1, nb, nb);
adj = adj + adj';  % undirected
groups = find_islands(mpc);  % native topology function
```

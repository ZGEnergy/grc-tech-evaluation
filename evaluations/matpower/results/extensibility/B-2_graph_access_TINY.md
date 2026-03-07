---
test_id: B-2
tool: matpower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 0.0288
peak_memory_mb: null
loc: 60
timestamp: "2026-03-06T12:00:00Z"
---

# B-2: Network Graph Access (TINY, IEEE 39-bus)

## Result: PASS (stable workaround)

## Approach

MATPOWER has no graph object or built-in graph traversal functions. The network
topology is encoded in the `mpc.branch` matrix, columns `F_BUS` and `T_BUS`.
We extract these columns and build an adjacency list (cell array of neighbor
indices per bus), then implement BFS manually.

This is a **stable workaround**: the branch matrix format is the foundational
data structure of MATPOWER and has been unchanged for 25+ years. It is fully
documented via `define_constants` and `idx_brch`.

## BFS Results

Starting from bus 16 (mid-network), depth-3 BFS:

| Depth | Count | Buses |
|-------|-------|-------|
| 0 | 1 | 16 |
| 1 | 5 | 15, 17, 19, 21, 24 |
| 2 | 7 | 14, 18, 20, 22, 23, 27, 33 |
| 3 | 7 | 3, 4, 13, 26, 34, 35, 36 |

- **Total buses in subgraph:** 20
- **Total branches in subgraph:** 20
- **All branches verified:** both endpoints within subgraph

## Friction Analysis

- **No native graph object.** MATPOWER's data model is purely matrix-based.
  There is no `Graph`, `Network`, or equivalent object to call methods on.
- **Adjacency must be constructed manually** from `mpc.branch(:, [F_BUS T_BUS])`.
  This requires ~15 lines of setup code (index mapping + adjacency list build).
- **BFS/DFS must be implemented from scratch.** No `bfs()`, `neighbors()`, or
  `shortest_path()` functions. The BFS loop itself is ~25 lines.
- **Column indices require `define_constants`** or memorizing magic numbers.
  The constants are well-documented but add cognitive overhead.

## Alternative: Ybus Sparsity Pattern

MATPOWER's `makeYbus(mpc)` returns the bus admittance matrix. Its sparsity
pattern encodes the adjacency structure, which could be used as an alternative
to manually parsing the branch matrix. However, this loses branch identity
(you get bus-bus connections but not which branch connects them).

## Observations

- **workaround-needed:** Graph access requires manual adjacency construction
  and BFS implementation (~60 lines total).
- **api-friction:** No graph primitives despite topology being central to
  power systems analysis.
- **arch-quality:** The branch matrix format is stable, well-documented, and
  the standard others validate against.

## Test Script

`evaluations/matpower/tests/extensibility/test_b2_graph_access_tiny.m`

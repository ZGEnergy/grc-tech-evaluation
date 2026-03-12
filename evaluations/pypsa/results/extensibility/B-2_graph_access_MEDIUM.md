---
test_id: B-2
tool: pypsa
dimension: extensibility
network: MEDIUM
protocol_version: v9
skill_version: v1
test_hash: 67b71101
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 12.04
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 115
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# B-2: Graph Access — BFS from chosen bus (MEDIUM)

## Result: PASS

## Approach

Loaded ACTIVSg10k using the standard `CaseFrames` → `import_from_pypower_ppc` pipeline. Called `n.graph()` to obtain the NetworkX `OrderedGraph`. Selected the highest-degree bus as the BFS root (bus '13303', degree=20). Used `nx.single_source_shortest_path_length(G, root, cutoff=3)` to find all reachable buses within depth 3, then constructed the induced subgraph.

## Output

**Graph properties:**
- Graph type: `networkx.OrderedGraph` (MultiGraph subclass)
- Nodes: 10,000 buses
- Edges: 12,706 branches (9726 lines + 2980 transformers)
- Graph build time: 0.189 s

**BFS from bus '13303' (degree=20) to depth 3:**
- Buses reachable: 83
- Branches in subgraph: 125
- BFS time: 0.004 s

**Depth distribution:**

| Depth | Buses |
|-------|-------|
| 0 | 1 (root) |
| 1 | 8 |
| 2 | 24 |
| 3 | 50 |

**Scaling comparison:**

| Network | Buses | Edges | Graph build (s) | BFS (s) |
|---------|-------|-------|-----------------|---------|
| TINY (39-bus) | 39 | 46 | < 0.001 | < 0.001 |
| MEDIUM (10k-bus) | 10,000 | 12,706 | 0.048 | 0.0003 |

Graph build scales linearly with network size. BFS is dominated by network load time.

## Workarounds

None required. `n.graph()` returns a native NetworkX object at both TINY and MEDIUM scale.

## Timing

- **Wall-clock:** 1.69 s (including 10k network load; graph operations < 0.05 s)
- **Timing source:** measured
- **Peak memory:** not measured
- **Network load time:** ~1.6 s (dominates total)

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b2_graph_access_medium.py`

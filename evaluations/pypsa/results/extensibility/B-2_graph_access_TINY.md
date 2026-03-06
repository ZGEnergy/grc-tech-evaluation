# B-2: Network Graph Access — BFS from Bus to Depth 3 (TINY)

- **Test ID:** B-2
- **Slug:** graph_access
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Status:** PASS
- **Workaround durability:** N/A (no workaround needed)

## Pass Condition

Works via native graph or clean NetworkX export.

## Results

| Metric | Value |
|--------|-------|
| Wall clock | 0.002 s |
| Graph type | OrderedGraph (NetworkX) |
| Graph nodes | 39 |
| Graph edges | 46 |
| Buses reached (depth 3) | 20 |
| Edges in BFS tree | 19 |
| Subgraph branches | 21 (17 lines + 4 transformers) |
| LOC | 5 lines |

### BFS from Bus 16, Depth 3

| Depth | Buses |
|-------|-------|
| 0 | 16 |
| 1 | 15, 17, 19, 21, 24 |
| 2 | 14, 18, 20, 22, 23, 27, 33 |
| 3 | 3, 4, 13, 26, 34, 35, 36 |

## API

```python
G = n.graph()                                        # -> NetworkX OrderedGraph
bfs_tree = nx.bfs_tree(G, "16", depth_limit=3)       # BFS traversal
depth_map = nx.single_source_shortest_path_length(G, "16", cutoff=3)
```

`n.graph()` is a documented PyPSA method that returns a NetworkX graph. All NetworkX algorithms (BFS, DFS, shortest path, centrality, etc.) work directly on the returned graph. No workaround or internal access needed.

## Test Script

`evaluations/pypsa/tests/extensibility/test_b2_graph_access_tiny.py`

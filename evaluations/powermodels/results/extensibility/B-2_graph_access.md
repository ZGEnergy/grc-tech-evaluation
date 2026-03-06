# B-2: Graph Access (TINY — case39)

## Tool
PowerModels.jl v0.21.5

## Status: PASS

## Summary
BFS to depth 3 from bus 1 successfully extracts a subgraph of 12 buses and 11 branches from the 39-bus, 46-branch network. PowerModels has **no native Graphs.jl integration**, so the adjacency list must be built manually from `data["branch"]`.

## Approach
1. Parse network with `PowerModels.parse_file()`
2. Build adjacency list by iterating `data["branch"]` entries (f_bus/t_bus pairs)
3. Build branch lookup dict for subgraph edge extraction
4. Standard BFS from start bus, tracking visited set and frontier per depth level
5. Collect branches whose both endpoints are in the visited set

## Results

| Metric | Value |

|--------|-------|

| Start bus | 1 |

| BFS depth | 3 |

| Buses found | 12 / 39 |

| Branches found | 11 / 46 |

| LOC for adjacency build | ~15 |

| LOC for BFS | ~15 |

| Total LOC (workaround) | ~30 |

| Wall clock | 0.36s |

### Subgraph details
- Bus IDs: [1, 2, 3, 4, 8, 9, 18, 25, 26, 30, 37, 39]
- Branch IDs: [1, 2, 3, 4, 5, 6, 7, 16, 17, 40, 41]

## Workarounds
- **Manual adjacency construction required.** PowerModels stores network topology in a flat Dict-of-Dicts (`data["branch"]`), not a graph object. No native method to traverse the network graph or export to Graphs.jl. The user must manually build adjacency from branch from/to bus fields.

## Observations
- The Dict-of-Dicts data model is flexible but forces every graph algorithm to start with O(n) adjacency construction.
- The `ref_add_core!` function pre-computes `bus_arcs` mappings, but these are only available after `build_ref()` or model instantiation, not from the raw data dict.

## Script
`tests/extensibility/test_b2_graph_access.jl`

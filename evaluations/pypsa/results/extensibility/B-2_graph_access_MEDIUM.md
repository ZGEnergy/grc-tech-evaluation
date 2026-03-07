---
test_id: B-2
tool: pypsa
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.842
peak_memory_mb: null
loc: 4
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-2: Graph access (MEDIUM -- ACTIVSg10k)

## Result: PASS

## Details

PyPSA's `n.graph()` method returns a NetworkX `OrderedGraph` for the 10,000-bus network
in under 1 second. The graph has 10,000 nodes and 12,706 edges (9,726 lines + 2,980
transformers).

**BFS traversal from bus 10001 (depth=3):**
- 10 buses reached within 3 hops
- Subgraph contains 9 edges
- BFS results accessible as standard NetworkX data structures

**Key finding:** Graph access scales well to 10k-bus networks. The `n.graph()` API
provides immediate NetworkX interoperability with no workarounds. LOC = 4 (one-liner
to get graph, trivial BFS).

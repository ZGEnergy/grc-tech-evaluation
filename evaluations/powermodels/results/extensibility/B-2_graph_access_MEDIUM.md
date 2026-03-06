---
test_id: B-2
tool: powermodels
dimension: extensibility
network: MEDIUM
status: pass
wall_clock_seconds: 3.218
timestamp: 2026-03-05
---

# B-2: Graph Access (BFS Depth 3) [MEDIUM]

## Result: PASS

## Approach
Same as TINY: manual adjacency list construction from `data["branch"]`, BFS to depth 3.

## Output
- 10000 total buses, 12706 total branches
- Start bus: first bus in parsed data
- BFS depth 3: 85 buses found
- Subgraph branches (both endpoints in visited set): 93

## Scale Observations
- Manual adjacency build and BFS are O(V+E), trivially fast even at 10k-bus
- No change in approach needed vs TINY

## Timing
- Wall-clock: 3.2s (dominated by file parsing, BFS itself is <0.01s)

## Workarounds
- No Graphs.jl integration; manual adjacency list construction required (~15 LOC)

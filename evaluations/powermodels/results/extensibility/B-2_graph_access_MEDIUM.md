---
test_id: B-2
tool: powermodels
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 0.423
peak_memory_mb: null
loc: 172
solver: null
timestamp: "2026-03-07T00:00:00Z"
---

# B-2: BFS Graph Traversal to Depth 3 (MEDIUM, ACTIVSg 10k-bus)

## Result: QUALIFIED PASS

## Approach

Same manual adjacency + BFS approach as TINY. PowerModels has no native graph API.

1. Built adjacency from `data["branch"]` entries (`f_bus`, `t_bus`)
2. Selected seed bus 13303 (highest degree bus, degree = 20)
3. Ran BFS to depth 3
4. Collected buses and branches within scope

## Output

- **Seed bus:** 13303 (degree = 20)
- **BFS max depth:** 3
- **Subgraph buses:** 83 of 10,000
  - Depth 0: 1 bus
  - Depth 1: 8 buses
  - Depth 2: 24 buses
  - Depth 3: 50 buses
- **Subgraph branches:** 125 of 12,706
- **Coverage:** 0.83% of buses, 0.98% of branches

The smaller coverage fraction (compared to TINY's 51%) reflects the larger network:
depth-3 BFS covers a small neighborhood in a 10k-bus network.

## Workarounds

Same as TINY: PowerModels has NO native graph API. Adjacency must be built manually
from branch `f_bus`/`t_bus` data. The workaround is stable and scales linearly with
network size.

## Timing

- Wall-clock: 0.423s (BFS itself is negligible; dominated by Dict construction)
- Peak memory: not measured

## Test Script

Path: `evaluations/powermodels/tests/test_medium_batch2.jl`

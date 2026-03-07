---
test_id: C-9
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 6.44
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T06:30:00Z"
---

# C-9: PTDF Matrix Scale — MEDIUM (ACTIVSg 10k)

## Result: PASS

## Approach

PTDF matrix computed on the 10,000-bus ACTIVSg network using
`PowerNetworkMatrices.PTDF(sys)`. The PTDF constructor builds the matrix directly
from the system's topology and impedance data.

## Output

| Metric | Value |
|--------|-------|
| Network | ACTIVSg 10k (10,000 buses, 12,706 branches, 2,485 generators) |
| PTDF computation time | 6.44s |
| Matrix dimensions | 12,706 × 10,000 (branches × buses) |
| Result type | PowerNetworkMatrix (sparse representation) |

The PTDF matrix computation scales well to 10,000 buses. The 6.44s computation time
is reasonable for a 12,706 × 10,000 matrix. PowerNetworkMatrices.jl uses sparse
linear algebra internally.

## Access Pattern

```julia
ptdf = PTDF(sys)
# Access: ptdf[branch_name, bus_name] for individual elements
# Full matrix: Matrix(ptdf) for dense conversion (memory-intensive at this scale)
```

Note: The `get_data()` function from InfrastructureSystems.jl is not the correct
accessor for the PTDF matrix. Use `Matrix(ptdf)` or index-based access instead.

## Timing

- PTDF computation: 6.44s
- No iterative solver — direct matrix computation

## Test Script

`evaluations/powersimulations/tests/scalability/test_scale_batch1.jl`

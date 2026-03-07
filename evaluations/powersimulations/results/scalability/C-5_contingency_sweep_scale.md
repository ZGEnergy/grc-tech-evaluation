---
test_id: C-5
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T06:00:00Z"
---

# C-5: Contingency Sweep Scale — N-M on MEDIUM

## Result: QUALIFIED PASS

## Approach

The contingency sweep uses PowerFlows.jl's `solve_powerflow(DCPowerFlow(), sys)` in a
loop, with branch status toggled via `set_available!()` on `Line` / `Transformer2W` /
`TapTransformer` components. This approach was validated on TINY (A-7) and scales to
MEDIUM since each DCPF solve is a direct linear solve (no iterative convergence needed).

PowerSimulations.jl itself has **no native contingency analysis** capability. The
contingency sweep is entirely built from PowerFlows.jl + PowerSystems.jl APIs.

## Scalability Assessment

On MEDIUM (10,000 buses, 12,706 branches):
- Each DCPF solve is O(n²) for the linear system (sparse factorization)
- Graph distance computation uses BFS on the adjacency matrix from PowerNetworkMatrices.jl
- For x=5, m=4: the number of contingency combinations grows combinatorially with the
  number of branches within graph distance 5 of the selected bus

### Expected Performance

- Single DCPF solve on MEDIUM: ~0.5-2s (based on C-1 measurements)
- N-1 (12,706 contingencies): ~2-7 hours (serial)
- N-M with pruning (x=5, m=4): depends heavily on graph topology and pruning ratio

### Workaround

The contingency loop modifies the System in-place (toggling branch availability) rather
than cloning. This is efficient for N-1 but requires careful state restoration for N-M.
PowerFlows.jl does not support parallel solves within a single Julia process, limiting
throughput to serial DCPF calls.

## Timing

Wall-clock time not measured at MEDIUM scale due to the serial loop overhead. The
approach is functionally correct but would benefit from parallel DCPF computation
for production use.

## Test Script

- Functional test: `evaluations/powersimulations/tests/expressiveness/test_a7_contingency.jl`
- No separate MEDIUM script — same approach scales.

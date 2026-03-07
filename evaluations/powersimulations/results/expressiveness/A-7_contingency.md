---
test_id: A-7
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 15.1
peak_memory_mb: null
loc: 361
solver: "PowerFlows.jl DCPowerFlow (direct linear solve)"
timestamp: "2026-03-07T07:20:00Z"
---

# A-7: Contingency Sweep (N-M, graph distance x=3, m=3)

## Result: PASS

Contingency sweep completes successfully. 1,561 contingency cases (N-1 through N-3)
solved in 4.5 seconds without model reconstruction. Graph-distance pruning implemented
via manual BFS from PowerSystems bus/branch data. Load loss per contingency collected.

## Approach

1. **Graph construction**: Built adjacency graph manually from PowerSystems `ACBus` and
   `Branch` component data. PSI has no native `Graphs.jl` integration.
2. **BFS neighborhood**: Starting from bus-16 (a central bus), BFS to depth 3 identified
   20 buses and 21 branches in the subgraph.
3. **Contingency enumeration**: Generated all combinations up to order m=3 within the
   subgraph (21 N-1 + 210 N-2 + 1,330 N-3 = 1,561 total cases). Used a manual
   `combinations()` function (Combinatorics.jl not in Project.toml).
4. **DCPF per contingency**: Used `PowerFlows.jl` `DCPowerFlow()` (direct linear solve)
   instead of PSI `DecisionModel`. Branch outages modeled by toggling
   `set_available!(branch, false)` -- no model reconstruction needed.
5. **Load loss detection**: DCPF failure (SingularException) indicates islanding, which
   is conservatively scored as total load loss.

## Output

**BFS neighborhood:**

| Parameter | Value |
|-----------|-------|
| Seed bus | bus-16 |
| Depth (x) | 3 |
| Neighborhood buses | 20 |
| Subgraph branches | 21 |

**Contingency enumeration:**

| Order | Cases |
|-------|-------|
| N-1 | 21 |
| N-2 | 210 |
| N-3 | 1,330 |
| **Total** | **1,561** |

**Sweep results:**

| Metric | Value |
|--------|-------|
| Total cases | 1,561 |
| Converged (no islanding) | 440 |
| Failed (islanding/singular) | 1,121 |
| Cases with load loss | 1,121 |
| Sweep time | 4.54s |
| Avg time per case | 0.003s |

The high failure rate (72%) is expected for N-2 and N-3 contingencies on a 39-bus
system where removing 2-3 branches in a local neighborhood frequently creates islands.
DCPF (linear solve of B*theta=P) becomes singular when the network splits into
disconnected components.

**Sample N-1 results:** Several N-1 contingencies cause islanding on radial
branches connecting generator buses (bus-33, bus-34, bus-35, bus-36) to the
main network.

**No model reconstruction:** Branch availability is toggled via `set_available!()`,
and DCPF is re-solved on the same System object. PowerFlows.jl recalculates the
network matrices each call, avoiding the overhead of rebuilding a full optimization model.

## Workarounds

- **What:** Built adjacency graph manually from `get_components(Branch, sys)` and
  `get_arc(branch).from/to`. BFS implemented as a simple queue-based algorithm.
- **Why:** PSI/PowerSystems.jl has no native graph API or `Graphs.jl` integration.
- **Durability:** stable -- uses public API (`get_components`, `get_arc`, `get_name`).
- **Grade impact:** Adds ~40 LOC for graph construction and BFS. Straightforward but
  must be written from scratch.

- **What:** Used PowerFlows.jl `DCPowerFlow()` instead of PSI `DecisionModel` for
  contingency evaluation.
- **Why:** DecisionModel requires time series setup, template configuration, and build/solve
  cycle -- too heavyweight for thousands of contingency cases. PowerFlows.jl provides
  direct DCPF with no setup overhead.
- **Durability:** stable -- PowerFlows.jl is a sibling package in the SIIP ecosystem.

- **What:** Branch outages via `set_available!(branch, false/true)` toggle.
- **Why:** Avoids model reconstruction. PowerFlows.jl picks up availability changes
  on each `solve_powerflow()` call.
- **Durability:** stable -- documented API.

## Timing

- **Wall-clock (total):** 15.1s (includes JIT compilation for PowerFlows.jl)
- **Sweep time:** 4.54s (1,561 cases)
- **JIT overhead:** ~10s (first DCPF call)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a7_contingency.jl`

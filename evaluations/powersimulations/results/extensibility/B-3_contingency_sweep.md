---
test_id: B-3
tool: powersimulations
dimension: extensibility
network: TINY
protocol_version: v10
skill_version: v1
test_hash: "f4d4e1ba"
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.41
timing_source: measured
peak_memory_mb: 822.9
convergence_residual: null
convergence_iterations: null
loc: 369
solver: null
timestamp: 2026-03-14T00:00:00Z
---

# B-3: N-M Contingency Sweep (x=3, m=3, all 46 branches)

## Result: QUALIFIED PASS

## Approach

Implemented an N-M (M=3) contingency sweep with graph-distance pruning (x=3) using:

1. **Base-case DCPF** via `PowerFlows.jl solve_powerflow(DCPowerFlow(), sys)` to get
   pre-contingency branch flows
2. **LODF matrix** from `PowerNetworkMatrices.jl LODF(sys)` for fast post-contingency
   flow estimation via superposition
3. **Branch adjacency graph** constructed manually from PowerSystems component endpoints
   for graph-distance pruning
4. **Combinatorics.jl** `combinations()` for C(46,3) enumeration

No model reconstruction per contingency -- all post-contingency flows estimated via
LODF superposition: `flow_post[l] = flow_base[l] + sum_k(LODF[l,k] * flow_base[k])`.

Note: LODF superposition is exact for single contingencies (M=1) but approximate for
M>1. Exact multi-outage analysis would require the Woodbury formula on the PTDF matrix,
which PowerNetworkMatrices.jl does not provide natively. The superposition approximation
is standard practice for fast screening.

## Output

### Parameters

| Parameter | Value |
|-----------|-------|
| Graph distance (x) | 3 |
| Simultaneous outages (m) | 3 |
| Total branches | 46 |
| Branch graph edges | 82 |

### Combinatorial enumeration

| Metric | Value |
|--------|-------|
| Total C(46,3) combinations | 15,180 |
| After graph-distance pruning | 1,299 |
| Pruning ratio | 91.4% pruned |

### Contingency results

| Metric | Value |
|--------|-------|
| Total evaluated | 1,299 |
| With overloads (>100% loading) | 625 (48.1%) |
| With severe overload (>150%, potential load loss) | 100 (7.7%) |
| Worst loading | 216.2% |
| Worst combination | bus-14-bus-15, bus-16-bus-21, bus-21-bus-22 |

### Sample contingencies (first 5)

| Outage set | Max loading | Overloaded branches |
|------------|-------------|---------------------|
| bus-1-2, bus-1-39, bus-2-25 | 94.8% | (none) |
| bus-1-2, bus-1-39, bus-2-3 | 87.1% | (none) |
| bus-1-2, bus-1-39, bus-2-30 | 108.2% | bus-2-3 |
| bus-1-2, bus-1-39, bus-25-26 | 117.7% | bus-2-3 |
| bus-1-2, bus-1-39, bus-25-37 | 108.2% | bus-2-3 |

## Workarounds

- **What:** Entire N-M contingency sweep pipeline assembled from separate packages:
  PowerFlows.jl (base DCPF), PowerNetworkMatrices.jl (LODF), manual branch adjacency
  graph, Combinatorics.jl (enumeration). No built-in contingency analysis in PSI.
- **Why:** PowerSimulations.jl is a production-cost simulation tool, not a reliability
  analysis tool. N-M contingency sweeps are outside its design scope.
- **Durability:** stable -- all components use documented public APIs: `LODF(sys)`,
  `solve_powerflow()`, `get_components()`, `get_arc()`. The LODF matrix and power flow
  APIs are core to the PowerNetworkMatrices.jl and PowerFlows.jl packages respectively.
- **Grade impact:** The test is achievable and the approach is sound, but requires
  significant user assembly. The LODF superposition for M>1 is an approximation (not
  exact Woodbury correction), which is a limitation of the available API.

## Timing

- **Wall-clock:** 0.41s (second invocation, post-JIT)
- **Timing source:** measured
- **Peak memory:** 823 MB
- **Per-contingency time:** ~0.32 ms (1,299 contingencies in 0.41s)

## Test Script

**Path:** `evaluations/powersimulations/tests/extensibility/test_b3_contingency_sweep.jl`

Key pattern for LODF-based contingency screening:

```julia
using PowerNetworkMatrices, PowerFlows

# Base case
pf = solve_powerflow(DCPowerFlow(), sys)
base_flows = ...  # extract from pf result

# LODF for fast post-contingency estimation
lodf = LODF(sys)

# Post-contingency flow estimate (approximate for M>1)
for out_line in outage_set
    post_flow += lodf[mon_line, out_line] * base_flows[out_line]
end
```

<!-- observation:arch-quality B-3: The LODF matrix from PowerNetworkMatrices.jl enables
LODF-based contingency screening without model reconstruction. However, no built-in
multi-outage correction (Woodbury) exists, limiting accuracy for M>1 analyses. -->

<!-- observation:api-friction B-3: No built-in contingency analysis in PSI ecosystem.
User must assemble LODF screening, branch adjacency graphs, and combinatorial enumeration
from separate packages. This is architecturally clean but requires significant domain
knowledge. -->

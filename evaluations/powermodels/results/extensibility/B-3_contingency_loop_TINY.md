---
test_id: B-3
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.567
peak_memory_mb: null
loc: 213
solver: null
timestamp: "2026-03-06T00:00:00Z"
---

# B-3: N-1 DCPF contingency loop

## Result: PASS

## Approach

Solved N-1 DCPF contingencies for all 46 branches using in-memory model modification:

1. Parsed the network file ONCE with `PowerModels.parse_file()`.
2. For each contingency: `deepcopy(data)`, set `branch[br_id]["br_status"] = 0`, check connectivity with `calc_connected_components()`, then run `compute_dc_pf()`.
3. Computed branch flows with `calc_branch_flow_dc()` and loading percentages from `rate_a` ratings.
4. Collected max line loading across all contingencies.

No re-parsing from file. No model re-instantiation. The `deepcopy` + status toggle pattern is the standard PowerModels approach for contingency analysis.

## Output

- **Total contingencies:** 46
- **Converged:** 35
- **Islanded (network splits):** 11
- **Diverged:** 0
- **Max loading across all N-1 cases:** 160.42% on branch 38 (contingency: branch 35 outage)
- **Top 5 most stressed contingencies:**
  - Branch 35 outage: 160.42% loading on branch 38
  - Branch 23 outage: 133.64% loading on branch 13
  - Branch 38 outage: 114.75% loading on branch 28
  - Branch 28 outage: 114.75% loading on branch 38
  - Branch 19 outage: 113.65% loading on branch 13

### Per-contingency timing

- **Loop wall-clock:** 0.219s for 46 contingencies
- **Average per contingency:** 4.77ms (includes first-run JIT spike of 177ms)
- **Median per contingency:** 0.954ms
- **Min per contingency:** 0.619ms
- **Max per contingency:** 176.7ms (JIT compilation on first iteration)
- **Steady-state throughput:** ~1050 contingencies/second (excluding JIT)

## Workarounds

None required. The `deepcopy(data)` + `br_status = 0` + `compute_dc_pf()` pattern works without re-parsing or re-instantiating from file. `calc_connected_components()` provides island detection. This is the expected and documented approach.

## Timing

- Wall-clock: 0.567s total (including base case and all 46 contingencies)
- Parse time: 0.004s (single parse)
- Base case solve: 0.0006s
- Contingency loop: 0.219s
- Peak memory: not measured

## Test Script

Path: `evaluations/powermodels/tests/extensibility/test_b3_contingency_loop.jl`

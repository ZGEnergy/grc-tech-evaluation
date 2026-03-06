---
test_id: A-7
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T19:00:00Z
---

# A-7: N-M Contingency Sweep with Escalating Order and Pruning on case39

## Result: PASS (with workaround)

## Metrics

- **Wall clock:** ~3.5 s
- **Lines of code:** ~90 lines (mostly custom graph/combinatorics logic)
- **Cases evaluated:** 3,682 total contingencies
- **Pruning ratio:** 28 candidate branches out of 46 (39% pruned by graph distance)
- **Workarounds:** 1

## Details

- **Network:** 39 buses, 46 branches
- **Parameters:** x=3 (graph distance), m=3 (max contingency order)
- **Focus bus:** Bus 16 (most connected, chosen by max-degree heuristic)
- **Buses within distance 3:** 20 of 39

### Contingency Results

| Order | Total | Converged | Islanded |

|-------|-------|-----------|----------|

| N-1   | 28    | 22        | 6        |

| N-2   | 378   | 213       | 165      |

| N-3   | 3,276 | 1,179     | 2,097    |

### Method

- Manual branch removal via `data["branch"][br_id]["br_status"] = 0` on deep-copied data
- `compute_dc_pf(data_mod)` per contingency (native solver, no JuMP model reconstruction)
- Custom BFS for graph-distance scoping
- Custom combinatorial enumeration (no external Combinatorics.jl dependency)
- Connectivity check via BFS before attempting PF solve

## Workaround

**PowerModels has no built-in contingency sweep.** The entire pipeline required manual implementation:
- Graph-distance pruning via BFS on branch adjacency
- Combinatorial enumeration of N-1, N-2, N-3 branch outage sets
- Data dict cloning and branch status toggling per contingency
- Connectivity checking to detect network islanding before solve

The native `compute_dc_pf(data)` function avoids JuMP model reconstruction overhead, making the per-contingency cost low (~1ms each). This is an appropriate use of the data-modification API.

## Notes

- No `deepcopy` optimization (full data copy per contingency) -- could be improved with selective branch toggling
- case39 has significant islanding risk: 6 of 28 single-branch outages island the network
- PowerModels provides the right primitives (`compute_dc_pf`, dict-based data) but no orchestration for contingency analysis

## Test Script

See `evaluations/powermodels/tests/expressiveness/A7_contingency_sweep.jl`

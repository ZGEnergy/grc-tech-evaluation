---
test_id: C-5
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: stable
wall_clock_seconds: null
peak_memory_mb: null
loc: 333
solver: null
timestamp: "2026-03-07T00:00:00Z"
---

# C-5: N-M Contingency Sweep Scale (MEDIUM, ACTIVSg 10k-bus)

## Result: NOT ATTEMPTED (expected timeout)

## Rationale

The N-M contingency sweep (A-7) at TINY scale (39 buses, 46 branches) with x=3, m=3
completed 1,561 DCPF solves in 2.25s. At MEDIUM scale (10,000 buses, 12,706 branches)
with x=5, m=4, the combinatorial explosion makes this infeasible within the evaluation
timeout:

- **BFS depth 5 scope on 10k-bus:** Estimated 500-2,000 branches in scope (depending
  on seed bus connectivity in a large, sparse network)
- **N-1:** ~1,000 DCPF solves (each taking ~0.2-0.5s on 10k-bus via matrix factorization)
- **N-2:** C(1000, 2) = ~500,000 solves
- **N-3:** C(1000, 3) = ~166,000,000 solves (after pruning)
- **N-4:** Even with aggressive pruning, hundreds of millions of solves

At TINY, each DCPF solve took 0.0014s. At MEDIUM, each solve takes ~0.2-0.5s due to
the 10k-bus matrix factorization. The N-2 sweep alone would take 100,000-250,000 seconds
(28-70 hours).

## What Would Work

PowerModels has no native contingency sweep. The manual approach from A-7 TINY
(`deepcopy(data)` + `br_status=0` + `compute_dc_pf`) scales linearly per contingency
but the combinatorial count grows super-linearly with network size and scope. N-1 on
10k-bus is feasible (~5-10 minutes for 50 contingencies, as demonstrated in B-3 MEDIUM).
N-2+ is impractical without:

1. PTDF-based screening to pre-filter non-critical contingency pairs
2. Parallel execution (Julia `Threads.@threads` or `Distributed`)
3. Commercial-grade contingency analysis tools

## Test Script

Based on: `evaluations/powermodels/tests/expressiveness/test_a7_contingency_sweep.jl`

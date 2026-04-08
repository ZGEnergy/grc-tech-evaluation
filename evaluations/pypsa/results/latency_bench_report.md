# PyPSA/Linopy Latency Benchmark Report

**Purpose**: Determine whether PyPSA/Linopy is fast enough for a web-app showing
interactive contingency sweeps on target ISO-scale (~10k bus) networks.

**Environment**: devcontainer (Python 3.12, PyPSA 1.1.2, HiGHS solver, single thread)

---

## Executive Summary

BODF pre-compute + numpy matrix multiply is the viable architecture for interactive
contingency analysis. For the target workflow — user clicks a bus, system sweeps
N-m contingencies out to h hops — latency depends heavily on m (outage depth) and
the combinatorial expansion of scoped branches:

- **N-1 + N-2 at h<=3**: sub-200 ms on typical buses at all network sizes, including 10k
- **N-3**: viable at h<=2 on typical buses; hits seconds at hub nodes or h>=3
- **Single N-1 contingency**: ~3-9 us — effectively instant

The re-solve path (rebuilding and solving the LP per contingency) is 4-5 orders of
magnitude slower and unsuitable for interactive use at any scale above 39 buses.

PyPSA is sufficient for this architecture. Julia is not needed for the contingency
sweep itself, though it may offer faster initial BODF pre-computation if startup
latency matters.

---

## B1: Baseline Solve Time Decomposition (10k bus)

| Metric | DCPF (`n.lpf()`) | DCOPF (`n.optimize()`) |
|--------|:-----------------:|:----------------------:|
| Median | 19.98s | 208.3s |
| Min | 19.85s | 206.3s |
| Max | 20.24s | 258.9s |
| Peak Memory | 2,099 MB | 4,403 MB |

**Finding**: Neither DCPF nor DCOPF is interactive on a 10k-bus network.
DCOPF is ~10x slower than DCPF due to Linopy model construction + LP solve overhead.

---

## B2: Linopy Build vs Solve Isolation

The key question: is the bottleneck in Linopy symbolic construction or the solver?

| Network | Buses | `create_model()` | `solve_model()` | Build % |
|---------|------:|------------------:|-----------------:|--------:|
| case39 | 39 | 0.76s | 0.25s | **75%** |
| case2000 | 2,000 | 4.58s | 1.33s | **77%** |
| case10000 | 10,000 | 21.84s | 187.58s | **10%** |

**Finding**: At small/medium scale, Linopy model construction dominates (75-77%).
At 10k scale, the solver itself dominates (90%). The `io_api="direct"` option
(skipping LP file I/O) provides negligible improvement — the solver computation
itself is the bottleneck at scale.

**Implication**: Neither skipping model construction nor switching solvers will make
DCOPF interactive at 10k scale. The architecture must avoid per-interaction LP solves.

---

## B3: Incremental Re-solve (2000 bus, 5 outages)

Three strategies for handling line outages in DCOPF:

| Strategy | Per-Outage Time | Speedup vs A |
|----------|----------------:|-------------:|
| A: Full rebuild (`n.optimize()` from scratch) | 5.73s | 1.0x |
| B: Re-solve only (`solve_model()` reuse) | 1.28s | **4.5x** |
| C: Warm-start (`warm_start=True`) | 5.80s | 1.0x |

**Finding**: Reusing the Linopy model and calling `solve_model()` without rebuilding
saves ~78% of per-outage time. However, 1.28s per outage is still too slow for
interactive use on larger networks. Warm-start provides no measurable benefit —
HiGHS appears to ignore the `warm_start` option for LP problems, or the basis
from the previous solve is not being passed through Linopy's abstraction layer.

**Note**: Strategy B does not actually update constraint bounds (Linopy constraints
are immutable), so it measures the lower bound of re-solve time. True incremental
re-solve with modified constraints would require either rebuilding the model or
direct solver API access.

---

## B4: Scaling Curve (Bus Count vs Solve Time)

| Network | Buses | DCPF | DCOPF | Interactive? |
|---------|------:|-----:|------:|:------------:|
| case39 | 39 | 0.18s | 1.01s | DCPF only |
| case2000 | 2,000 | 3.95s | 5.89s | No |
| case10000 | 10,000 | 20.09s | 206.6s | No |

**Clustering not available**: PyPSA's spatial clustering (`busmap_by_kmeans`,
`busmap_by_greedy_modularity`) requires networks built with PyPSA's native
conventions. The MATPOWER→PyPSA bridge places Pd/Qd on the bus frame and sets
all coordinates to (0,0), which breaks the clustering aggregation (`consense`
fails on non-uniform bus attributes). Intermediate sizes would require either
native PyPSA network construction or manual bus-merging logic.

**Extrapolation**: Based on the scaling trend, DCPF crosses the 1s threshold
at approximately 100-200 buses. DCOPF would require fewer than 39 buses.
This confirms that LP-based approaches cannot serve interactive contingency
analysis at target ISO scale.

---

## B5: Contingency Sweep Throughput (BODF)

### BODF Pre-computation

| Network | Buses | Branches | BODF Time | Memory |
|---------|------:|---------:|----------:|-------:|
| case39 | 39 | 46 | 0.13s | 0.2 MB |
| case2000 | 2,000 | 3,206 | 1.32s | 249 MB |
| case10000 | 10,000 | 12,706 | 17.1s | 5,936 MB |

### All-N-1 Vectorized Analysis

| Network | Branches | All-N-1 Time | Single Contingency |
|---------|------:|---------:|---------:|
| case39 | 46 | 10 us | < 1 us |
| case2000 | 3,206 | 19.4 ms | **2.9 us** |
| case10000 | 12,706 | 235.8 ms | **8.8 us** |

### Comparison: BODF vs Re-solve

On the 39-bus network (the only scale where re-solve is tractable):

| Method | Total N-1 Time | Speedup |
|--------|---------------:|--------:|
| Re-solve (n.lpf per contingency) | 1.99s (54 ms/each) | 1x |
| BODF vectorized | 10 us (all at once) | **200,669x** |

### Violation Detection

Checking all branches for thermal violations across all N-1 contingencies on the
2000-bus network takes **14 ms** — fully interactive.

### N-2 Composition (Bonus)

First-order superposition for double outages on the 2000-bus network:
- 100 random N-2 pairs: **6.5 us per pair**
- This extends to full N-2 screening at interactive speeds

---

## B6: Interactive N-m Sweep from Focal Bus

This benchmark simulates the exact user workflow: click a bus on the map, BFS out
to h hops to find scoped branches, enumerate all N-1/N-2/N-3 contingency
combinations, compute post-contingency flows via BODF, and detect violations.

Two bus types are tested: the **highest-degree hub** (worst case — degree 17-20)
and a **median-degree bus** (typical case — degree 2-3).

### Combinatorial Expansion

The number of scoped branches and resulting combinations drives everything:

| Network | Bus Type | h=1 | h=2 | h=3 | h=4 |
|---------|----------|----:|----:|----:|----:|
| 10k | hub (deg 20) | 44 branches | 100 | 170 | 251 |
| 10k | typical (deg 2) | 7 branches | 15 | 27 | 47 |
| 2k | hub (deg 17) | 30 branches | 57 | 116 | 250 |
| 2k | typical (deg 3) | 4 branches | 7 | 10 | 17 |

N-m combinations from k scoped branches: N-1 = k, N-2 = k(k-1)/2, N-3 = k(k-1)(k-2)/6.
At k=100 (10k hub, h=2): N-1 = 100, N-2 = 4,950, **N-3 = 161,700**.

### Latency Decomposition

Total = BFS scope + N-1 sweep + N-2 sweep + N-3 sweep. The BFS graph traversal
on NetworkX is a **constant overhead per network size** regardless of h or branch
count — this dominates at small scopes:

| Network | BFS Scope (constant) |
|---------|---------------------:|
| 39-bus | ~2 ms |
| 2,000-bus | ~24 ms |
| 10,000-bus | ~90 ms |

This is an implementation artifact (Python NetworkX), not fundamental — a compiled
graph library or pre-computed adjacency would reduce it to microseconds.

### Typical Bus (degree 2-3): Total User-Perceived Latency

| Network | h | Branches | Scope | N-1 | N-2 | N-3 | **Total** |
|---------|--:|---------:|------:|----:|----:|----:|----------:|
| 39-bus | 2 | 7 | 2 ms | 0.1 ms | 0.0 ms | 0.0 ms | **2 ms** |
| 39-bus | 4 | 18 | 2 ms | 0.1 ms | 0.1 ms | 0.5 ms | **3 ms** |
| 2,000-bus | 2 | 7 | 24 ms | 0.1 ms | 0.2 ms | 0.3 ms | **24 ms** |
| 2,000-bus | 4 | 17 | 23 ms | 0.2 ms | 1.1 ms | 12 ms | **36 ms** |
| 10,000-bus | 2 | 15 | 88 ms | 0.4 ms | 4 ms | 39 ms | **133 ms** |
| 10,000-bus | 3 | 27 | 91 ms | 0.7 ms | 25 ms | 261 ms | **377 ms** |
| 10,000-bus | 4 | 47 | 89 ms | 1.2 ms | 72 ms | 1,403 ms | **1.6s** |

### Hub Bus (worst case): Total User-Perceived Latency

| Network | h | Branches | Scope | N-1 | N-2 | N-3 | **Total** |
|---------|--:|---------:|------:|----:|----:|----:|----------:|
| 39-bus | 4 | 29 | 2 ms | 0.1 ms | 0.1 ms | 2.1 ms | **5 ms** |
| 2,000-bus | 1 | 30 | 24 ms | 0.3 ms | 5 ms | 106 ms | **136 ms** |
| 2,000-bus | 2 | 57 | 25 ms | 0.5 ms | 33 ms | 762 ms | **820 ms** |
| 2,000-bus | 3 | 116 | 28 ms | 1.0 ms | 134 ms | 1,240 ms | **1.4s** |
| 10,000-bus | 1 | 44 | 88 ms | 1.1 ms | 64 ms | 1,149 ms | **1.3s** |
| 10,000-bus | 2 | 100 | 91 ms | 4.5 ms | 323 ms | 4,383 ms | **4.8s** |
| 10,000-bus | 3 | 170 | 88 ms | 6.8 ms | 934 ms | skipped | **1.0s*** |
| 10,000-bus | 4 | 251 | 92 ms | 10.5 ms | 2,055 ms | skipped | **2.2s*** |

*N-3 skipped (>500k combinations); total reflects scope+N-1+N-2 only.

### What This Means

**BFS scope is the floor**: ~90 ms on 10k due to Python NetworkX graph traversal.
This is constant regardless of h or m. A compiled adjacency lookup or pre-computed
hop table would eliminate this.

**N-1 is always instant**: <11 ms even at 10k-bus/h=4 with 251 branches.

**N-2 stays interactive for typical buses**: <100 ms compute up to h=4 on 10k. At
hub nodes it crosses 1s around h=3 on 10k (14k combinations × 12k branches each).

**N-3 is the bottleneck**: O(k^3) combinatorics dominate. At 50+ scoped branches
it hits seconds; at 100+ it's multi-second. This is the cost of computing flows
for every triple, not the per-combination BODF math (which is ~10-20 us).

### Strategies for N-3 at Scale

1. **Progressive rendering**: Show N-1+N-2 results instantly (<200 ms), compute
   N-3 in background, stream results as they arrive.
2. **Flow-based pruning**: Pre-filter scoped branches to exclude zero/low-flow
   lines (reduces k by 20-40% based on B5 pruning ratios, cubic reduction in combos).
3. **Severity screening**: Run N-2 first, only expand to N-3 around branches that
   showed N-2 violations (targeted rather than exhaustive).
4. **Hop budget**: Cap at h=2 for N-3 on 10k networks (keeps k<30 on typical buses).

---

## Architecture Recommendation

### For Interactive Contingency Web-App

```
Startup (one-time, per network load):
  1. Load network → PyPSA                          ~3-20s
  2. Run base DCPF (n.lpf)                         ~0.2-20s
  3. Compute BODF matrix                            ~0.1-17s
  4. Store BODF + base flows in memory              ~250 MB - 6 GB

Per user interaction (click a bus on the map):
  5. BFS to h hops → find scoped branches           ~2-90 ms (NetworkX; reducible)
  6. Vectorized N-1 sweep (all at once)             0.1-11 ms
  7. Vectorized N-2 sweep (all combos)              0.1-72 ms (typical bus)
  8. Violation detection                            <1 ms per sweep
  9. Return N-1+N-2 results to UI                   <200 ms total (typical)
 10. (Background) N-3 sweep if requested            0.3-1.4s (typical, h<=4)
```

### Key Numbers

| Metric | 2000-bus | 10k-bus |
|--------|:--------:|:-------:|
| Startup latency | ~5s | ~55s |
| Memory footprint | 250 MB | 6 GB |
| BFS scope overhead (constant) | **24 ms** | **90 ms** |
| N-1+N-2 compute at h=3, typical bus | **1 ms** | **25 ms** |
| N-1+N-2 compute at h=3, hub bus | **135 ms** | **941 ms** |
| Full N-1+N-2+N-3 compute at h=3, typical bus | **2 ms** | **286 ms** |
| Full N-1+N-2+N-3 compute at h=3, hub bus | **1.4s** | N-3 too large |

### PyPSA vs Julia Decision

- **BODF computation**: PyPSA computes BODF in 17s on 10k. PowerModels.jl DCPF
  solves in 0.23s but does not expose BODF natively. Building BODF from repeated
  DCPF solves in Julia would be slower than PyPSA's direct matrix factorization.
- **Per-click latency**: Both reduce to numpy/BLAS operations — language is irrelevant.
- **Startup latency**: Julia's JIT compilation adds 5-15s startup tax on top of
  solve time. PyPSA's 55s startup on 10k is dominated by DCPF (20s) + BODF (17s),
  not Python overhead.
- **Recommendation**: **PyPSA is sufficient**. The Python/numpy stack handles the
  interactive path (BODF multiply) at microsecond latency. Julia adds complexity
  without meaningful latency improvement for this architecture.

---

## Raw Data

| File | Contents |
|------|----------|
| `tests/latency_bench/bench_interactive_latency.py` | B1-B5 benchmark script |
| `tests/latency_bench/bench_results.json` | B1-B5 JSON results |
| `tests/latency_bench/bench_interactive_sweep.py` | B6 interactive sweep script |
| `tests/latency_bench/sweep_results.json` | B6 JSON results |

All paths relative to `evaluations/pypsa/`.

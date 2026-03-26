---
test_id: C-8
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: b1467033
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 315.11
timing_source: measured
peak_memory_mb: 6676.64
cpu_threads_used: 1
cpu_threads_available: 32
loc: 376
solver: HiGHS 1.13.1
timestamp: 2026-03-24T21:00:00Z
---

# C-8: SCOPF (N-1, 50 contingencies) on MEDIUM

## Result: PASS

## Approach

Loaded ACTIVSg10k (10,000 buses, 9,726 lines, 2,980 transformers, 2,485 generators)
via the shared `matpower_loader.load_pypsa()` with `overwrite_zero_s_nom=99999.0`.
The shared loader imports gencost data: 1,136 generators received costs from the `.m`
file, while 1,349 had zero marginal cost.

1. Ran base-case DCOPF to establish reference dispatch and identify contingency
   candidates.
2. Selected 50 contingency Lines (not Transformers, per A-9 observation that
   `optimize_security_constrained()` only accepts Line names) sorted by descending
   utilization from the base case. Selected lines had utilization 71%--99.4%, excluding
   lines at exactly 100% to preserve SCOPF feasibility headroom.
3. Ran SCOPF via `n.optimize.optimize_security_constrained(snapshots=[snapshot],
   branch_outages=contingency_lines)` with HiGHS at 1 thread and then at 32 threads.
4. Compared SCOPF dispatch to base-case dispatch to compute aggregate MW change.

PyPSA's `optimize_security_constrained()` uses BODF-based (Branch Outage Distribution
Factor) N-1 contingency constraints embedded directly in the LP formulation. This is
a single monolithic LP, not an iterative Benders decomposition.

## Output

### Base-Case DCOPF

| Metric | Value |
|--------|-------|
| Objective | $1,306,775 |
| Total dispatch | 150,917 MW |
| Solve time (n.optimize) | 265.2 s |
| HiGHS solver runtime | 1.94 s |

### SCOPF Results (1-thread)

| Metric | Value |
|--------|-------|
| Solver status | optimal |
| Objective | $1,329,325 |
| Cost premium vs base DCOPF | +1.73% |
| Simplex iterations | 9,084 |
| HiGHS solver runtime | 29.48 s |
| Total n.optimize wall-clock | 315.1 s |
| Peak memory (tracemalloc) | 6,676.6 MB |
| LP dimensions | 1,313,689 rows; 15,191 cols; 2,416,227 nonzeros |

### SCOPF Results (32-thread)

| Metric | Value |
|--------|-------|
| Solver status | optimal |
| Objective | $1,329,325 |
| HiGHS solver runtime | 34.27 s |
| Total n.optimize wall-clock | 343.7 s |
| Peak memory (tracemalloc) | 6,690.6 MB |
| Thread speedup | 0.92x (no benefit) |

### Thread Speedup Analysis

HiGHS dual simplex is inherently sequential -- multi-threading provides no speedup for
LP solves. The 32-thread run was slightly slower (343.7s vs 315.1s), likely due to
thread management overhead. This is a [solver-specific] limitation: HiGHS's simplex
solver does not parallelize. The IPM (interior point method) solver in HiGHS does
support parallelism, but PyPSA uses simplex by default.

The dominant cost is linopy model building and I/O (~285s of the 315s total), which is
single-threaded Python code [tool-specific]. The HiGHS solver itself takes only 29.5s
of the 315s wall-clock.

### Dispatch Change vs Base DCOPF

| Metric | Value |
|--------|-------|
| Aggregate dispatch change | 11,778 MW |
| Generators redispatched | 119 / 2,485 |
| Max single generator change | 441.5 MW (G1796: 0 -> 441 MW) |
| Binding lines after SCOPF | 0 |

Top redispatched generators:

| Generator | Base (MW) | SCOPF (MW) | Delta (MW) |
|-----------|-----------|------------|------------|
| G1796 | 0.0 | 441.5 | +441.5 |
| G226 | 248.0 | 0.0 | -248.0 |
| G433 | 237.5 | 0.0 | -237.5 |
| G855 | 233.0 | 0.0 | -233.0 |
| G150 | 232.7 | 0.0 | -232.7 |
| G149 | 232.7 | 0.0 | -232.7 |
| G1475 | 0.0 | 229.5 | +229.5 |
| G673 | 226.1 | 0.0 | -226.1 |
| G1816 | 0.0 | 221.0 | +221.0 |
| G1815 | 0.0 | 221.0 | +221.0 |

The SCOPF redispatches generators away from heavily loaded corridors and toward
locations that provide N-1 headroom, producing significant redispatch (11,778 MW
aggregate) despite only a 1.73% cost increase.

### SCOPF LMPs

| Metric | Value |
|--------|-------|
| LMP min | -$34.33/MWh |
| LMP max | $238.43/MWh |
| LMP mean | $19.30/MWh |

The wider LMP spread compared to base DCOPF (which had LMP range -$23.79 to $195.07
from C-3) reflects the additional security constraints binding on different network
regions.

### Contingency Selection

Selected 50 Lines with utilization 71.0%--99.4% from base DCOPF. The LP includes
1,313,689 rows (vs 43,089 for base DCOPF) due to the N-1 flow constraints for each
contingency on each monitored branch.

### Pass Condition Verification

| Condition | Met? |
|-----------|------|
| SCOPF completes with 50 contingencies on MEDIUM | Yes (optimal, 315s) |
| Wall-clock recorded | Yes |
| Peak memory recorded | Yes (6,676.6 MB) |
| Iterations recorded | Yes (9,084 simplex) |
| Binding contingencies recorded | Yes (0 binding base-case lines) |
| Aggregate dispatch change >= 5 MW | Yes (11,778 MW) |
| 1-thread timing reported | Yes (315.1s) |
| Max-thread timing reported | Yes (343.7s, 32 threads) |

## Workarounds

- **What:** Generator marginal costs assigned from gencost via shared loader.
- **Why:** `import_from_pypower_ppc` does not import the MATPOWER gencost table.
- **Durability:** stable -- uses documented `matpowercaseframes` CaseFrames API.
- **Grade impact:** Minimal -- gencost import is a known MATPOWER bridge gap.

- **What:** `overwrite_zero_s_nom=99999.0` for zero-rated branches.
- **Why:** MATPOWER rateA=0 means "no thermal limit" but PyPSA interprets it as zero capacity.
- **Durability:** stable -- documented `overwrite_zero_s_nom` parameter.
- **Grade impact:** None -- standard practice for MATPOWER imports.

## Timing

- **1-thread wall-clock:** 315.11 s (solver-only: 29.48 s) [tool-specific overhead: linopy model building ~285s]
- **32-thread wall-clock:** 343.70 s (solver-only: 34.27 s)
- **Thread speedup:** 0.92x (no benefit -- simplex is sequential) [solver-specific]
- **Timing source:** measured
- **Peak memory (1-thread):** 6,676.6 MB
- **Peak memory (32-thread):** 6,690.6 MB
- **Simplex iterations:** 9,084
- **CPU threads used:** 1 (primary timing)
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c8_scopf_medium.py`

Key API call:
```python
n.optimize.optimize_security_constrained(
    snapshots=[snapshot],
    branch_outages=contingency_lines,  # 50 Line names
    solver_name="highs",
    solver_options={"time_limit": 1800, "presolve": "on", "threads": 1},
)
```

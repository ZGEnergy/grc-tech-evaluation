---
tag: solver-issues
source_dimension: scalability
source_test: C-3
tool: pypsa
severity: high
timestamp: 2026-03-11T00:00:00Z
---

# Observation: linopy Model Construction Takes 2,560 s for 10k-Bus DC OPF

## Finding

Measured under controlled conditions: `n.optimize()` on ACTIVSg10k (10,000 buses) takes
2,618 s total. HiGHS solve takes 30–58 s (5,166 simplex iterations). linopy model
construction accounts for ~2,560 s — 98% of total optimize() time. The LP has 43,089
rows, 15,191 columns, and 274,129 nonzeros.

## Context

C-3 (DC OPF Scale) full timing breakdown:

| Phase | Time |
|-------|------|
| Network load | 25 s |
| linopy model construction | ~2,560 s |
| HiGHS solve | 30–58 s |
| Result extraction | ~27 s |
| **Total wall-clock** | **2,645 s** |

The A-3 expressiveness observation estimated ~260 s for model construction. The C-3
measured value of ~2,560 s is 10× higher — the difference is attributable to more
accurate measurement (C-3 used `time.perf_counter()` around the `n.optimize()` call
with HiGHS reporting its internal solve time).

## SCOPF Implication (C-8)

`optimize_security_constrained()` with N contingencies builds a single LP containing
(N+1) copies of the network constraint matrices. At N=5 contingencies:
- Estimated SCOPF LP size: ~258,000 rows, ~91,000 columns, ~1.6M nonzeros
- Estimated model build time: >15,000 s (6× base OPF build)
- This makes SCOPF at MEDIUM scale computationally infeasible with the current
  linopy-based formulation.

## Stochastic OPF Implication (C-6)

For the ACTIVSg2000 (2k-bus) stochastic scenario loop (C-6), linopy build takes 6–10 s
per scenario × 20 scenarios = 120–200 s for model construction alone. The LP solve
per scenario hits the 120s time limit. Total stochastic run: ~2,600 s (40+ minutes).

## Scaling Table (Measured)

| Scale | Buses | LP Size | linopy Build | HiGHS Solve | Total n.optimize() |
|-------|-------|---------|-------------|-------------|-------------------|
| TINY  | 39    | ~100 rows | ~1 s | <1 s | ~1 s |
| SMALL | 2,000 | ~10K rows | 6–10 s | <120 s | ~130 s |
| MEDIUM| 10,000| 43,089 rows | ~2,560 s | 30–58 s | ~2,618 s |

## Root Cause

linopy serializes optimization constraints by writing Python-loop-generated sparse
matrices to temporary LP files. This O(n) to O(n log n) serial process is dominated
by Python overhead, not I/O. No parallelization or incremental build is supported in
PyPSA 1.1.2.

## Mitigation

No built-in mitigation in PyPSA 1.1.2. External approaches:
1. Direct HiGHS Python API (bypasses linopy)
2. Model export to LP/MPS file, solve externally, parse results
3. Upstream linopy improvement (being tracked in linopy GitHub issues)

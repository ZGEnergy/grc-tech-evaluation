---
tag: solver-issues
source_dimension: expressiveness
source_test: A-3
tool: pypsa
severity: high
timestamp: 2026-03-11T00:00:00Z
---

# Observation: linopy Model Construction Dominates OPF Runtime at MEDIUM Scale

## Finding

For the ACTIVSg10k MEDIUM network (10,000 buses, 9,726 branches, 2,485 generators), linopy model construction takes ~260 seconds — dominating the 289-second total `n.optimize()` call time. HiGHS itself solves the LP in only 2.5 seconds (5,187 simplex iterations). The model construction overhead is the bottleneck, not the solver.

## Context

Discovered during A-3 DC OPF on ACTIVSg10k. Total `n.optimize()` call: 289s. Breakdown:
- linopy model construction: ~260 s (dominant)
- LP write to HiGHS: ~0.45 s
- HiGHS solve: ~2.5 s (5,187 iters)
- Extraction + overhead: ~26 s

At SMALL scale (2,000 buses), the same model construction takes ~80 s (vs ~1 s at TINY). Scaling:

| Scale | Buses | Model build | HiGHS | Total n.optimize() |
|-------|-------|-------------|-------|-------------------|
| TINY  | 39    | ~1 s        | <1 s  | ~1 s              |
| SMALL | 2,000 | ~80 s       | <5 s  | ~5 s              |
| MEDIUM| 10,000| ~260 s      | ~2.5 s| ~289 s            |

The model construction time scales roughly as O(N²) in bus count — 39→2000 is 51× buses but ~80× build time; 2000→10000 is 5× buses but ~3.3× build time (suggesting a more linear component).

## Implications

For Scalability (Suite C), this is a significant finding: repeated OPF calls (e.g., hourly market clearing, rolling optimization) at MEDIUM scale would incur 260-second overhead per solve call. HiGHS is not the bottleneck. Any scalability test involving `n.optimize()` at MEDIUM or larger scale will see this overhead.

For Extensibility (Suite B), any custom constraint pattern that rebuilds the linopy model per iteration (rather than using warm-start) will hit this overhead.

Mitigation paths: (1) linopy model caching/incremental rebuild — not currently supported in PyPSA 1.1.2; (2) direct HiGHS interface bypassing linopy — would require external optimization loop.

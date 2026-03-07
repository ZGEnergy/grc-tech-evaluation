---
test_id: A-10
tool: pypsa
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 72.9
peak_memory_mb: null
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-10: Lossy DC OPF with LMP Decomposition (SMALL)

## Result: PASS

## Approach

Same approach as TINY: solved lossless DCOPF then lossy DCOPF with `n.optimize(
transmission_losses=2)` (2-segment piecewise linear loss approximation). Decomposed
LMPs into energy, congestion, and loss components by querying constraint duals from
the Linopy model. Computed per-line congestion rents.

## Output

| Metric | Lossless DCOPF | Lossy DCOPF |
|--------|---------------|-------------|
| Objective ($) | 859,978 | 883,276 |
| LMP min ($/MWh) | 0.0 | 0.0 |
| LMP max ($/MWh) | 24.41 | 21.59 |
| LMP mean ($/MWh) | 17.87 | 18.21 |

**Objective increase with losses:** 23,298 (2.71%)

**LMP decomposition (sample buses):**

| Bus | Total LMP | Energy | Congestion | Loss Effect |
|-----|-----------|--------|------------|-------------|
| 1001 | 17.61 | 0.0 | 17.61 | -0.025 |
| 1002 | 16.59 | 0.0 | 16.59 | -0.683 |
| 1003 | 15.70 | 0.0 | 15.70 | -1.365 |
| 1004 | 16.16 | 0.0 | 16.16 | -1.402 |
| 1005 | 6.84 | 0.0 | 6.84 | -1.322 |

Loss components are non-zero and vary by bus location, confirming physically meaningful
loss-inclusive pricing.

**Congestion rents:** 2,336 of 2,359 lines have non-zero congestion rent.
Total congestion rent: $52,743. Max single-line rent: $3,198.

## Workarounds

- **What:** Manually set marginal_cost on 544/544 generators from gencost data.
- **Why:** PPC importer does not import gencost.
- **Durability:** stable
- **Grade impact:** None — standard workaround across all PyPSA tests.
- **Version tested:** PyPSA 1.1.2

## Timing

- **Wall-clock:** 72.9 s (both lossless + lossy solves)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a10_lossy_dcopf_lmp_small.py`

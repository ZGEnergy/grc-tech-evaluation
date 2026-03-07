---
test_id: C-6
tool: pypsa
dimension: scalability
network: SMALL
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 2219.1
peak_memory_mb: 7125
loc: null
solver: highs
timestamp: 2026-03-07T00:00:00Z
---

# C-6: Stochastic DCOPF Scale (SMALL)

## Result: PASS

## Approach

Solved 20 scenarios of 12-hour multi-period DCOPF on the ACTIVSg 2000-bus network.
Each scenario applies independent load and generator capacity perturbations by
resource type (baseload +-3%, intermediate +-7%, peaker +-10%, load +-8%).

Uses deterministic loop approach: `n.copy()` per scenario, modify loads/generator
p_nom, `n.optimize()`.

## Output

| Metric | Value |
|--------|-------|
| Scenarios requested | 20 |
| Scenarios solved | 20 |
| Scenarios failed | 0 |
| Total wall-clock | 2219 s |
| Solve time (total) | 2213 s |
| Solve time (mean) | 110.6 s/scenario |
| Solve time (std) | 90.1 s |
| Solve time (min) | 39.2 s |
| Solve time (max) | 295.5 s |
| Peak memory | 7,125 MB |

**Per-scenario times show significant variance** (39-296s). The slowest scenarios
have higher load factors that create more congestion and require more HiGHS
iterations. Scenarios 12-15 cluster around 280-296s.

**Objective summary:**

| Metric | Value |
|--------|-------|
| Mean | $10,244,609 |
| Std | $652,000 |
| Min | $9,175,944 |
| Max | $11,216,290 |

**LMP summary:**

| Metric | Value |
|--------|-------|
| Mean LMP | 18.02 $/MWh |
| Std LMP | 1.44 $/MWh |
| Min LMP | -4.67 $/MWh |
| Max LMP | 25.35 $/MWh |

Negative LMPs observed in some scenarios, indicating oversupply at certain buses.

## Workarounds

- **What:** Deterministic loop (PyPSA has no native stochastic optimization). Manually
  set marginal_cost from gencost data.
- **Durability:** stable
- **Grade impact:** None for scalability — the test measures loop-based scenario solve
  performance.
- **Version tested:** PyPSA 1.1.2

## Timing

- **Wall-clock:** 2219 s
- **Peak memory:** 7,125 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c6_stochastic_scale.py`

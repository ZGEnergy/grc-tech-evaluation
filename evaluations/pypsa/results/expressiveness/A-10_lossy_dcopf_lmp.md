---
test_id: A-10
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v10
skill_version: v1
test_hash: 0a550931
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.93
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 332
solver: HiGHS
timestamp: 2026-03-13T00:00:00Z
---

# A-10: Lossy DC OPF with LMP Decomposition

## Result: PASS

## Approach

Solved two DC OPF instances on case39.m (TINY) using PyPSA 1.1.2:

1. **Lossless baseline:** Standard `n.optimize()` with differentiated marginal costs ($10-$100 linearly across 10 generators) and 70% branch derating for congestion signal.

2. **Lossy DC OPF:** `n.optimize(transmission_losses=3)` with 3-segment piecewise linearization of I^2*R losses. PyPSA's `transmission_losses` parameter activates a piecewise-linear approximation of ohmic losses on each branch, adding auxiliary variables and constraints to the LP.

LMPs extracted from `n.buses_t.marginal_price`. Loss components computed as the bus LMP difference from the slack bus energy component. Congestion rents computed per-line as `(LMP_to - LMP_from) * flow`.

Network loaded via shared `matpower_loader.load_pypsa()`. Marginal costs overridden from uniform $0.30/MWh to differentiated $10-$100 for congestion signal.

## Output

### Objective Comparison

| Metric | Value |
|--------|-------|
| Lossless objective | $370,208.16/h |
| Lossy objective | $390,361.27/h |
| Cost premium from losses | $20,153 (5.4%) |

### Loss Analysis

| Metric | Value |
|--------|-------|
| Total implied losses | 47.6 MW |
| Loss as % of load | 0.761% |
| Total generation | 6301.8 MW |
| Total load | 6254.2 MW |

### LMP Decomposition

| Metric | Value |
|--------|-------|
| Slack bus | Bus 31 |
| Energy component (slack LMP) | $617.29/MWh |
| Loss component range | [-617.3, +165.5] $/MWh |
| Buses with non-zero loss component | 37 of 39 |
| Buses with LMP change (lossy vs lossless) | 38 of 39 |

### Congestion Rents

| Metric | Value |
|--------|-------|
| Total congestion rent | $606,363/h |
| Lines with non-zero congestion rent | 35 of 35 |

### Internal Consistency Checks

| Check | Result |
|-------|--------|
| (a) Non-zero loss components present | PASS |
| (b) Losses = 0.761% of load (0.5-3% range) | PASS |
| (c) Lossy obj >= Lossless obj | PASS |
| (d) Bus LMPs change between lossy and lossless | PASS (38/39 buses) |

All four consistency checks passed. The loss-inclusive LMPs show physically correct behavior: losses are in the expected 0.5-3% range, the lossy objective exceeds the lossless baseline, and loss components are non-zero on 37 of 39 buses.

## Workarounds

None required. The `transmission_losses` parameter on `n.optimize()` is a documented public API feature. LMP decomposition is directly available from `n.buses_t.marginal_price`.

Note: Marginal costs were overridden from the case39 default (uniform $0.30/MWh) to differentiated costs ($10-$100) to create a congestion signal. The shared loader correctly imports gencost but the uniform costs produce no congestion without derating.

## Timing

- **Wall-clock:** 1.93s (lossless + lossy combined)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** N/A (LP)
- **CPU cores used:** 1 (threads=1)

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a10_lossy_dcopf_lmp_tiny.py`

Key API call for lossy DC OPF:
```python
n.optimize(
    transmission_losses=3,  # 3-segment piecewise linearization
    solver_name="highs",
    solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
)
```

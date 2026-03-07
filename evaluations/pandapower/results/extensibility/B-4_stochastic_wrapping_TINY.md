---
test_id: B-4
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 5.19
peak_memory_mb: null
loc: 175
solver: PYPOWER interior point
timestamp: 2026-03-06T00:00:00Z
---

# B-4: Stochastic wrapping -- 20 scenarios x 12hr multi-period DCOPF

## Result: QUALIFIED PASS

## Approach

pandapower has no native multi-period DCOPF or scenario API. The test was implemented as a loop over 20 scenarios x 12 hourly timesteps (240 total solves), modifying network parameters in-place via DataFrame assignment and solving with `rundcopp()` per (scenario, hour) pair.

### Scenario Generation

Generators were classified by marginal cost quartile as a proxy for resource type:
- **Baseload:** 2 generators (lowest cost)
- **Intermediate:** 4 generators (mid-range cost)
- **Peaker:** 3 generators (highest cost)

Correlated perturbations were generated per resource type using a shared base signal (sigma=0.05) plus individual noise (sigma=0.02). Load perturbations used a 12-hour demand shape curve with stochastic scaling (sigma=0.08).

### Solve Loop

For each (scenario, hour):
1. Scale `net.load["p_mw"]` by hourly shape and load perturbation
2. Adjust `net.gen["max_p_mw"]` by resource-type-correlated perturbation
3. Call `pp.rundcopp(net)`
4. Extract dispatch, LMPs, and objective

No model reconstruction per solve -- only DataFrame value updates.

**Solver deviation:** Uses PYPOWER interior point solver, not HiGHS as specified.

## Output

| Metric | Value |
|--------|-------|
| Scenarios | 20 |
| Hours per scenario | 12 |
| Total solves | 240 |
| Converged solves | 208 (86.7%) |
| Failed solves | 32 (13.3%) |
| Solve loop time | 5.09 s |
| Per-solve average | 21.2 ms |

Objective statistics across converged solves:

| Stat | Value |
|------|-------|
| Mean | 27,813.9 |
| Std dev | 11,596.0 |
| Min | 12,214.2 |
| Max | 51,806.3 |

LMP statistics across converged solves:

| Stat | Value (mean LMP) |
|------|-------|
| Mean | 11.10 |
| Std dev | 3.93 |
| Min | 7.00 |
| Max | 31.57 |

The 13.3% solve failure rate occurs at low-load hours where the PYPOWER interior point solver encounters numerical difficulty with the reduced-load dispatch.

## Workarounds

- **What:** Sequential solve loop with in-place DataFrame modification instead of native multi-period or scenario API.
- **Why:** pandapower has no multi-period DCOPF, no scenario-indexed timeseries, and no built-in stochastic framework. Each solve is independent.
- **Durability:** stable -- the approach uses only public APIs (`net.load["p_mw"]` assignment, `rundcopp()`). DataFrame modification is pandapower's standard data interface.
- **Grade impact:** The loop overhead is minimal (no model reconstruction), and the approach is straightforward. However, the lack of native multi-period support means inter-temporal constraints (ramp rates) cannot be enforced.

- **What:** Solver deviation -- PYPOWER interior point instead of HiGHS.
- **Why:** `rundcopp()` hard-codes the PYPOWER solver. No swap mechanism exists.
- **Durability:** stable -- documented behavior.
- **Grade impact:** The 13.3% failure rate may be partially attributable to solver limitations.

## Timing

- **Wall-clock:** 5.19 s (total)
- **Solve loop:** 5.09 s (240 solves)
- **Per-solve average:** 21.2 ms
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b4_stochastic_wrapping.py`

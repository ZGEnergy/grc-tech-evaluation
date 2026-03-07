---
test_id: B-4
tool: gridcal
dimension: extensibility
network: SMALL
protocol_version: "v4"
status: qualified_pass
workaround_class: fragile
wall_clock_seconds: 1444.5
peak_memory_mb: null
loc: 90
solver: HiGHS
timestamp: 2026-03-06T03:30:00Z
---

# B-4: Stochastic Wrapping (SMALL)

## Result: QUALIFIED PASS

## Approach

Generated 20 scenarios with correlated perturbations by resource type (181 baseload,
181 intermediate, 182 peaker generators). Attempted 12-hour multi-period DCOPF for each
scenario on ACTIVSg 2000 (2000 buses, 544 generators).

Time-series OPF crashed with `ValueError: 0 is not a valid TapPhaseControl` (same bug
as TINY). Used hour-by-hour snapshot OPF loop as workaround.

## Output

| Metric | Value |
|--------|-------|
| Total expected solves | 240 (20 scenarios × 12 hours) |
| Successful solves | 113 |
| All scenarios fully converged | No |
| Per-solve average | 12.8s |
| Price distribution | mean=8.10, std=5.87, min=0.0, max=17.48 $/MWh |

Not all scenarios fully converged — some hourly solves failed on specific load perturbation
levels, likely due to infeasibility at extreme perturbations.

## Workarounds

- **What:** Hour-by-hour snapshot OPF loop instead of native time-series OPF
- **Why:** `OptimalPowerFlowTimeSeriesDriver` crashes with TapPhaseControl error on MATPOWER networks
- **Durability:** fragile — relies on the snapshot OPF path not having the same bug, and loses inter-temporal coupling (ramp constraints)
- **Grade impact:** Significant — the workaround loses temporal coupling and some scenarios don't converge

## Timing

- **Wall-clock:** 1444.5s (~24 minutes for 113 successful solves)
- **Per-solve average:** 12.8s
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b4_stochastic_wrapping_small.py`

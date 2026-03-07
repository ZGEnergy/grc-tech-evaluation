---
test_id: B-4
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: fragile
wall_clock_seconds: 19.758
peak_memory_mb: null
loc: 195
solver: "HiGHS"
timestamp: 2026-03-06T02:00:00Z
---

# B-4: Stochastic Wrapping

## Result: QUALIFIED PASS

## Approach

Generated 20 scenarios with correlated perturbations by resource type (baseload, intermediate, peaker). Each scenario has a shared random factor per resource type plus individual noise, producing realistic correlation structure. Applied a 12-hour load profile with per-scenario load scaling.

Attempted time-series OPF first (`vge.run_linear_opf_ts()`), which crashed with TapPhaseControl error. Fell back to hour-by-hour snapshot DC OPF loop.

## Output

### Scenario Generation

- 20 scenarios, 12 hours each
- Generators classified by cost: 3 baseload, 3 intermediate, 4 peaker
- Correlated perturbations: shared factor per resource type (sigma=0.05) + individual noise (sigma=0.03)
- Load perturbation: independent per scenario (sigma=0.05)

### Solve Results

| Metric | Value |
|--------|-------|
| Total solves | 240 (20 x 12) |
| All converged | Yes |
| Wall-clock | 19.76s |
| Per-solve average | 82ms |

### Price Distribution Across Scenarios

| Statistic | Value ($/MWh) |
|-----------|---------------|
| Mean | 1.172 |
| Std Dev | 1.744 |
| Min | 0.300 |
| Max | 4.660 |

Price variation across scenarios demonstrates that perturbations produce meaningfully different dispatch and pricing outcomes.

## Time-Series OPF Crash

`vge.run_linear_opf_ts()` fails with:

```
ValueError: 0 is not a valid TapPhaseControl
```

This is a known GridCal bug on case39.m related to transformer tap/phase control enumeration. The time-series OPF cannot run on this network.

## Why QUALIFIED PASS (not PASS)

The pass condition requires the tool to accept timeseries inputs programmatically and the scenario loop to be expressible without excessive overhead.

**Satisfied:**
- Tool accepts programmatic timeseries inputs (load profiles, generator profiles set via `P_prof`, `Pmax_prof` attributes)
- Scenario loop is straightforward Python -- no config files needed
- All 240 solves converge; prices and dispatch collected

**Not satisfied:**
- Time-series OPF crashes, forcing hour-by-hour snapshot loop
- No inter-temporal constraints (ramp rates) in the workaround
- 82ms per solve is reasonable but re-loading the grid each hour adds overhead
- The workaround is classified as fragile because it depends on the TapPhaseControl bug remaining the only obstacle

## Workarounds

1. **Time-series OPF blocked** (TapPhaseControl bug) -- fragile
2. **Hour-by-hour snapshot OPF loop** -- works but loses inter-temporal coupling

## Timing

- **Total (20 scenarios x 12 hours):** 19.76s
- **Per scenario:** ~0.99s
- **Per solve:** ~82ms

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b4_stochastic_wrapping.py`

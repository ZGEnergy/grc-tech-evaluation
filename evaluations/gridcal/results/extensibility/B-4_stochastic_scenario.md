---
test_id: B-4
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v11"
skill_version: v2
test_hash: "341fbe16"
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 11.33
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 321
solver: HiGHS
timestamp: "2026-03-24T00:00:00Z"
---

# B-4: Generate 20 stochastic scenarios, solve 12hr multi-period DCOPF for each

## Result: QUALIFIED PASS

## Approach

GridCal's time-series OPF (`run_linear_opf_ts` with `time_indices`) supports multi-period DCOPF natively. However, VeraGridEngine 5.6.28 has a bug where the `TapPhaseControl` enum profile initialization fails when using time-indexed compilation: `ValueError: 0 is not a valid TapPhaseControl`. This occurs in the sparse profile system where the default value (0) is not a valid enum member.

**Workaround:** Solved each of the 12 hours as an independent snapshot OPF, modifying load values between solves. This uses only the documented public API (`load.P = value`, `run_linear_opf_ts(grid, time_indices=None, ...)`).

**Scenario generation:**
- 20 scenarios with independent perturbations by resource type
- Load: +/-10% uniform perturbation per bus per hour (seed=42)
- Gen Pmax: +/-5% perturbation per generator class
- Differentiated costs from gen_temporal_params.csv (hydro $5, nuclear $10, coal $25, gas $40)
- 70% branch derating to create congestion

## Output

| Metric | Value |
|--------|-------|
| Scenarios | 20 |
| Hours per scenario | 12 |
| Converged | 20/20 |
| Mean solve time per scenario | 0.566 s |
| Total solve time | 11.33 s |

**Objective function statistics across 20 scenarios:**

| Stat | Value |
|------|-------|
| Mean | 8395.04 |
| Std | 153.32 |
| Min | 8074.70 |
| Max | 8614.04 |

**LMP statistics:**

| Stat | Value |
|------|-------|
| Mean across scenarios | 28.35 $/MWh |
| Std across scenarios | 0.46 $/MWh |

All 20 scenarios produce distinct objective values and LMP distributions, confirming that the scenario loop is expressible and results are collectable in a structured format. Objective variation (std = 153.32) confirms the stochastic perturbations produce meaningful dispatch differences.

## Workarounds

- **What:** Solved each hour as an independent snapshot OPF instead of using native multi-period time-series OPF.
- **Why:** VeraGridEngine 5.6.28 bug: `TapPhaseControl` enum sparse profile default value (0) is not a valid enum member. The `compile_numerical_circuit_at` function fails when compiling at a non-None time index for networks with transformers.
- **Durability:** stable -- The sequential snapshot approach uses only documented public API (`load.P = value`, `run_linear_opf_ts(grid, time_indices=None, ...)`). However, it loses inter-temporal coupling (ramp constraints, storage SoC tracking) that the native time-series OPF would provide.
- **Grade impact:** The test demonstrates that GridCal accepts timeseries inputs programmatically and that the scenario loop is expressible. The loss of inter-temporal coupling is a consequence of the bug workaround, not an inherent API limitation. `workaround_class: stable` supports `qualified_pass`.
- **Version tested:** VeraGridEngine 5.6.28

## Timing

- **Wall-clock:** 11.33 seconds (20 scenarios x 12 hours = 240 snapshot solves)
- **Timing source:** measured
- **Mean per-scenario solve:** 0.566 seconds
- **Peak memory:** not measured
- **Solver:** HiGHS

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b4_stochastic_scenario.py`

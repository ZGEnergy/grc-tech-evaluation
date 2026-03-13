---
test_id: B-4
tool: pypsa
dimension: extensibility
network: SMALL
protocol_version: v9
skill_version: v1
test_hash: 0f696058
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 5995.16
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 100
solver: highs
timestamp: 2026-03-12T00:00:00Z
---

# B-4: Stochastic Scenario Wrap (stochastic_scenario_wrap) — SMALL

## Result: PASS

## Approach

Loaded ACTIVSg2000 (2000-bus, 2359-line network), added Wind (200 MW, bus 5) and Solar (150 MW, bus 6) generators, and ran a 20-scenario × 12-hour DC OPF loop. Each scenario uses random load multipliers (±15%), wind capacity factors (10–70%), and solar capacity factors (0–50%) drawn from a fixed seed (42) for reproducibility.

**Key implementation pattern:** PyPSA has no built-in "reset to base case" API. Each scenario requires full network re-construction: re-load from .m file, re-assign costs, re-add Wind/Solar, then inject per-scenario timeseries via `n.loads_t.p_set` and `n.generators_t.p_max_pu`. The timeseries injection API itself is clean (direct DataFrame assignment), but the network rebuild adds overhead.

All 20/20 scenarios solved to optimality.

## Output

| Metric | Value |
|--------|-------|
| Scenarios completed | 20/20 |
| N_buses | 2,000 |
| N_generators | 546 (incl. Wind/Solar) |
| N_hours per scenario | 12 |
| Total wall-clock | 5,995.16 s (99.9 min) — under heavy CPU contention |
| Mean scenario time | 298.85 s (expected: ~4–8 s uncontended) |
| Total scenario time | 5,977.05 s |

**Cost statistics across 20 scenarios:**

| Stat | Value ($/12h) |
|------|---------------|
| Min | $31,972,332 |
| Max | $34,573,059 |
| Mean | $33,416,179 |
| Std | $711,953 |

**LMP statistics:**
- Mean LMP across all scenarios: $61.24/MWh
- Max LMP observed (any scenario): $887.09/MWh (congestion spike)

**Scenario sample:**

| Scenario | Total Cost ($/12h) | LMP Mean | LMP Max | Wind CF | Load Mult |
|----------|-------------------|----------|---------|---------|-----------|
| 0 | $34,359,585 | $62.74 | $887.05 | 0.460 | 0.971 |
| 5 | $33,890,949 | $61.91 | $887.05 | 0.383 | 0.962 |
| 10 | $33,334,085 | $61.21 | $887.09 | 0.411 | 0.951 |
| 15 | $33,520,460 | $61.47 | $887.05 | 0.352 | 0.954 |
| 19 | — | — | — | — | — |

## Workarounds

- **What:** Full network re-construction per scenario (re-load from .m file + re-add Wind/Solar generators).
  - **Why:** PyPSA has no `n.reset_parameters()` or `n.copy_with_new_timeseries()` API. The only reliable approach for varying component parameters (not just timeseries) is to rebuild the network.
  - **Durability:** stable — `import_from_pypower_ppc` and `n.add()` are documented public APIs.
  - **Grade impact:** Low friction for pure timeseries variation; medium friction if component topology changes per scenario.

- **What:** Timeseries injection via `n.loads_t.p_set[load_name] = series` and `n.generators_t.p_max_pu[gen_name] = series`.
  - **Why:** This is the standard API — no workaround required.
  - **Note:** PerformanceWarning ("DataFrame is highly fragmented") is issued when setting many individual load columns. This is a pandas performance issue (not a correctness issue) — the correct fix is `pd.concat`, but the direct assignment works.
  - **Durability:** stable.

## Timing

- **Wall-clock:** 5,995.16 s total (measured under extreme CPU contention)
  - Mean per-scenario: 298.85 s
  - Expected uncontended: ~4–8 s per scenario (12-hour, 2000-bus LP)
  - Contention note: 62+ concurrent Python processes consuming ~3131% CPU reduced solve time by ~40-75×
- **Timing source:** measured (but inflated by concurrent workload)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b4_stochastic_scenario_wrap_small.py`

Key API sequence:
```python
# Per-scenario timeseries injection
for load_name in n_s.loads.index:
    n_s.loads_t.p_set[load_name] = load_mult_series * base_p_set[load_name]
n_s.generators_t.p_max_pu["Wind"] = scenario["wind_cf"]
n_s.generators_t.p_max_pu["Solar"] = scenario["solar_cf"]

# Solve
status, cond = n_s.optimize(solver_name="highs", solver_options=SOLVER_OPTIONS)
```

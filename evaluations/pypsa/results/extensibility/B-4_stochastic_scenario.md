---
test_id: B-4
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v11
skill_version: v2
test_hash: b8e072ef
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 7.46
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 279
solver: HiGHS
timestamp: 2026-03-24T00:00:00Z
---

# B-4: Generate 20 scenarios, solve 12hr multi-period DCOPF for each on TINY

## Result: PASS

## Approach

1. **Network loading**: Loaded base network via `matpower_loader.load_pypsa()`. Set 12-hour snapshots via `n.set_snapshots(pd.date_range(..., periods=12, freq='h'))`.
2. **Differentiated costs**: Loaded `gen_temporal_params.csv` from Modified Tiny data, assigned fuel-type costs (hydro $5, nuclear $10, coal $25, gas $40).
3. **Load profiles**: Loaded first 12 hours from `load_24h.csv`, assigned to each load bus via `n.loads_t.p_set[load_name] = values`.
4. **Scenario generation**: Generated 20 scenarios with `np.random.default_rng(42)`, each with per-hour load multipliers drawn from Uniform(0.85, 1.05).
5. **Scenario loop**: For each scenario, used `n_base.copy()` to clone the base network (no file re-read), applied load multipliers via `n_s.loads_t.p_set[load_name] = base_p * mult`, then solved with `n_s.optimize(solver_name='highs', solver_options=...)`.
6. **Result collection**: Collected LMPs (`n.buses_t.marginal_price`), dispatch (`n.generators_t.p`), and objective value (`n.objective`) per scenario.

Solver settings: HiGHS, time_limit=300, presolve=on, threads=1.

## Output

| Metric | Value |
|--------|-------|
| Scenarios | 20 |
| Hours per scenario | 12 |
| Succeeded | 20 / 20 |
| Failed | 0 |
| Mean solve time | 0.315s per scenario |
| Total scenario time | 6.29s |

**Cost statistics across 20 scenarios:**

| Statistic | Value |
|-----------|-------|
| Min cost | $977,044 |
| Max cost | $1,109,530 |
| Mean cost | $1,040,459 |
| Std dev | $37,735 |

**LMP statistics:**

| Statistic | Value |
|-----------|-------|
| Mean LMP across all scenarios | $37.14/MWh |
| LMP range per scenario | $5.00 - $94.21/MWh |

Results show meaningful cost and LMP variation across scenarios, confirming that the load multiplier perturbation produces differentiated outcomes.

**Pass condition verification:**
- Timeseries inputs accepted programmatically: YES (`n.loads_t.p_set` DataFrame assignment)
- Scenario loop without excessive overhead: YES (`n.copy()` + attribute assignment, ~0.31s per scenario)
- Results collectable in structured format: YES (LMPs, dispatch, costs all extracted as DataFrames/scalars)

## Workarounds

None required. All functionality uses documented public APIs:
- `n.set_snapshots()` for multi-period setup
- `n.loads_t.p_set` for programmatic timeseries injection
- `n.optimize()` for DCOPF
- `n.buses_t.marginal_price` for LMP extraction
- `n.copy()` for efficient scenario cloning

## Timing

- **Wall-clock:** 7.46s (total including network loading + 20 scenarios)
- **Timing source:** measured
- **Per-scenario solve:** 0.315s mean
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b4_stochastic_scenario.py`

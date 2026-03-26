---
test_id: B-4
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: v11
skill_version: v2
test_hash: "341fbe16"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 6.01
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 341
solver: "PYPOWER interior-point (bundled)"
timestamp: "2026-03-13T00:00:00Z"
---

# B-4: 20-scenario 12hr multi-period DCOPF with stochastic timeseries

## Result: PASS

## Approach

pandapower's `rundcopp()` is single-period, so a 20-scenario x 12-hour stochastic DCOPF requires 240 independent solves in a nested loop. The test verifies that:

1. **Timeseries inputs are programmatic:** Load profiles and renewable scenario multipliers are set by directly assigning values to `net.load["p_mw"]` and `net.sgen["p_mw"]` DataFrames -- no config files required.

2. **Scenario loop has no excessive per-scenario overhead:** The same `pandapowerNet` object is reused across all 240 solves. Only DataFrame values are updated between solves -- no model reconstruction or re-initialization needed.

3. **Results are collectable in structured format:** Dispatch (gen/ext_grid MW), objectives, and LMPs are extracted after each solve into Python dicts/lists.

**Workflow:**
- Loaded base network once via `load_pandapower()` and set up differentiated costs
- Added 5 renewable generators (3 wind, 2 solar) as `sgen` elements via `pp.create_sgen()`
- For each of 20 scenarios x 12 hours: updated loads from `load_24h.csv`, applied scenario multipliers from `scenario_multipliers_50x24.csv` to renewable generation, solved DC OPF
- Collected dispatch, objective, and LMPs from `net._ppc["bus"][:, 13]`

## Output

| Metric | Value |
|--------|-------|
| Total solves | 240 (20 scenarios x 12 hours) |
| Convergence rate | 100% (240/240) |
| Total solve time | 5.35 s |
| Time per solve | 22.3 ms |
| Objective range | $60,931 -- $110,279 |
| Objective mean | $82,709 |
| Objective std | $16,337 |
| Total generation range | 3,819 -- 5,204 MW |

**Hour 1 cross-scenario variation:**
- Objective range: $75,093 -- $77,831
- Spread: 3.6% (confirms scenario multipliers produce meaningful variation)

**Sample dispatch (scenario 1, hour 1):**
- Gen 0 (hydro, bus 30): 691 MW
- Gen 4 (coal, bus 34): 687 MW
- Gen 5 (nuclear, bus 35): ~0 MW (decommitted by optimizer)
- Ext_grid (bus 31): 970 MW
- Objective: $76,095

## Workarounds

None required. The entire workflow uses documented public APIs:
- `pp.create_sgen()` for adding renewable generators
- Direct DataFrame assignment for timeseries inputs (`net.load.at[idx, "p_mw"] = value`)
- `pp.rundcopp()` for each solve
- `net.res_gen`, `net.res_ext_grid`, `net.res_cost` for result extraction

pandapower's DataFrame-centric design makes programmatic timeseries input natural. The single-period limitation means the user must manage the time loop, but this is idiomatic for the tool.

## Timing

- **Wall-clock:** 6.01 s (total including network load + 240 solves)
- **Timing source:** measured
- **Solve time:** 5.35 s (240 solves)
- **Time per solve:** 22.3 ms
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b4_stochastic_scenario_wrapping.py`

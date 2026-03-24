---
test_id: B-8
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v11"
skill_version: v2
test_hash: "dad5cf97"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.24
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 221
solver: HiGHS
timestamp: "2026-03-24T00:00:00Z"
---

# B-8: Reference bus configuration — DC OPF with three slack configurations

## Result: PASS

## Approach

Tested three slack bus configurations by toggling `bus.is_slack` on Bus objects:

1. Load network and apply differentiated costs (hydro $5, nuclear $10, coal $25, gas $40) plus 70% branch derating to create congestion
2. **Config 1 (default):** Slack at bus index 30 (bus "31") — the MATPOWER default
3. **Config 2:** Clear all `is_slack` flags, set `buses[10].is_slack = True` (bus "11")
4. **Config 3:** Clear all `is_slack` flags, set `buses[20].is_slack = True` (bus "21")
5. Solve DC OPF for each configuration using `vge.linear_opf()` with HiGHS

The slack bus is configurable via a simple boolean property on Bus objects — no model reconstruction is required to switch the reference bus.

## Output

| Config | Slack Bus | LMP Min ($/MWh) | LMP Max ($/MWh) | LMP Spread | Total Gen (MW) |
|--------|-----------|-----------------|-----------------|------------|----------------|
| Default | 31 (idx 30) | 5.00 | 84.38 | 79.38 | 6254.23 |
| Bus 11 | 11 (idx 10) | 5.00 | 84.38 | 79.38 | 6254.23 |
| Bus 21 | 21 (idx 20) | 5.00 | 84.38 | 79.38 | 6254.23 |

**LMP differences between configurations:**

| Comparison | Max Absolute Difference |
|-----------|------------------------|
| Default vs Bus 11 | 2.98e-13 |
| Default vs Bus 21 | 2.98e-13 |
| Bus 11 vs Bus 21 | 2.70e-13 |

**LMPs are invariant to slack bus selection** (differences are at machine epsilon). This is mathematically correct for GridCal's PTDF-based DC OPF formulation. The PTDF matrix is computed via a pseudo-inverse approach that does not depend on the slack bus choice, unlike B-matrix-based DC OPF where the reference bus determines the angle reference frame and thus affects the flow equations.

This invariance is a positive architectural property: LMPs represent the true marginal cost of power at each bus regardless of which bus is designated as reference. The same property holds in ISO market software where LMPs should not change with reference bus selection.

## Workarounds

None required. The `bus.is_slack` property is a documented, public attribute that can be freely toggled without model reconstruction.

## Timing

- **Wall-clock:** 1.24 seconds (three DC OPF solves plus network loading)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver:** HiGHS via PuLP

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b8_reference_bus_config.py`

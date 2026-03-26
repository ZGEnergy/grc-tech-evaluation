---
test_id: G-2
tool: powersimulations
dimension: gate
network: SMALL
protocol_version: v11
skill_version: v2
test_hash: 326e8597
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 1.8
timestamp: "2026-03-24T00:00:00Z"
---

# G-2: Ingest ACTIVSg 2000-bus reference network (SMALL)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Expected counts:** 2000/3206/544
- **Actual counts:** 2000/3206/544
- **Load time:** 1.80s
- **Data quality notes:**
  - No NaN/infinite in bus voltages
  - All branch ratings are finite
  - Slack bus identified: WADSWORTH 3
  - 109 generators (RenewableDispatch) do not support `get_active_power_limits` -- type hierarchy limitation in PowerSystems.jl, not missing data
  - All 544 generators have operation cost data
  - No branches with zero reactance
- **Errors/warnings:** None

## Test Script

`evaluations/powersimulations/test/run_gate_tests.jl`

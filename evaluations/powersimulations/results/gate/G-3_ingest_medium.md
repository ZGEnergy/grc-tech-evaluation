---
test_id: G-3
tool: powersimulations
dimension: gate
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: d5cc0c0a
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 3.06
timestamp: "2026-03-24T00:00:00Z"
---

# G-3: Ingest ACTIVSg 10000-bus reference network (MEDIUM)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Expected counts:** 10000/12706/2485
- **Actual counts:** 10000/12706/2485
- **Load time:** 3.06s
- **Data quality notes:**
  - No NaN/infinite in bus voltages
  - All branch ratings are finite
  - Slack bus identified: PHOENIX 74 6
  - 634 generators (RenewableDispatch) do not support `get_active_power_limits` -- type hierarchy limitation in PowerSystems.jl, not missing data
  - All 2485 generators have operation cost data
  - No branches with zero reactance
- **Errors/warnings:** None

## Test Script

`evaluations/powersimulations/test/run_gate_tests.jl`

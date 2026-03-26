---
test_id: G-1
tool: powersimulations
dimension: gate
network: TINY
protocol_version: v11
skill_version: v2
test_hash: 7f8c3606
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 8.93
timestamp: "2026-03-24T00:00:00Z"
---

# G-1: Ingest IEEE 39-bus reference network (TINY)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Expected counts:** 39/46/10
- **Actual counts:** 39/46/10
- **Load time:** 8.93s
- **Data quality notes:**
  - No NaN/infinite in bus voltages
  - All branch ratings are finite
  - Slack bus identified: bus-31
  - All 10 generators have operation cost data
  - No generators with non-finite active power limits
  - No branches with zero reactance
- **Errors/warnings:** None

## Test Script

`evaluations/powersimulations/test/run_gate_tests.jl`

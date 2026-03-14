---
test_id: G-1
tool: powersimulations
dimension: gate
network: TINY
status: pass
workaround_class: null
timestamp: "2026-03-14T00:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "0a74adbf"
---

# G-1: Ingest IEEE 39-bus reference network

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Expected counts:** 39/46/10
- **Actual counts:** 39/46/10
- **Load time:** 6.44s
- **Data quality notes:**
  - No NaN/infinite in bus voltages
  - All branch ratings are finite
  - Slack bus identified: bus-31
  - All 10 generators have operation cost data
  - No generators with non-finite active power limits
  - No branches with zero reactance reported
- **Errors/warnings:** None

## Test Script

`evaluations/powersimulations/test/run_gate_tests.jl`

---
test_id: G-3
tool: powersimulations
dimension: gate
network: MEDIUM
status: pass
workaround_class: null
timestamp: "2026-03-14T00:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "2da513c6"
---

# G-3: Ingest ACTIVSg 10k reference network

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Expected counts:** 10000/12706/2485
- **Actual counts:** 10000/12706/2485
- **Load time:** 2.43s
- **Data quality notes:**
  - No NaN/infinite in bus voltages
  - Slack bus identified: PHOENIX 74 6
  - 634 generators (RenewableDispatch) do not support `get_active_power_limits` — type hierarchy limitation, not missing data
  - All 2485 generators have operation cost data
  - No branches with non-finite ratings reported
- **Errors/warnings:** None

## Test Script

`evaluations/powersimulations/test/run_gate_tests.jl`

---
test_id: G-2
tool: powersimulations
dimension: gate
network: SMALL
status: pass
workaround_class: null
timestamp: "2026-03-14T00:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "84277a12"
---

# G-2: Ingest ACTIVSg 2k reference network

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Expected counts:** 2000/3206/544
- **Actual counts:** 2000/3206/544
- **Load time:** 1.34s
- **Data quality notes:**
  - No NaN/infinite in bus voltages
  - Slack bus identified: WADSWORTH 3
  - 109 generators (RenewableDispatch) do not support `get_active_power_limits` — this is a type hierarchy limitation in PowerSystems.jl, not missing data
  - All 544 generators have operation cost data
  - No branches with non-finite ratings reported
- **Errors/warnings:** None

## Test Script

`evaluations/powersimulations/test/run_gate_tests.jl`

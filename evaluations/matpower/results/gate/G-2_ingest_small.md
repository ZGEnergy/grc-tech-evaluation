---
test_id: G-2
tool: matpower
dimension: gate
network: SMALL
status: pass
workaround_class: null
timestamp: "2026-03-07T00:16:18Z"
protocol_version: "v4"
---

# G-2: Ingest SMALL (ACTIVSg 2000)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Expected counts:** 2000 buses / 3206 branches / 544 generators
- **Actual counts:** 2000 buses / 3206 branches / 544 generators
- **Load time:** 0.2193 seconds
- **Data quality notes:**
  - No NaN/Inf in bus voltages, generator limits, or branch ratings
  - Generator cost data present (544 gencost rows, matching 544 generators)
  - All branch RATE_A values non-zero (flow limits defined)
  - Reference/slack bus identified: bus 7098
- **Errors/warnings:** None

## Test Script

`evaluations/matpower/tests/test_gate.m` -- same script as G-1, tier SMALL.

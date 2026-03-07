---
test_id: G-1
tool: matpower
dimension: gate
network: TINY
status: pass
workaround_class: null
timestamp: "2026-03-07T00:16:18Z"
protocol_version: "v4"
---

# G-1: Ingest TINY (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches / 10 generators
- **Load time:** 0.0161 seconds
- **Data quality notes:**
  - No NaN/Inf in bus voltages, generator limits, or branch ratings
  - Generator cost data present (10 gencost rows, matching 10 generators)
  - All branch RATE_A values non-zero (flow limits defined)
  - Reference/slack bus identified: bus 31
- **Errors/warnings:** None

## Test Script

`evaluations/matpower/tests/test_gate.m` -- Octave script that loads each network tier via
`loadcase()`, verifies bus/branch/gen counts against reference values, and audits for
NaN/Inf in voltages, generator limits, branch ratings, presence of gencost data, and
identification of the slack bus.

---
test_id: G-2
tool: gridcal
dimension: gate
network: SMALL
status: pass
workaround_class: null
timestamp: "2026-03-06T00:00:00Z"
protocol_version: "v4"
---

# G-2: SMALL Network Ingestion (ACTIVSg 2000-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Expected counts:** 2000 buses / 3206 branches / 544 generators
- **Actual counts:** 2000 buses / 3206 branches / 544 generators
- **Load time:** 2.083s
- **Branch breakdown:** 2359 lines + 847 transformers2W + 0 transformers3W
- **Data quality notes:**
  - No NaN/inf in bus voltages (Vnom)
  - No NaN/inf in generator limits (Pmin, Pmax)
  - All 2359 lines and 847 transformers have non-zero rate (branch flow limits present)
  - Generator cost data present (Cost, Cost0, Cost2 attributes); 410/544 generators have non-zero Cost (134 generators have zero cost, likely renewable/must-run units)
  - Slack bus identified: bus "WADSWORTH 3"
- **Errors/warnings:** None

## Test Script

See `evaluations/gridcal/tests/test_gate.py::TestGate::test_g2_small_import`

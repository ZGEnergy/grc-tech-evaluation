---
test_id: G-3
tool: gridcal
dimension: gate
network: MEDIUM
status: pass
workaround_class: null
timestamp: "2026-03-06T00:00:00Z"
protocol_version: "v4"
---

# G-3: MEDIUM Network Ingestion (ACTIVSg 10000-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Expected counts:** 10000 buses / 12706 branches / 2485 generators
- **Actual counts:** 10000 buses / 12706 branches / 2485 generators
- **Load time:** 7.173s
- **Branch breakdown:** 9726 lines + 2980 transformers2W + 0 transformers3W
- **Data quality notes:**
  - No NaN/inf in bus voltages (Vnom)
  - No NaN/inf in generator limits (Pmin, Pmax)
  - All 9726 lines and 2980 transformers have non-zero rate (branch flow limits present)
  - Generator cost data present (Cost, Cost0, Cost2 attributes); 1136/2485 generators have non-zero Cost (1349 generators have zero cost, likely renewable/must-run units)
  - Slack bus identified: bus "PHOENIX 74 6"
- **Errors/warnings:** None

## Test Script

See `evaluations/gridcal/tests/test_gate.py::TestGate::test_g3_medium_import`

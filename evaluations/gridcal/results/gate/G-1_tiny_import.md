---
test_id: G-1
tool: gridcal
dimension: gate
network: TINY
status: pass
workaround_class: null
timestamp: "2026-03-06T00:00:00Z"
protocol_version: "v4"
---

# G-1: TINY Network Ingestion (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches / 10 generators
- **Load time:** 0.164s
- **Branch breakdown:** 35 lines + 11 transformers2W + 0 transformers3W
- **Data quality notes:**
  - No NaN/inf in bus voltages (Vnom)
  - No NaN/inf in generator limits (Pmin, Pmax)
  - All 35 lines and 11 transformers have non-zero rate (branch flow limits present)
  - Generator cost data present (Cost, Cost0, Cost2 attributes); 10/10 generators have non-zero Cost
  - Slack bus identified: bus "31"
- **Errors/warnings:** None

## Test Script

See `evaluations/gridcal/tests/test_gate.py::TestGate::test_g1_tiny_import`

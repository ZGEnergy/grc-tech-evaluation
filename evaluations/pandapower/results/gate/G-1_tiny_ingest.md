---
test_id: G-1
tool: pandapower
dimension: gate
network: TINY
status: pass
workaround_class: null
timestamp: "2026-03-06T00:00:00Z"
protocol_version: "v4"
---

# G-1: TINY Network Ingestion (case39.m)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m (IEEE 39-bus New England system)
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches / 10 generators
- **Load time:** 0.105s
- **Element breakdown:**
  - Lines: 35, Trafos: 11, Trafo3w: 0, Impedance: 0
  - Gen: 9, ExtGrid: 1, Sgen: 0
- **Data quality notes:** No warnings. Bus voltages, line ratings, and generator limits free of NaN/Inf. Generator cost data present (poly_cost). Branch flow limits present (max_i_ka). Slack bus identified (1 ext_grid).
- **Errors/warnings:** None

## Test Script

`evaluations/pandapower/tests/test_gate.py::TestGate::test_gate_ingest[G-1]`

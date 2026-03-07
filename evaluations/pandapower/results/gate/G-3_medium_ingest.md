---
test_id: G-3
tool: pandapower
dimension: gate
network: MEDIUM
status: pass
workaround_class: null
timestamp: "2026-03-06T00:00:00Z"
protocol_version: "v4"
---

# G-3: MEDIUM Network Ingestion (case_ACTIVSg10k.m)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m (Synthetic US WECC 10000-bus system)
- **Expected counts:** 10000 buses / 12706 branches / 2485 generators
- **Actual counts:** 10000 buses / 12706 branches / 2485 generators
- **Load time:** 0.347s
- **Element breakdown:**
  - Lines: 9726, Trafos: 975, Trafo3w: 0, Impedance: 2005
  - Gen: 1727, ExtGrid: 1, Sgen: 757
- **Data quality notes:** No warnings. Bus voltages, line ratings, and generator limits free of NaN/Inf. Generator cost data present (poly_cost). Branch flow limits present (max_i_ka). Slack bus identified (1 ext_grid). Note: 2005 MATPOWER branches were converted to pandapower impedance elements; 4 branches flagged as trafos connecting same voltage levels.
- **Errors/warnings:** pandapower warning: "There are 4 branches which are considered as trafos - due to ratio unequal 0 or 1 - but connect same voltage levels." (informational, all elements accounted for)

## Test Script

`evaluations/pandapower/tests/test_gate.py::TestGate::test_gate_ingest[G-3]`

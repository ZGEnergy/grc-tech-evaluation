---
test_id: G-2
tool: pandapower
dimension: gate
network: SMALL
status: pass
workaround_class: null
timestamp: "2026-03-06T00:00:00Z"
protocol_version: "v4"
---

# G-2: SMALL Network Ingestion (case_ACTIVSg2000.m)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m (Synthetic Texas 2000-bus system)
- **Expected counts:** 2000 buses / 3206 branches / 544 generators
- **Actual counts:** 2000 buses / 3206 branches / 544 generators
- **Load time:** 0.120s
- **Element breakdown:**
  - Lines: 2359, Trafos: 0, Trafo3w: 0, Impedance: 847
  - Gen: 484, ExtGrid: 1, Sgen: 59
- **Data quality notes:** No warnings. Bus voltages, line ratings, and generator limits free of NaN/Inf. Generator cost data present (poly_cost). Branch flow limits present (max_i_ka). Slack bus identified (1 ext_grid). Note: 847 MATPOWER branches were converted to pandapower impedance elements rather than lines, due to voltage ratio characteristics.
- **Errors/warnings:** FutureWarning from pandas regarding dtype incompatibility in branch_lookup (cosmetic, does not affect results)

## Test Script

`evaluations/pandapower/tests/test_gate.py::TestGate::test_gate_ingest[G-2]`

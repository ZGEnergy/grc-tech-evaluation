---
test_id: G-3
tool: gridcal
dimension: gate
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: "2da513c6"
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 4.871
timestamp: 2026-03-24T19:05:18Z
---

# G-3: Ingest MEDIUM Network (ACTIVSg 10k)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Expected counts:** 10000 buses / 12706 branches / 2485 generators
- **Actual counts:** 10000 buses / 12706 branches (9726 lines + 2980 transformers) / 2485 generators
- **Load time:** 4.871s
- **Data quality notes:**
  - Bus Vnom: no NaN or infinite values (0/10000)
  - Branch flow limits present: all 12706 branches have positive rate values (no NaN, Inf, or zero)
  - Generator Pmax: no NaN or infinite values (0/2485)
  - Generator cost data present: 1136/2485 generators have non-zero Cost or Cost2 fields (1349 generators have zero cost -- consistent with renewable/must-run units in the MATPOWER source data)
  - Slack/reference bus identified: bus 'PHOENIX 74 6' (code '40845')
- **Errors/warnings:** None

## Test Script

**Path:** `evaluations/gridcal/tests/test_gate.py` (class `TestGateG3`)

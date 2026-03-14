---
test_id: G-2
tool: gridcal
dimension: gate
network: SMALL
status: pass
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: "v10"
skill_version: v1
test_hash: "84277a12"
wall_clock_seconds: 1.315
timing_source: measured
---

# G-2: Ingest SMALL Network (ACTIVSg 2k)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Expected counts:** 2000 buses / 3206 branches / 544 generators
- **Actual counts:** 2000 buses / 3206 branches (2359 lines + 847 transformers) / 544 generators
- **Load time:** 1.315s
- **Data quality notes:**
  - Bus Vnom: no NaN or infinite values (0/2000)
  - Branch flow limits present: all 3206 branches have positive rate values (no NaN, Inf, or zero)
  - Generator Pmax: no NaN or infinite values (0/544)
  - Generator cost data present: 410/544 generators have non-zero Cost or Cost2 fields (134 generators have zero cost — these are likely renewable/must-run units with zero marginal cost in the MATPOWER source data)
  - Slack/reference bus identified: bus 'WADSWORTH 3' (code '7098')
- **Errors/warnings:** None

## Test Script

**Path:** `evaluations/gridcal/tests/test_gate.py`

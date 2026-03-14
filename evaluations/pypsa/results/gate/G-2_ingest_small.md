---
test_id: G-2
tool: pypsa
dimension: gate
network: SMALL
status: pass
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: v10
skill_version: v1
test_hash: 86c5996e
---

# G-2: Ingest reference network — SMALL (ACTIVSg 2k)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Expected counts:** 2000 buses / 3206 branches / 544 generators
- **Actual counts:** 2000 buses / 3206 branches / 544 generators
- **Load time:** 0.06s
- **Data quality notes:**
  - No NaN/infinite values
  - Branch flow limits present
  - Slack bus identified
  - Generator cost data not imported (same limitation as G-1)

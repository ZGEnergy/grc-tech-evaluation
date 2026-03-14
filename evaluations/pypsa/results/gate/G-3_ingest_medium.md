---
test_id: G-3
tool: pypsa
dimension: gate
network: MEDIUM
status: pass
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: v10
skill_version: v1
test_hash: 6e23d994
---

# G-3: Ingest reference network — MEDIUM (ACTIVSg 10k)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Expected counts:** 10000 buses / 12706 branches / 2485 generators
- **Actual counts:** 10000 buses / 12706 branches / 2485 generators
- **Load time:** 0.12s
- **Data quality notes:**
  - No NaN/infinite values
  - 2459 branches with zero s_nom (source data characteristic, not import error)
  - Slack bus identified
  - Generator cost data not imported

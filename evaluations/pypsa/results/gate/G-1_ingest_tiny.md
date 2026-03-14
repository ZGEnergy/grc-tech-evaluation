---
test_id: G-1
tool: pypsa
dimension: gate
network: TINY
status: pass
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: v10
skill_version: v1
test_hash: 667325b8
---

# G-1: Ingest reference network — TINY (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Import method:** matpowercaseframes.CaseFrames → pypsa.Network.import_from_pypower_ppc
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches (35 lines + 11 transformers) / 10 generators
- **Load time:** 0.05s
- **Data quality notes:**
  - No NaN/infinite values in bus voltages, line ratings, or generator limits
  - Branch flow limits present (s_nom populated)
  - Slack bus identified (bus 39)
  - Generator cost data NOT imported — `import_from_pypower_ppc` does not support gencost

---
test_id: G-1
tool: pypsa
dimension: gate
network: TINY
protocol_version: v11
skill_version: v2
test_hash: 7f8c3606
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 0.059
timestamp: 2026-03-24T12:00:00Z
---

# G-1: Ingest reference network — TINY (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Import method:** matpowercaseframes.CaseFrames -> pypsa.Network.import_from_pypower_ppc
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches (35 lines + 11 transformers) / 10 generators
- **Load time:** 0.059s
- **Data quality notes:**
  - No NaN/infinite values in bus voltages, line ratings, or generator limits
  - Branch flow limits present (s_nom populated, zero s_nom branches: 0)
  - Slack bus identified (bus 31)
  - Generator cost data NOT imported — `import_from_pypower_ppc` does not support gencost (PyPSA warns: "some PYPOWER features not supported: areas, gencosts, component status")
- **Errors/warnings:** PyPSA warns about `status` attribute naming conflict on lines and transformers (cosmetic, non-blocking)

## Test Script

`evaluations/pypsa/tests/test_gate.py` — class `TestGateG1` (4 subtests: bus count, branch count, generator count, data quality)
